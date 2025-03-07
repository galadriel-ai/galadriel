import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel.entities import Message, PushOnlyQueue
from intent_routing_agent import intent_router
from galadriel import AgentRuntime
from galadriel.clients import ChatUIClient, Cron
from galadriel.memory.memory_store import MemoryStore


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

class CronUI(Cron):
    async def start(self, queue: PushOnlyQueue):
        while True:
            try:
                await queue.put(Message(content="Start a trading research session",
                                        conversation_id="chat-1",
                                        additional_kwargs={"author": "cron"}))
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

cron_client = CronUI(interval_seconds=120)
chatui_client = ChatUIClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[chatui_client, cron_client],
    outputs=[chatui_client],
    memory_store=MemoryStore(
        api_key=os.getenv("OPENAI_API_KEY"),
        embedding_model="text-embedding-3-large",
        agent_name="trading_agent",
        short_term_memory_limit=4,
    ),
    agent=intent_router,
)

# Run the agent
asyncio.run(runtime.run(stream=False))
