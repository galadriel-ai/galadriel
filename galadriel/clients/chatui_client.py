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
from galadriel.entities import Message, PushOnlyQueue


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

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, logger: Optional[logging.Logger] = None):
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

        self.active_connection: Optional[asyncio.Queue] = None

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

        await self.queue.put(incoming)
        self.logger.info(f"Enqueued message: {incoming}")

        # Create a response stream for this conversation
        response_stream = self._create_response_stream(conversation_id)

        return StreamingResponse(
            response_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    async def _create_response_stream(self, conversation_id: str) -> AsyncGenerator[str, None]:
        """Create a response stream for a specific conversation."""
        # Create a queue for this connection
        queue: asyncio.Queue[Dict] = asyncio.Queue()

        # Store the active connection
        self.active_connection = queue

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
            self.active_connection = None

    async def send(self, request: Message, response: Message) -> None:
        """Send a response message back to the chat interface.

        Args:
            request (Message): The original request message
            response (Message): The response to send to the client
        """
        if not response.conversation_id:
            self.logger.warning("No conversation_id found in response; cannot respond.")
            return

        # Check if we have an active connection
        if not self.active_connection:
            self.logger.warning(f"No active connection for conversation {response.conversation_id}")
            return

        # Format response in OpenAI-compatible format
        formatted_response = {
            "id": "chatcmpl-" + response.conversation_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-4",  # This could be configurable
            "choices": [{"index": 0, "delta": {"content": response.content}, "finish_reason": None}],
        }

        # Send the response to the active connection
        await self.active_connection.put(formatted_response)

        # Send a final message to indicate completion if the response is not a log message
        if response.final:
            final_message = {
                "id": "chatcmpl-" + response.conversation_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            await self.active_connection.put(final_message)

        self.logger.info(f"Response sent to conversation {response.conversation_id}: {response.content}")
