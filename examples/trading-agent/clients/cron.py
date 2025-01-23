import asyncio
from typing import Dict

from galadriel_agent.clients.client import Client

CRON_INTERVAL = 300


class CronClient(Client):
    async def start(self, queue: asyncio.Queue):
        while True:
            try:
                await queue.put({})
                await asyncio.sleep(CRON_INTERVAL)
            except asyncio.CancelledError:
                break

    async def post_output(self, request, response: Dict, proof: str):
        pass
