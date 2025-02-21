import asyncio
import os
from pathlib import Path
from galadriel.tools.web3.market_data import coingecko
from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent, LiteLLMModel
from galadriel.clients import SimpleMessageClient
from galadriel.tools import DuckDuckGoSearchTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Add agent with GPT-4o model and DuckDuckGo search tool
agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool(), coingecko.GetCoinPriceTool(), coingecko.GetCoinHistoricalDataTool()],
)

# Add basic client which sends two messages to the agent and prints agent's result
# client = SimpleMessageClient("What are the prices of Solana and Bitcoin today in USD and Polish zloty?")

client = SimpleMessageClient("How did the price of Bitcoin changed over last 2 days")

# Set up the runtime
runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())
