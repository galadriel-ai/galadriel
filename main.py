import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel_agent.twitter_post_agent import TwitterPostAgent
from galadriel_agent.clients.twitter import TwitterCredentials


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


if __name__ == "__main__":
    _load_dotenv()
    twitter_credentials = TwitterCredentials(
        consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY"),
        consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )
    agent = TwitterPostAgent(
        api_key=os.getenv("GALADRIEL_API_KEY"),
        agent_name="daige",
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        twitter_credentials=twitter_credentials,
    )
    
    asyncio.run(agent.run())
