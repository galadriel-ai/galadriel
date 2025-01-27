from galadriel_agent.entities import Message
from galadriel_agent.entities import ShortTermMemory


def execute(request: Message, short_term_memory: ShortTermMemory) -> Message:
    print("\nadd_conversation_history, request:", request)
    # TODO: when conversation_id missing
    messages = short_term_memory.get(request.conversation_id)
    print("messages:", messages)
    if not messages:
        return request

    text = ""
    for message in messages:
        text += message.content

    if not text:
        return request

    request.content = text + " " + request.content
    request.content = request.content.strip()
    print("\n======== add_conversation_history ========")
    print("request:", request)
    return request
