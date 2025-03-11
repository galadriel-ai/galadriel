import asyncio
from typing import List
from typing import Optional

from galadriel import AgentInput, AgentOutput
from galadriel.entities import Message, PushOnlyQueue, Proof


class SimpleMessageClient(AgentInput, AgentOutput):
    """A basic client that sends predefined messages to an agent at regular intervals.

    This class implements both AgentInput and AgentOutput interfaces to provide
    a simple way to test agent functionality with predefined messages. It can
    either send messages once or repeatedly at specified intervals.

    Attributes:
        infinite_interval_seconds (Optional[int]): Time interval between message repetitions
        messages (List[Message]): List of predefined messages to send
    """

    def __init__(self, *messages: str, repeat_messages_interval: Optional[int] = None):
        """Initialize the SimpleMessageClient with a set of messages.

        Args:
            *messages: Variable number of message strings to send to the agent
            repeat_messages_interval (Optional[int]): If set, specifies the interval
                in seconds between repeated sends of all messages. If None,
                messages are sent only once.

        Raises:
            ValueError: If no messages are provided
        """
        if not messages:
            raise ValueError("At least one message must be provided.")

        self.infinite_interval_seconds: Optional[int] = repeat_messages_interval
        self.messages: List[Message] = [Message(content=msg) for msg in messages]
        self.response_received = asyncio.Event()

    async def start(self, queue: PushOnlyQueue):
        """Begin sending messages to the queue.

        If repeat_messages_interval was specified during initialization,
        continuously sends messages at that interval. Otherwise, sends
        all messages once and returns.

        Args:
            queue (PushOnlyQueue): Queue to which messages will be pushed

        Raises:
            asyncio.CancelledError: When the repeating task is cancelled
        """
        if self.infinite_interval_seconds is None:
            # If no interval is provided, just push messages once and return
            for message in self.messages:
                await self.put_message_and_wait(message, queue)
            return

        while True:
            try:
                for message in self.messages:
                    await self.put_message_and_wait(message, queue)
                await asyncio.sleep(self.infinite_interval_seconds)
            except asyncio.CancelledError:
                break

    async def put_message_and_wait(self, message, queue):
        self.response_received.clear()
        await queue.put(message)
        await self.response_received.wait()

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None):
        """Print the request and response messages to stdout.

        A simple implementation of message output that prints formatted
        request-response pairs to the console.

        Args:
            request (Message): The original request message
            response (Message): The agent's response message
        """
        if response.final:
            self.response_received.set()
            print("\n======== simple_message_client.post_output ========")
            print(" request:", request)
            print(" response:", response)
