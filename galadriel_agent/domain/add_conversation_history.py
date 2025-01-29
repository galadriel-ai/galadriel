from galadriel_agent.entities import Message
from galadriel_agent.entities import ShortTermMemory


def execute(request: Message, short_term_memory: ShortTermMemory) -> Message:
    messages = short_term_memory.get(request.conversation_id)
    if not messages:
        return request

    message_contents = []
    for message in messages:
        message_contents.append(message.content)

    if not message_contents:
        return request

    request.content = "\n\n".join(message_contents) + "\n\n" + request.content
    request.content = request.content.strip()
    return request
