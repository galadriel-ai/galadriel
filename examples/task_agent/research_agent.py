import os
from typing import List

from smolagents import CodeAgent
from smolagents import LiteLLMModel

from galadriel_agent.agent import Agent

from domain import parse_twitter_message
from entities import Memory
from entities import ShortTermMemory
from galadriel_agent.entities import Message
from repositories.memory_repository import MemoryRepository
from tools.coin_price_tool import coin_price_api
from tools.dex_screener_tool import dex_screener_api
from tools.memory_tool import update_long_term_memory
from tools import solana_tool

AGENT_WALLET_ADDRESS = "5RYHzQuknP2viQjYzP27wXVWKeaxonZgMBPQA86GV92t"

memory_repository = MemoryRepository()


class ResearchAgent(Agent):

    async def run(self, request: Message) -> Message:
        conversation_id = request.conversation_id
        request_id = request.additional_kwargs["id"]
        author_id = request.additional_kwargs["author_id"]
        task = request.content

        twitter_message = parse_twitter_message.execute(task)
        if twitter_message:
            is_payment_valid = solana_tool.solana_payment_tool(
                signature=twitter_message.payment_signature,
                wallet_address=AGENT_WALLET_ADDRESS,
            )
            if not is_payment_valid:
                return Message(
                    content="Invalid payment",
                    additional_kwargs={"reply_to_id": request_id},
                )
            # call out agent now after payment has been validated
            if not memory_repository.add_payment_signature(
                twitter_message.payment_signature, twitter_message.task
            ):
                return Message(
                    content="Funds already spent",
                    additional_kwargs={"reply_to_id": request_id},
                )
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
                    task
                    + "\nLong term memory:\n"
                    + self._format_memories(long_term_memory)
                )
            agent = self._get_agent()
            answer = agent.run(task)
            memory = ShortTermMemory(task=(task), result=str(answer))
            memory_repository.add_short_term_memory(author_id, conversation_id, memory)
            update_long_term_memory(memory_repository, author_id, memory)
            return Message(
                content=answer, additional_kwargs={"reply_to_id": request_id}
            )
        else:
            return Message(
                content="Invalid request", additional_kwargs={"reply_to_id": request_id}
            )

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
