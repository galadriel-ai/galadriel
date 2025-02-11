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

# Add agent with GPT-4o model and access to web search and market data
agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool(), dexscreener.fetch_market_data],
    additional_authorized_imports=["json"],
)

# Add basic client which sends two messages to the agent and prints agent's result
client = SimpleMessageClient(
    "What are top tokens on the market today?", "Should I buy ETH?"
)

# Set up the runtime
runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())
