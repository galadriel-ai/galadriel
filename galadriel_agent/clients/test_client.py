import asyncio
from typing import List

from galadriel_agent.agent import AgentInput, AgentOutput
from galadriel_agent.entities import Message, PushOnlyQueue


class TestClient(AgentInput, AgentOutput):
    def __init__(self, messages: List[Message], interval_seconds: int = 60):
        self.messages = messages
        self.interval_seconds = interval_seconds

    async def start(self, queue: PushOnlyQueue):
        while True:
            try:
                for message in self.messages:
                    await queue.put(message)
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def send(self, request: Message, response: Message, proof: str):
        print("\n======== test.client.post_output ========")
        print("request:", request)
        print("response:", response)
        print("proof:", proof)
