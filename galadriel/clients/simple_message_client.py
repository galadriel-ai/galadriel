import asyncio
from typing import List

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue

# Implementation of agent input and output which infinitely pushes simple input for agent at specific interval
class SimpleMessageClient(AgentInput, AgentOutput):
    def __init__(self, *messages: str, interval_seconds: int = 60):
        if not messages:
            raise ValueError("At least one message must be provided.")

        self.interval_seconds: int = interval_seconds
        self.messages: List[Message] = [Message(content=msg) for msg in messages]

    async def start(self, queue: PushOnlyQueue):
        while True:
            try:
                for message in self.messages:
                    await queue.put(message)
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def send(self, request: Message, response: Message, proof: str):
        print("\n======== simple_message_client.post_output ========")
        print("request:", request)
        print("response:", response)
        print("proof:", proof)
