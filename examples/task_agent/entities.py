from pydantic import BaseModel, Field
from uuid import uuid4


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))


class ShortTermMemory(Memory):
    task: str
    result: str

    def __str__(self):
        return f"TASK: {self.task}\nRESULT: {self.result}"


class LongTermMemory(Memory):
    content: str

    def __str__(self):
        return f"MEMORY: {self.content}"
