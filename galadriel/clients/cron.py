import asyncio

from galadriel import AgentInput
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue


class Cron(AgentInput):
    """A time-based input source that generates empty messages at fixed intervals.

    This class implements AgentInput to provide periodic triggers to an agent runtime.
    It can be used to schedule regular agent actions or health checks.
    """

    def __init__(self, interval_seconds: int):
        """Initialize the Cron input source.

        Args:
            interval_seconds (int): The time interval in seconds between messages
        """
        self.interval_seconds = interval_seconds

    async def start(self, queue: PushOnlyQueue):
        """Begin sending periodic empty messages to the queue.

        This method runs indefinitely until cancelled, pushing an empty message
        to the queue at the specified interval.

        Args:
            queue (PushOnlyQueue): The queue to which messages will be pushed

        Raises:
            asyncio.CancelledError: When the task is cancelled
        """
        while True:
            try:
                await queue.put(Message(content=""))
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
