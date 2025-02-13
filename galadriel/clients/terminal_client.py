import asyncio
import logging
from datetime import datetime
from typing import Optional

from galadriel import AgentInput, AgentOutput
from galadriel.entities import HumanMessage, Message, PushOnlyQueue


class TerminalClient(AgentInput, AgentOutput):
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.message_queue: Optional[PushOnlyQueue] = None
        self.logger = logger or logging.getLogger("terminal_client")
        self.conversation_id = "terminal"  # Single conversation ID for terminal

    async def get_user_input(self):
        """Get input from user asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "You: ")

    async def start(self, queue: PushOnlyQueue) -> None:
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
                msg = HumanMessage(
                    content=user_input,
                    conversation_id=self.conversation_id,
                    additional_kwargs={
                        "author": "user_terminal",
                        "message_id": "terminal",
                        "timestamp": str(datetime.now().isoformat()),
                    },
                )
                await self.message_queue.put(msg)
                self.logger.debug(f"Added message to queue: {msg}")
            except Exception as e:
                self.logger.error(f"Error processing input: {e}")
                break

    async def send(self, request: Message, response: Message) -> None:
        print(f"\nAgent: {response.content}")
