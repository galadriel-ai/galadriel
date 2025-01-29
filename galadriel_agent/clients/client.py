import asyncio

from galadriel_agent.entities import Message


class PushOnlyQueue:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def put(self, item: Message):
        await self._queue.put(item)


class AgentInput:
    async def start(self, queue: PushOnlyQueue) -> None:
        pass

class AgentOutput:
    async def send(self, request: Message, response: Message, proof: str) -> None:
        pass