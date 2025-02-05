import asyncio
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime
from galadriel.clients import Cron
from trading_agent import trading_agent
from tools import onchain

TRADING_INTERVAL_SECONDS = 300

load_dotenv(dotenv_path=Path(".") / ".env", override=True)


onchain.deposit_usdc("Alice", 1000)
onchain.deposit_token("Alice", "SOL", 10)

onchain.deposit_usdc("Bob", 500)
onchain.deposit_token("Bob", "ELON", 5)


agent = AgentRuntime(
    inputs=[Cron(TRADING_INTERVAL_SECONDS)],
    outputs=[],
    agent=trading_agent,
)

asyncio.run(agent.run())
