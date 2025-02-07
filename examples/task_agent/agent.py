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
        pricing=_get_pricing("agent.json"),
    )
    await agent.run()


def _get_pricing(agent_json_path: str) -> Pricing:
    try:
        with open(agent_json_path, "r", encoding="utf-8") as f:
            agent_config = json.loads(f.read())
    except:
        raise Exception(f"Failed to read pricing {agent_json_path}")
    pricing_config = agent_config.get("pricing", {})
    agent_wallet_address = pricing_config.get("wallet_address")
    if not agent_wallet_address:
        raise Exception(
            f'agent json: {agent_json_path}, is missing ["pricing"]["wallet_address"]'
        )
    task_cost_sol = pricing_config.get("cost")
    if not task_cost_sol:
        raise Exception(
            f'agent json: {agent_json_path}, is missing ["pricing"]["cost"]'
        )
    return Pricing(
        wallet_address=agent_wallet_address,
        cost=task_cost_sol,
    )


if __name__ == "__main__":
    asyncio.run(main())
