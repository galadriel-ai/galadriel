import asyncio
import os

from galadriel import AgentRuntime
from galadriel.clients import SimpleMessageClient
from galadriel.clients import TwitterMentionClient
from galadriel.clients.twitter_mention_client import TwitterCredentials
from galadriel.entities import Pricing
from research_agent import research_agent

twitter_client = TwitterMentionClient(
    TwitterCredentials(
        consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY"),
        consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    ),
    user_id=os.getenv("TWITTER_USER_ID"),
    logger=logger,
)

simple_client = SimpleMessageClient(
    "Is Bitcoin good investment now with high prices? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy",
    "Should I buy ETH at this dip? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy",
)

runtime = AgentRuntime(
    inputs=[twitter_client, simple_client],
    outputs=[twitter_client, simple_client],
    agent=research_agent,
    pricing=Pricing(
        wallet_address="5RYHzQuknP2viQjYzP27wXVWKeaxonZgMBPQA86GV92t",
        cost=0.001,
    ),
)

asyncio.run(runtime.run())
