import asyncio
import json
import logging
import time
from typing import Dict, Optional, AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, Proof


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatUIClient(AgentInput, AgentOutput):
    """A ChatUI client that handles SSE-based message communication.

    This class implements both AgentInput and AgentOutput interfaces to provide
    integration with a web-based chat interface using Server-Sent Events (SSE).
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the ChatUI client.

        Args:
            host (str): Host to bind the server to
            port (int): Port to bind the server to
            logger (Optional[logging.Logger]): Logger instance for tracking activities
        """
        self.app = FastAPI()
        self.queue: Optional[PushOnlyQueue] = None
        self.logger = logger or logging.getLogger("chatui_client")
        self.host = host
        self.port = port

        # Replace single connection with a dictionary of connections
        self.active_connections: Dict[str, asyncio.Queue] = {"chat": None, "cron": None}  # type: ignore

        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register the chat endpoint
        self.app.post("/chat/completions")(self.chat_endpoint)

    async def start(self, queue: PushOnlyQueue) -> None:
        """Start the ChatUI client and begin processing messages.

        This method starts the FastAPI server in a way that doesn't block the calling
        coroutine, allowing it to be used with asyncio.create_task().

        Args:
            queue (PushOnlyQueue): Queue for storing incoming messages
        """
        self.queue = queue
        self.logger.info(f"Starting ChatUI client on {self.host}:{self.port}")

        # Create a server config
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info")

        # Create the server
        server = uvicorn.Server(config)

        # Start the server - this will run until the server is stopped
        await server.serve()

    async def chat_endpoint(self, chat_request: ChatRequest):
        """Handle incoming chat requests via SSE."""
        if not self.queue:
            self.logger.warning("Queue not initialized. Ignoring incoming message.")
            return

        # Process only the last message in the conversation
        last_message = chat_request.messages[-1]

        # Check if this is a cron check request
        if "[CRON CHECK]" in last_message.content:
            # Create a response stream for cron messages
            response_stream = self._create_response_stream("cron")

            # If we don't have a cron connection with messages, add an empty response
            if not self.active_connections["cron"] or self.active_connections["cron"].empty():
                # Create a queue if it doesn't exist
                if not self.active_connections["cron"]:
                    self.active_connections["cron"] = asyncio.Queue()

                # Add a "no messages" response to the queue
                no_messages_response = {
                    "id": "chatcmpl-cron-check",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "galadriel",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": " "},
                            "finish_reason": None,
                        }
                    ],
                }
                await self.active_connections["cron"].put(no_messages_response)

                # Add a final message to close the stream
                final_message = {
                    "id": "chatcmpl-cron-check",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "galadriel",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                await self.active_connections["cron"].put(final_message)

            return StreamingResponse(
                response_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # Create a unique conversation ID (in practice, you might want to manage this differently)
        conversation_id = "chat-1"  # Simplified for this example

        # Create and queue the incoming message
        incoming = Message(
            content=last_message.content,
            conversation_id=conversation_id,
            additional_kwargs={
                "author": "web_user",
                "role": last_message.role,
            },
        )

        # Enqueue the incoming message in a non-blocking way
        asyncio.create_task(self.queue.put(incoming))
        self.logger.info(f"Enqueued message: {incoming}")

        # Create a response stream for this conversation
        response_stream = self._create_response_stream("chat")

        return StreamingResponse(
            response_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    async def _create_response_stream(self, connection_type: str) -> AsyncGenerator[str, None]:
        """Create a response stream for a specific connection type (chat or cron)."""
        # Create a queue for this connection if it doesn't exist
        if not self.active_connections[connection_type]:
            self.active_connections[connection_type] = asyncio.Queue()

        # Get the queue for this connection
        queue = self.active_connections[connection_type]

        try:
            # Keep the connection open
            while True:
                # Wait for messages to be added to this queue
                try:
                    # Wait for a message with a timeout
                    message = await asyncio.wait_for(queue.get(), timeout=60)

                    # Format and yield the message
                    yield f"data: {json.dumps(message)}\n\n"

                    # If this is the end message, break the loop
                    if message.get("choices", [{}])[0].get("finish_reason") == "stop":
                        break

                except asyncio.TimeoutError:
                    # Send a keep-alive comment to prevent connection timeout
                    yield ": keep-alive\n\n"
                    continue

        finally:
            # Clean up when the connection is closed
            self.active_connections[connection_type] = None  # type: ignore

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Send a response message back to the chat interface in OpenAI format.

        Args:
            request (Message): The original request message
            response (Message): The response to send to the client
        """
        if not response.conversation_id:
            self.logger.warning("No conversation_id found in response; cannot respond.")
            return

        # Determine if this is a cron message
        is_cron = response.additional_kwargs and response.additional_kwargs.get("author") == "cron"
        connection_type = "cron" if is_cron else "chat"

        # Check if we have an active connection for this type
        if not self.active_connections[connection_type]:
            if is_cron:
                # For cron messages, create a queue if it doesn't exist
                self.active_connections[connection_type] = asyncio.Queue()
            else:
                self.logger.warning(f"No active connection for conversation {response.conversation_id}")
                return

        # Get role from additional_kwargs or default to "assistant"
        role = response.additional_kwargs.get("role", "assistant") if response.additional_kwargs else "assistant"

        # Format response in OpenAI-compatible format
        formatted_response = {
            "id": "chatcmpl-" + response.conversation_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "galadriel",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": role, "content": response.content},
                    "finish_reason": None,
                }
            ],
        }

        # Add any additional metadata that might be useful for the UI
        if response.additional_kwargs:
            # Create a clean copy of additional_kwargs without role to avoid duplication
            metadata = {k: v for k, v in response.additional_kwargs.items() if k != "role"}
            if metadata:  # Only add if there's something left
                formatted_response["choices"][0]["delta"]["metadata"] = metadata  # type: ignore

        # Send the response to the appropriate connection
        await self.active_connections[connection_type].put(formatted_response)

        # Send a final message to indicate completion if this is the final message
        if response.final:
            final_message = {
                "id": "chatcmpl-" + response.conversation_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "galadriel",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            await self.active_connections[connection_type].put(final_message)

        self.logger.info(f"Response sent to {connection_type} connection")
        # Yield a small delay to that the response is picked up and sent to the client
        await asyncio.sleep(0.1)
