import os
from galadriel import CodeAgent
from galadriel.agent import LiteLLMModel
from galadriel.tools.web3.dexscreener import get_token_profile
from tools.coin_price_tool import coin_price_api


model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

research_agent = CodeAgent(
    tools=[
        coin_price_api,
        get_token_profile,
    ],
    model=model,
    add_base_tools=True,
)
