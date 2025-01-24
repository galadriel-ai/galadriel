from litellm import completion

from entities import ShortTermMemory
from entities import LongTermMemory
from repositories.memory_repository import MemoryRepository

PROMPT = """You are analyzing a conversation between a user and an AI agent to determine if any new information needs to be stored in the AI agent's long-term memory.

Input includes:
- User Query: The user's input in the current interaction.
- AI Response: The AI's output in response to the user's input.
- Existing Long-Term Memory: A list of facts or details already stored in the AI agent's memory.

Your task is to decide:
- If any part of the user query or the AI response contains specific, personal, or unique information that improves future interactions by providing context, continuity, or personalization.
- If so, output the exact information to store in a concise and clear format.
- Ensure no duplication by cross-referencing with the existing long-term memory.

Output format:
- If nothing needs to be stored, respond with: NO
- If something needs to be stored, respond with the memory to store

User Query:
{user_message}

AI Response:
{ai_response}

Existing Long-Term Memory:
{memory}
"""


def update_long_term_memory(
    repository: MemoryRepository, user_id: str, memory: ShortTermMemory
) -> bool:
    """
    Save the memory to the long term memory.
    Args:
        memory: the memory to save
    """
    long_term_memory = repository.get_long_term_memory(user_id)
    print("Long term memory:", long_term_memory)
    prompt = PROMPT.format(
        user_message=memory.task, ai_response=memory.result, memory=long_term_memory
    )
    response = completion(
        model="gpt-4o", messages=[{"content": prompt, "role": "user"}]
    )
    if response["choices"][0]["message"]["content"] == "NO":
        return False

    new_memory = LongTermMemory(content=response["choices"][0]["message"]["content"])
    repository.add_long_term_memory(user_id, new_memory)
    return True
