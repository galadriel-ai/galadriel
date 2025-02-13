import asyncio
from typing import Optional
import logging
from datetime import datetime
import gradio as gr

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, HumanMessage


class GradioClient(AgentInput, AgentOutput):
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.message_queue: Optional[PushOnlyQueue] = None
        self.logger = logger or logging.getLogger("gradio_client")
        self.conversation_id = "gradio"
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()

        # Initialize the Gradio interface with a chatbot component
        with gr.Blocks() as self.interface:
            self.chatbot = gr.Chatbot(
                value=[],
                label="Chat History",
                height=400,
                show_label=False,
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
        """Handle incoming messages from Gradio"""
        if not message:
            return "", history

        await self.input_queue.put(message)
        history = history or []
        history.append((message, None))
        return "", history

    async def _process_response(self, history):
        """Process the response and update the UI"""
        while self.output_queue.empty():
            await asyncio.sleep(0.1)
        new_message = await self.output_queue.get()
        history.append((None, new_message))
        return history

    async def start(self, queue: PushOnlyQueue) -> None:
        self.message_queue = queue

        # Launch Gradio interface in a background thread
        self.interface.queue()
        self.interface.launch(server_name="0.0.0.0", share=False, prevent_thread_lock=True)
        # Log the local URL for accessing the Gradio interface
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
        """Update the Gradio chat interface with the response"""
        message = response.content
        if not message:
            self.logger.error("No message to send")
            raise ValueError("No message to send")
        await self.output_queue.put(message)
