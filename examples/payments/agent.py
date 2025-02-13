import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel
from galadriel.entities import Pricing
from galadriel.tools.web3 import dexscreener, coingecko

load_dotenv(dotenv_path=Path(".") / ".env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Set up a researcher who will perform Web3 related tasks
researcher = CodeAgent(
    tools=[
        coingecko.get_coin_price,
        dexscreener.get_token_profile,
    ],
    model=model,
    add_base_tools=True,
)

# Configure agent's pricing information
agent_pricing = Pricing(
    wallet_address="5RYHzQuknP2viQjYzP27wXVWKeaxonZgMBPQA86GV92t",  # Agent's wallet address
    cost=0.001,  # Price per task in SOL
)

# The client will pass a research task to the agent with either
# - a link to the transaction on Solscan
# - a signature of transaction of Solana
# Example transaction passed to SimpleMessageClient below:
# https://explorer.solana.com/tx/5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy
simple_client = SimpleMessageClient(
    "Is Bitcoin good investment now with high prices? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy",
)

# Alternatively, Twitter (or Discord, Telegram) client which can be passed to inputs and outputs in order to get tasks from social channels
# twitter_client = TwitterMentionClient(
#     TwitterCredentials(
#         consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY"),
#         consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET"),
#         access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
#         access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
#     ),
#     user_id=os.getenv("TWITTER_USER_ID"),
# )

# Combine all elements into runtime
runtime = AgentRuntime(
    inputs=[simple_client],  # Runtime inputs, pass twitter_client if you use it
    outputs=[simple_client],  # Runtime outputs, pass twitter_client if you use it
    agent=researcher,
    pricing=agent_pricing,
)

# Run the runtime with agent
asyncio.run(runtime.run())
