import asyncio
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime
from galadriel.clients import Cron
from trading_agent import trading_agent

TRADING_INTERVAL_SECONDS = 300

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

agent = AgentRuntime(
    inputs=[Cron(TRADING_INTERVAL_SECONDS)],
    outputs=[],
    agent=trading_agent,
)

asyncio.run(agent.run())
