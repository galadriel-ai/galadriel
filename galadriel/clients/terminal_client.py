import asyncio
from typing import Optional
import logging
from datetime import datetime

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, Proof


class TerminalClient(AgentInput, AgentOutput):
    """A command-line interface for interactive chat with the agent.

    This class implements both AgentInput and AgentOutput interfaces to provide
    a simple terminal-based chat interface. It allows users to type messages
    directly into the console and receive responses from the agent.

    Attributes:
        message_queue (Optional[PushOnlyQueue]): Queue for storing messages to be processed
        logger (logging.Logger): Logger instance for tracking client activities
        conversation_id (str): Identifier for the terminal chat session
        response_received (asyncio.Event): Event to signal when a response is received
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the terminal client interface.

        Args:
            logger (Optional[logging.Logger]): Custom logger instance. If None,
                                             creates a default logger
        """
        self.message_queue: Optional[PushOnlyQueue] = None
        self.logger = logger or logging.getLogger("terminal_client")
        self.conversation_id = "terminal"  # Single conversation ID for terminal
        self.response_received = asyncio.Event()

    async def get_user_input(self):
        """Get input from user asynchronously.

        Uses an event loop executor to handle blocking input() calls without
        blocking the entire async application.

        Returns:
            str: The user's input text

        Note:
            This method runs input() in a separate thread to maintain
            asynchronous operation.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "You: ")

    async def start(self, queue: PushOnlyQueue) -> None:
        """Start the terminal chat interface.

        Begins an interactive loop that processes user input and queues
        messages for the agent. The loop continues until the user types 'exit'.

        Args:
            queue (PushOnlyQueue): Queue for storing messages to be processed

        Note:
            - Empty input lines are ignored
            - The chat can be terminated by typing 'exit' (case-insensitive)
        """
        self.message_queue = queue
        self.logger.info("Terminal chat started. Type 'exit' to quit.")

        while True:
            try:
                # Get user input
                user_input = await self.get_user_input()

                # Ignore empty
                if not user_input.strip():
                    continue

                if user_input.lower() == "exit":
                    print("Goodbye!")
                    break

                # Create Message object and add to queue
                msg = Message(
                    content=user_input,
                    conversation_id=self.conversation_id,
                    additional_kwargs={
                        "author": "user_terminal",
                        "message_id": "terminal",
                        "timestamp": str(datetime.now().isoformat()),
                    },
                )

                # Clear the event before sending the message
                self.response_received.clear()

                await self.message_queue.put(msg)
                self.logger.debug(f"Added message to queue: {msg}")

                # Wait for the response
                await self.response_received.wait()

            except Exception as e:
                self.logger.error(f"Error processing input: {e}")
                break

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Display the agent's response in the terminal.

        Prints the agent's response to the console with simple formatting.

        Args:
            request (Message): The original request message (unused)
            response (Message): The response to display

        Note:
            The response is prefixed with "Agent: " for clarity in the
            conversation flow.
        """
        print(f"\nAgent: {response.content}")

        if response.final:
            self.response_received.set()
