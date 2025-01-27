from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel


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
