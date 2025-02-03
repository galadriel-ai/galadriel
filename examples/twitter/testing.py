import asyncio
import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from galadriel_agent.agent import AgentInput
from galadriel_agent.agent import AgentOutput
from galadriel_agent.agent import AgentRuntime
from galadriel_agent.connectors.llm import LlmClient
from galadriel_agent.entities import Message
from galadriel_agent.entities import PushOnlyQueue
from src.agent.twitter_agent import TwitterAgent
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.repository.database import DatabaseClient


async def main():
    agent_config = _load_agent_config()

    galadriel_client = LlmClient()
    database_client = DatabaseClient()

    # Set up my own agent
    twitter_agent = TwitterAgent(
        agent_config=agent_config,
        llm_client=galadriel_client,
        database_client=database_client,
        # CHANGE THIS TO EITHER "perplexity" OR "search"
        # "perplexity" - uses perplexity to search and generates a tweet
        # "search" - uses twitter search API to do a search and generate a tweet based on that
        original_tweet_type="perplexity",
    )

    galadriel_agent = AgentRuntime(
        inputs=[TestingTwitterClient()],
        outputs=[OutputClient()],
        agent=twitter_agent,
    )
    await galadriel_agent.run()


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


class TestingTwitterClient(AgentInput):

    async def start(self, queue: PushOnlyQueue) -> None:
        await queue.put(
            Message(
                content="",
                type="tweet_original",
            ),
        )


class OutputClient(AgentOutput):

    async def send(self, request: Message, response: Message, proof: str) -> None:
        print("GOT GENERATED TWEET ============================")
        tweet = TwitterPost.from_dict(response.additional_kwargs)
        print(json.dumps(tweet.to_dict(), indent=4))


def _load_agent_config() -> TwitterAgentConfig:
    _load_dotenv()
    agent_name = "daige"
    agent_path = Path("agent_configurator") / f"{agent_name}.json"
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_dict = json.loads(f.read())
    missing_fields: List[str] = [
        field
        for field in TwitterAgentConfig.required_fields()
        if not agent_dict.get(field)
    ]
    if missing_fields:
        raise KeyError(
            f"Character file is missing required fields: {', '.join(missing_fields)}"
        )
    return TwitterAgentConfig.from_json(agent_dict)


if __name__ == "__main__":
    asyncio.run(main())
