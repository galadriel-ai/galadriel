import asyncio
from typing import Dict

from galadriel_agent.clients.client import Client


class TestClient(Client):
    def __init__(self, request: Dict, interval_seconds: int = 120):
        self.request = request
        self.interval_seconds = interval_seconds

    async def start(self, queue: asyncio.Queue):
        while True:
            try:
                await queue.put(self.request)
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def post_output(self, request, response: Dict, proof: str):
        print("\n======== test.client.post_output ========")
        print("request:", request)
        print("response:", response)
        print("proof:", proof)
