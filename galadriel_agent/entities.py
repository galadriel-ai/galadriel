import asyncio
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel

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
