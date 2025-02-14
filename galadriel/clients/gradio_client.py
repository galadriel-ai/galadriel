import asyncio
from typing import Optional
import logging
from datetime import datetime
import gradio as gr

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, HumanMessage


class GradioClient(AgentInput, AgentOutput):
    """A Gradio-based web interface for chat interactions.

    This class implements both AgentInput and AgentOutput interfaces to provide
    a web-based chat interface using Gradio. It supports real-time message
    exchange between users and the agent system.

    Attributes:
        message_queue (Optional[PushOnlyQueue]): Queue for storing messages to be processed
        public_url (bool): Whether to share the Gradio interface publicly
        logger (logging.Logger): Logger instance for tracking client activities
        conversation_id (str): Identifier for the chat conversation
        input_queue (asyncio.Queue[str]): Queue for storing user inputs
        output_queue (asyncio.Queue[str]): Queue for storing agent responses
        interface (gr.Blocks): The Gradio interface instance
        chatbot (gr.Chatbot): The chat interface component
    """

    def __init__(self, logger: Optional[logging.Logger] = None, public_url: Optional[bool] = False):
        """Initialize the Gradio client interface.

        Args:
            logger (Optional[logging.Logger]): Custom logger instance. If None,
                                             creates a default logger
        """
        self.message_queue: Optional[PushOnlyQueue] = None
        self.public_url = public_url
        self.logger = logger or logging.getLogger("gradio_client")
        self.conversation_id = "gradio"
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()

        # Initialize the Gradio interface with a chatbot component
        with gr.Blocks() as self.interface:
            self.chatbot = gr.Chatbot(
                value=[],
                label="Agent",
                resizeable=True,
                scale=1,
            )
            with gr.Row():
                self.msg = gr.Textbox(
                    label="Message",
                    placeholder="Type a message...",
                    show_label=False,
                    scale=7,
                )
                self.submit = gr.Button("Send", scale=1)
            self.clear = gr.Button("Clear")

            # Set up event handlers with chaining
            self.msg.submit(self._handle_message, [self.msg, self.chatbot], [self.msg, self.chatbot]).then(
                self._process_response, [self.chatbot], [self.chatbot]
            )

            self.submit.click(self._handle_message, [self.msg, self.chatbot], [self.msg, self.chatbot]).then(
                self._process_response, [self.chatbot], [self.chatbot]
            )

            self.clear.click(lambda: [], None, self.chatbot, queue=False)

    async def _handle_message(self, message: str, history):
        """Process incoming messages from the Gradio interface.

        Args:
            message (str): The user's input message
            history: The current chat history

        Returns:
            tuple: A tuple containing (empty string, updated history)
        """
        if not message:
            return "", history

        await self.input_queue.put(message)
        history = history or []
        history.append((message, None))
        return "", history

    async def _process_response(self, history):
        """Process the agent's response and update the chat interface.

        Waits for a response from the output queue and adds it to the chat history.

        Args:
            history: The current chat history

        Returns:
            list: Updated chat history including the new response
        """
        while self.output_queue.empty():
            await asyncio.sleep(0.1)
        new_message = await self.output_queue.get()
        history.append((None, new_message))
        return history

    async def start(self, queue: PushOnlyQueue) -> None:
        """Start the Gradio interface and begin processing messages.

        Launches the web interface and starts the message processing loop.

        Args:
            queue (PushOnlyQueue): Queue for storing messages to be processed
        """
        self.message_queue = queue

        # Launch Gradio interface in a background thread
        self.interface.queue()
        self.interface.launch(server_name="0.0.0.0", server_port=7860, share=self.public_url, prevent_thread_lock=True)
        # Log the local URL for accessing the Gradio interface
        if not self.public_url:
            self.logger.info("Gradio interface available at: http://0.0.0.0:7860")

        # Process messages from input queue
        while True:
            if not self.input_queue.empty():
                user_input = await self.input_queue.get()

                msg = HumanMessage(
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

    async def send(self, request: Message, response: Message) -> None:
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
