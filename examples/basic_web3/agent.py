import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool
from galadriel.tools.web3 import dexscreener

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool(), dexscreener.fetch_market_data],
    additional_authorized_imports=["json"],
)

client = SimpleMessageClient(
    "What are top tokens on the market today?", "Should I buy ETH?"
)

runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

asyncio.run(runtime.run())
