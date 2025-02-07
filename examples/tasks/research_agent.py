import os
from galadriel import CodeAgent
from galadriel.core_agent import LiteLLMModel
from galadriel.tools.web3.dexscreener import get_token_profile
from galadriel.tools.web3.coingecko import get_coin_price


model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

research_agent = CodeAgent(
    tools=[
        get_coin_price,
        get_token_profile,
    ],
    model=model,
    add_base_tools=True,
)
