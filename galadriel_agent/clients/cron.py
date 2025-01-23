import asyncio
from typing import Dict

from galadriel_agent.clients.client import Client


class Cron(Client):
    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds

    async def start(self, queue: asyncio.Queue):
        while True:
            try:
                await queue.put({})
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def post_output(self, request, response: Dict, proof: str):
        pass
