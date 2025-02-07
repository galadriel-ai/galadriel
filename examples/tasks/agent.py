import os
import json
import asyncio

from galadriel import AgentRuntime

from galadriel.clients import DiscordClient
from galadriel.clients import SimpleMessageClient
from galadriel.clients import TelegramClient
from galadriel.clients import TwitterMentionClient
from galadriel.clients.twitter_mention_client import TwitterCredentials
from galadriel.entities import Message
from galadriel.entities import Pricing
from galadriel.logging_utils import get_agent_logger
from research_agent import research_agent

logger = get_agent_logger()


async def main():
    clients = []
    """
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
    clients.append(twitter_client)
    discord_client = DiscordClient(
        guild_id=os.getenv("DISCORD_GUILD_ID"), logger=logger
    )
    clients.append(discord_client)
    telegram_client = TelegramClient(token=os.getenv("TELEGRAM_TOKEN"), logger=logger)
    clients.append(telegram_client)
    """
    message1 = Message(
        content="is ShitCoin good investment now with high prices? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy",
        conversation_id="conversationid123",
        additional_kwargs={"id": "id123", "author_id": "authorid123"},
    )
    message2 = Message(
        content="is FartoCoin good investment now with high prices? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy",
        conversation_id="conversationid123",
        additional_kwargs={"id": "id124", "author_id": "authorid123"},
    )
    test_client = SimpleMessageClient(message1.content, message2.content)
    clients.append(test_client)
    agent = AgentRuntime(
        inputs=clients,
        outputs=clients,
        agent=research_agent,
        pricing=Pricing(
            wallet_address="5RYHzQuknP2viQjYzP27wXVWKeaxonZgMBPQA86GV92t",
            cost=0.001,
        ),
    )
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
