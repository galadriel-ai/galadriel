import json
import asyncio

from galadriel_agent.agent import AgentRuntime

# from clients.twitter_mention_client import TwitterCredentials
# from clients.twitter_mention_client import TwitterMentionClient
from galadriel_agent.clients.test_client import TestClient
from galadriel_agent.entities import Message
from galadriel_agent.entities import Pricing
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

    research_agent = ResearchAgent()
    agent = AgentRuntime(
        inputs=[test_client],
        outputs=[test_client],
        agent=research_agent,
        short_term_memory=short_term_memory,
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
