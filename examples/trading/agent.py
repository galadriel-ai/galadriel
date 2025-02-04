import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel_agent.agent import AgentRuntime
from galadriel_agent.clients.cron import Cron
from galadriel_agent.core_agent import LiteLLMModel
from trading_agent import TradingAgent
from tools import onchain
from tools import markets

TRADING_INTERVAL_SECONDS = 300

load_dotenv(dotenv_path=Path(".") / ".env", override=True)


onchain.deposit_usdc("Alice", 1000)
onchain.deposit_token("Alice", "SOL", 10)

onchain.deposit_usdc("Bob", 500)
onchain.deposit_token("Bob", "ELON", 5)


model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

tools = [
    markets.fetch_market_data,
    onchain.get_all_portfolios,
    onchain.get_user_balance,
    onchain.update_user_balance,
    onchain.swap_token,
]

agent = TradingAgent(
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
)


agent = AgentRuntime(
    inputs=[Cron(TRADING_INTERVAL_SECONDS)],
    outputs=[],
    agent=agent,
)

asyncio.run(agent.run())
