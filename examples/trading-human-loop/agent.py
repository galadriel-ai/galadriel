import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from intent_routing_agent import intent_router
from galadriel import AgentRuntime
from galadriel.clients import ChatUIClient
from galadriel.memory.memory_store import MemoryStore


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

chatui_client = ChatUIClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[chatui_client],
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
