from typing import List

from galadriel_agent.entities import Message
from galadriel_agent.entities import ShortTermMemory


class InMemoryShortTermMemory(ShortTermMemory):

    def __init__(self):
        self.messages = []

    def get(self, conversation_id: str) -> List[Message]:
        result = []
        print("\nget, convid:", conversation_id, "messages:", self.messages)
        for message in self.messages:
            if message.conversation_id == conversation_id:
                result.append(message)
        return result

    def add(self, message: Message):
        self.messages.append(message)
