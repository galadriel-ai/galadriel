import asyncio
from typing import Optional
import logging
from datetime import datetime
import gradio as gr

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, Proof


class GradioClient(AgentInput, AgentOutput):
    """A Gradio-based web interface for chat interactions.

    This class implements both AgentInput and AgentOutput interfaces to provide
    a web-based chat interface using Gradio. It supports real-time message
    exchange between users and the agent system.

    Attributes:
        message_queue (Optional[PushOnlyQueue]): Queue for storing messages to be processed
        is_public (bool): Whether to share the Gradio interface publicly
        server_port (int): The port on which to run the Gradio interface
        logger (logging.Logger): Logger instance for tracking client activities
        conversation_id (str): Identifier for the chat conversation
        input_queue (asyncio.Queue[str]): Queue for storing user inputs
        output_queue (asyncio.Queue[str]): Queue for storing agent responses
        interface (gr.Blocks): The Gradio interface instance
        chatbot (gr.Chatbot): The chat interface component
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        is_public: Optional[bool] = False,
        server_port: Optional[int] = 7860,
    ):
        """Initialize the Gradio client interface.

        Args:
            logger (Optional[logging.Logger]): Custom logger instance. If None,
                                             creates a default logger
        """
        self.message_queue: Optional[PushOnlyQueue] = None
        self.is_public = is_public
        self.server_port = server_port
        self.logger = logger or logging.getLogger("gradio_client")
        self.conversation_id = "gradio"
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()

        # Initialize the Gradio interface with a chatbot component
        with gr.Blocks() as self.interface:
            stored_messages = gr.State([])
            chatbot = gr.Chatbot(
                label="Agent",
                type="messages",
                resizeable=True,
                scale=1,
            )
            text_input = gr.Textbox(lines=1, label="Chat Message")
            text_input.submit(
                self._handle_message,
                [text_input, stored_messages, chatbot],
                [stored_messages, text_input, chatbot],
            )
            # Hidden refresh button to update the UI state.
            # Its click action calls refresh_chat, which returns the latest chat history.
            refresh_btn = gr.Button("Refresh", visible=False, elem_id="refresh-btn")
            refresh_btn.click(
                self._refresh_chat,
                inputs=[chatbot, stored_messages],
                outputs=[chatbot, stored_messages],
            )
            # JavaScript to click the hidden refresh button every 0.1 second
            gr.HTML(
                """
            <script>
            setInterval(function(){
                document.getElementById("refresh-btn").click();
            }, 100);
            </script>
            """
            )

    async def _refresh_chat(self, chatbot, stored_messages):
        """
        Simply returns the latest chat history.
        This function is used by a hidden button that is triggered via JavaScript
        to periodically refresh the UI.
        """
        return chatbot, stored_messages

    async def _handle_message(self, message: str, stored_messages, chatbot):
        """Process incoming messages from the Gradio interface.

        Args:
            message (str): The user's input message
            stored_messages: The stored messages state
            chatbot: The chatbot component

        Returns:
            tuple: A tuple containing (stored_messages, empty string, updated chatbot)
        """
        if not message:
            return stored_messages, "", chatbot

        await self.input_queue.put(message)

        # Add user message to chat
        chatbot.append(gr.ChatMessage(role="user", content=message))

        # Wait for and process the response
        while self.output_queue.empty():
            await asyncio.sleep(0.01)

        # Get and display the response
        while not self.output_queue.empty():
            new_message = await self.output_queue.get()
            chatbot.append(gr.ChatMessage(role="assistant", content=new_message))
            await asyncio.sleep(0.2)

        return stored_messages, "", chatbot

    async def start(self, queue: PushOnlyQueue) -> None:
        """Start the Gradio interface and begin processing messages.

        Launches the web interface and starts the message processing loop.

        Args:
            queue (PushOnlyQueue): Queue for storing messages to be processed
        """
        self.message_queue = queue

        # Launch Gradio interface in a background thread
        self.interface.queue()
        self.interface.launch(
            server_name="0.0.0.0",
            server_port=self.server_port,
            share=self.is_public,
            prevent_thread_lock=True,
        )
        # Log the local URL for accessing the Gradio interface
        if not self.is_public:
            self.logger.info(f"Gradio interface available at: http://0.0.0.0:{self.server_port}")

        # Process messages from input queue
        while True:
            if not self.input_queue.empty():
                user_input = await self.input_queue.get()

                msg = Message(
                    content=user_input,
                    conversation_id=self.conversation_id,
                    additional_kwargs={
                        "author": "user_gradio",
                        "message_id": "gradio",
                        "timestamp": str(datetime.now().isoformat()),
                    },
                )
                await self.message_queue.put(msg)

            await asyncio.sleep(0.1)

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Send a response message to the Gradio interface.

        Args:
            request (Message): The original request message (unused)
            response (Message): The response to display in the chat interface

        Raises:
            ValueError: If the response message is empty
        """
        message = response.content
        if not message:
            self.logger.error("No message to send")
            raise ValueError("No message to send")
        await self.output_queue.put(message)
