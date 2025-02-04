import json
import os
from typing import List
from typing import Optional

from galadriel import CodeAgent, LiteLLMModel

from entities import Memory
from entities import ShortTermMemory
from galadriel import Agent
from galadriel.entities import Message
from repositories.memory_repository import MemoryRepository
from tools.coin_price_tool import coin_price_api
from tools.dex_screener_tool import dex_screener_api
from tools.memory_tool import update_long_term_memory

memory_repository = MemoryRepository()


class ResearchAgent(Agent):

    async def execute(self, request: Message) -> Message:
        conversation_id = request.conversation_id
        request_id = request.additional_kwargs["id"]
        author_id = request.additional_kwargs["author_id"]
        task = request.content

        if not conversation_id or not author_id:
            return Message(
                content="Invalid request", additional_kwargs={"reply_to_id": request_id}
            )
        task = await self._add_memories_to_task(task, author_id, conversation_id)
        agent = self._get_agent()
        answer = agent.execute(task)
        memory = ShortTermMemory(task=(task), result=str(answer))
        memory_repository.add_short_term_memory(author_id, conversation_id, memory)
        update_long_term_memory(memory_repository, author_id, memory)
        return Message(content=answer, additional_kwargs={"reply_to_id": request_id})

    async def _add_memories_to_task(
        self,
        task: str,
        author_id: str,
        conversation_id: str,
    ) -> str:
        short_term_memory = memory_repository.get_short_term_memory(
            author_id, conversation_id
        )
        long_term_memory = memory_repository.query_long_term_memory(author_id, task)
        if short_term_memory:
            task = (
                task
                + "\nShort term memory:\n"
                + self._format_memories(short_term_memory)
            )
        if long_term_memory:
            task = (
                task + "\nLong term memory:\n" + self._format_memories(long_term_memory)
            )
        return task

    def _format_memories(self, memories: List[Memory]) -> str:
        return "\n".join([str(memory) for memory in memories])

    def _get_agent(self) -> CodeAgent:
        model = LiteLLMModel(
            model_id="openai/gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return CodeAgent(
            tools=[
                coin_price_api,
                dex_screener_api,
            ],
            model=model,
            add_base_tools=True,
        )
