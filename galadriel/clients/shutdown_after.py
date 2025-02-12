import asyncio

from galadriel import AgentInput
from galadriel.agent import AgentRuntime
from galadriel.entities import Message, PushOnlyQueue


class ShutdownAfter(AgentInput):
    """Client that sends a shutdown message after specified number of seconds"""

    def __init__(self, seconds: int):
        self.seconds = seconds

    async def start(self, queue: PushOnlyQueue):
        await asyncio.sleep(self.seconds)
        await queue.put(Message(content=AgentRuntime.SHUTDOWN_MESSAGE))
