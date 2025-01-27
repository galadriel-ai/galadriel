from typing import Dict
from typing import List

from galadriel_agent.domain import add_conversation_history
from galadriel_agent.entities import Message
from galadriel_agent.entities import ShortTermMemory
from galadriel_agent.memory.in_memory import InMemoryShortTermMemory

CONVERSATION_ID = "ci123"


def test_empty():
    stm = InMemoryShortTermMemory()
    message = Message(content="", conversation_id=CONVERSATION_ID)
    result = add_conversation_history.execute(message, stm)
    assert result == Message(content="", conversation_id=CONVERSATION_ID)


def test_empty_has_history():
    stm = InMemoryShortTermMemory()
    stm.add(Message(content="hello", conversation_id=CONVERSATION_ID))
    message = Message(content="", conversation_id=CONVERSATION_ID)
    result = add_conversation_history.execute(message, stm)
    assert result == Message(content="hello", conversation_id=CONVERSATION_ID)


def test_request_with_history():
    stm = InMemoryShortTermMemory()
    stm.add(Message(content="hello", conversation_id=CONVERSATION_ID))
    message = Message(content="world", conversation_id=CONVERSATION_ID)
    result = add_conversation_history.execute(message, stm)
    assert result == Message(content="hello world", conversation_id=CONVERSATION_ID)
