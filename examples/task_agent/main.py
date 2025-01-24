import os
import asyncio

from galadriel_agent.agent import AgentConfig
from galadriel_agent.agent import GaladrielAgent

from clients.twitter_mention_client import TwitterCredentials
from clients.twitter_mention_client import TwitterMentionClient
from galadriel_agent.clients.test_client import TestClient
from research_agent import ResearchAgent


async def main():
    twitter_client = TwitterMentionClient(
        TwitterCredentials(
            consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY"),
            consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        ),
        user_id=os.getenv("TWITTER_USER_ID"),
    )
    test_client = TestClient(
        request={
            "id": "mockid123",
            "author_id": "authorid123",
            "conversation_id": "conversationid123",
            "text": "is BTC good investment now with high prices? 5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"
        }
    )
    research_agent = ResearchAgent()
    agent = GaladrielAgent(
        AgentConfig(
            name="task_agent",
            settings={},
            system="",
            bio=[],
            lore=[],
            adjectives=[],
            topics=[],
            style={},
            goals_template=[],
            facts_template=[],
            knowledge=[],
            search_queries={},
        ),
        clients=[test_client],
        user_agent=research_agent,
        s3_client=None,
    )
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
