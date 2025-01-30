import hashlib
import json

from galadriel_agent.entities import Message


def execute(request: Message, response: Message) -> str:
    # print("request:", request)
    # print("response:", response)
    return _hash_data(request, response)


def _hash_data(request: Message, response: Message) -> str:
    combined_str = f"{_dump(request)}{_dump(response)}"
    return hashlib.sha256(combined_str.encode("utf-8")).digest().hex()


def _dump(message: Message) -> str:
    if message:
        return json.dumps(message.model_dump(), sort_keys=True)
    return ""
