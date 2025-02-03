import asyncio
from typing import List

from pydantic import BaseModel
from pydantic import Field

from core_agent.models import Message

GALADRIEL_API_BASE_URL = "https://api.galadriel.com/v1"


class HumanMessage(Message):
    type: str = "human"


class AgentMessage(Message):
    type: str = "agent"


class ShortTermMemory:
    def get(self, conversation_id: str) -> List[Message]:
        pass

    def add(self, conversation_id: str, message: Message):
        pass


class PushOnlyQueue:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def put(self, item: Message):
        await self._queue.put(item)


class Pricing(BaseModel):
    """Represents pricing information for Galadriel Agent.

    Contains the cost in SOL and the agent wallet address for payments.
    """

    cost: float = Field(
        description="The cost of the task in SOL (Solana native currency)", gt=0
    )
    wallet_address: str = Field(
        description="The Solana wallet address where payment should be sent",
        min_length=32,
        max_length=44,
    )
