import asyncio
from typing import List
from typing import Optional

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue


# Implementation of agent input and output which pushes simple input for agent at specific interval
class SimpleMessageClient(AgentInput, AgentOutput):
    def __init__(self, *messages: str, repeat_messages_interval: Optional[int] = None):
        if not messages:
            raise ValueError("At least one message must be provided.")

        self.infinite_interval_seconds: int = repeat_messages_interval
        self.messages: List[Message] = [Message(content=msg) for msg in messages]

    async def start(self, queue: PushOnlyQueue):
        if self.infinite_interval_seconds is None:
            # If no interval is provided, just push messages once and return
            for message in self.messages:
                await queue.put(message)
            return

        while True:
            try:
                for message in self.messages:
                    await queue.put(message)
                await asyncio.sleep(self.infinite_interval_seconds)
            except asyncio.CancelledError:
                break

    async def send(self, request: Message, response: Message, proof: str):
        print("\n======== simple_message_client.post_output ========")
        print("request:", request)
        print("response:", response)
        print("proof:", proof)
