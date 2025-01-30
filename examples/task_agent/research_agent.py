import json
import os
from typing import List
from typing import Optional

from smolagents import CodeAgent
from smolagents import LiteLLMModel

from domain import parse_twitter_message
from entities import Memory
from entities import ShortTermMemory
from galadriel_agent.agent import Agent
from galadriel_agent.entities import Message
from repositories.memory_repository import MemoryRepository
from tools import solana_tool
from tools.coin_price_tool import coin_price_api
from tools.dex_screener_tool import dex_screener_api
from tools.memory_tool import update_long_term_memory

memory_repository = MemoryRepository()


class ResearchAgent(Agent):
    agent_wallet_address: str
    task_per_price_lamport: Optional[int]

    def __init__(
        self,
        character_json_path: str,
    ):
        try:
            with open(character_json_path, "r", encoding="utf-8") as f:
                agent_config = json.loads(f.read())
        except:
            raise Exception(
                f"Failed to read the provided character json: {character_json_path}"
            )
        pricing_config = agent_config.get("pricing", {})
        agent_wallet_address = pricing_config.get("wallet_address")
        if not agent_wallet_address:
            raise Exception(
                f'character json: {character_json_path}, is missing ["pricing"]["wallet_address"]'
            )
        self.agent_wallet_address = agent_wallet_address
        task_cost_sol = pricing_config.get("cost")
        if task_cost_sol:
            self.task_per_price_lamport = int(float(task_cost_sol) * 10**9)
        else:
            self.task_per_price_lamport = None

    async def run(self, request: Message) -> Message:
        conversation_id = request.conversation_id
        request_id = request.additional_kwargs["id"]
        author_id = request.additional_kwargs["author_id"]
        task = request.content

        if not conversation_id or not author_id:
            return Message(
                content="Invalid request", additional_kwargs={"reply_to_id": request_id}
            )
        twitter_message = parse_twitter_message.execute(task)
        if not twitter_message:
            return Message(
                content="Invalid request", additional_kwargs={"reply_to_id": request_id}
            )
        is_payment_valid = solana_tool.solana_payment_tool(
            signature=twitter_message.payment_signature,
            wallet_address=self.agent_wallet_address,
            price_lamport=self.task_per_price_lamport,
        )
        if not is_payment_valid:
            return Message(
                content="Invalid payment",
                additional_kwargs={"reply_to_id": request_id},
            )
        if not memory_repository.add_payment_signature(
            twitter_message.payment_signature, twitter_message.task
        ):
            return Message(
                content="Funds already spent",
                additional_kwargs={"reply_to_id": request_id},
            )
        task = await self._add_memories_to_task(task, author_id, conversation_id)
        agent = self._get_agent()
        answer = agent.run(task)
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
