import asyncio
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

GALADRIEL_API_BASE_URL = "https://api.galadriel.com/v1"


class Message(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    type: Optional[str] = None
    additional_kwargs: Optional[Dict] = None


class HumanMessage(Message):
    type: str = "human"


class AgentMessage(Message):
    type: str = "agent"


class AgentState(BaseModel):
    agent_id: str
    type: str
    steps: List[Dict[str, str]]


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
