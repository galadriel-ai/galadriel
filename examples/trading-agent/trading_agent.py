import os
from typing import Dict

from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from galadriel_agent.agent import GaladrielAgent, UserAgent
from galadriel_agent.models import AgentConfig
from tools import markets, onchain
from trading_client import TradingClient

load_dotenv()

class TradingAgent:
    def __init__(self):
        model = LiteLLMModel(
            model_id="openai/gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        self.internal = CodeAgent(
            model=model,
            tools=[
                markets.fetch_market_data,
                onchain.get_all_portfolios,
                onchain.swap_token,
            ],
            add_base_tools=True,
            additional_authorized_imports=["json"],
        )

    async def run(self, request: Dict) -> Dict:
        output = self.internal.run(request["input"])
        return {"output": output}
