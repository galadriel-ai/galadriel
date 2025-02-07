import asyncio
from typing import Optional
import sys
import logging
from datetime import datetime

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, HumanMessage


class TerminalClient(AgentInput, AgentOutput):
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.message_queue = None
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
                
                if user_input.lower() == 'exit':
                    print("Goodbye!")
                    break

                # Create Message object and add to queue
                msg = HumanMessage(
                    content=user_input,
                    conversation_id=self.conversation_id,
                    additional_kwargs={
                        "author": "user",
                        "message_id": "1",
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
        