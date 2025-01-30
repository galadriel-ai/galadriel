from galadriel_agent.domain import add_conversation_history
from galadriel_agent.entities import Message
from galadriel_agent.memory.in_memory import InMemoryShortTermMemory

CONVERSATION_ID = "ci123"


def test_conversation_id_missing_in_stm():
    stm = InMemoryShortTermMemory()
    stm.add(Message(content="hello"))
    message = Message(content="world", conversation_id=CONVERSATION_ID)
    result = add_conversation_history.execute(message, stm)
    assert result == Message(content="world", conversation_id=CONVERSATION_ID)


def test_conversation_id_missing_in_message():
    stm = InMemoryShortTermMemory()
    stm.add(Message(content="hello", conversation_id=CONVERSATION_ID))
    message = Message(content="world")
    result = add_conversation_history.execute(message, stm)
    assert result == Message(content="world")


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
    assert result == Message(content="hello\n\nworld", conversation_id=CONVERSATION_ID)


def test_request_with_multiple_messages_in_history():
    stm = InMemoryShortTermMemory()
    stm.add(Message(content="hello1", conversation_id=CONVERSATION_ID))
    stm.add(Message(content="hello2", conversation_id=CONVERSATION_ID))
    stm.add(Message(content="hello3", conversation_id=CONVERSATION_ID))
    message = Message(content="world", conversation_id=CONVERSATION_ID)
    result = add_conversation_history.execute(message, stm)
    assert result == Message(
        content="hello1\n\nhello2\n\nhello3\n\nworld", conversation_id=CONVERSATION_ID
    )
