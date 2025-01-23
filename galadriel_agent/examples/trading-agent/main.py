import asyncio

from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.cron import Cron
from galadriel_agent.models import AgentConfig
from tools import onchain
from trading_agent import TradingAgent

TRADING_INTERVAL_SECONDS = 300

def main():
    onchain.deposit_usdc("Alice", 1000)
    onchain.deposit_token("Alice", "SOL", 10)

    onchain.deposit_usdc("Bob", 500)
    onchain.deposit_token("Bob", "ELON", 5)

    agent = GaladrielAgent(
        agent_config=AgentConfig(),
        clients=Cron(TRADING_INTERVAL_SECONDS),
        user_agent=TradingAgent(),
    )

    asyncio.create_task(agent.run())

if __name__ == "__main__":
    main()
