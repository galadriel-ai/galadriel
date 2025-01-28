import asyncio

from galadriel_agent.entities import Message


class PushOnlyQueue:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def put(self, item: Message):
        await self._queue.put(item)


# Client interface, client itself can be Twitter, Discord, CLI, API etc...
class Client:
    async def start(self, queue: PushOnlyQueue) -> None:
        pass

    async def post_output(self, request: Message, response: Message, proof: str):
        pass
