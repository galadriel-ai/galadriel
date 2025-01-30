import os
import asyncio

from galadriel_agent.agent import AgentRuntime

# from clients.twitter_mention_client import TwitterCredentials
# from clients.twitter_mention_client import TwitterMentionClient
from galadriel_agent.clients.test_client import TestClient
from galadriel_agent.entities import Message
from galadriel_agent.memory.in_memory import InMemoryShortTermMemory
from research_agent import ResearchAgent


async def main():
    """twitter_client = TwitterMentionClient(
        TwitterCredentials(
            consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY"),
            consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        ),
        user_id=os.getenv("TWITTER_USER_ID"),
    )"""
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
    test_client = TestClient(messages=[message1, message2])

    short_term_memory = InMemoryShortTermMemory()

    research_agent = ResearchAgent("agent.json")
    agent = AgentRuntime(
        inputs=[test_client],
        outputs=[test_client],
        agent=research_agent,
        short_term_memory=short_term_memory,
    )
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
