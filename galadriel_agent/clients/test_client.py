import asyncio
from typing import Dict
from typing import List

from galadriel_agent.clients.client import Client
from galadriel_agent.entities import Message


class TestClient(Client):
    def __init__(self, messages: List[Message], interval_seconds: int = 60):
        self.messages = messages
        self.interval_seconds = interval_seconds

    async def start(self, queue: asyncio.Queue):
        while True:
            try:
                for message in self.messages:
                    await queue.put(message)
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def post_output(self, request, response: Dict, proof: str):
        print("\n======== test.client.post_output ========")
        print("request:", request)
        print("response:", response)
        print("proof:", proof)
