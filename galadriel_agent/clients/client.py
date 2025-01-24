import asyncio
from typing import Dict


class PushOnlyQueue:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def put(self, item):
        await self._queue.put(item)


# Client interface, client itself can be Twitter, Discord, CLI, API etc...
class Client:
    async def start(self, queue: PushOnlyQueue) -> Dict:
        pass

    async def post_output(self, request, response: Dict, proof: str):
        pass
