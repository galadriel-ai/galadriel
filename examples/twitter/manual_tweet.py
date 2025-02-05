import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import List
from typing import Optional

from dotenv import load_dotenv

from galadriel_agent.agent import AgentInput
from galadriel_agent.agent import AgentOutput
from galadriel_agent.agent import AgentRuntime
from galadriel_agent.connectors.llm import LlmClient
from galadriel_agent.connectors.perplexity import PerplexityClient
from galadriel_agent.entities import Message
from galadriel_agent.entities import PushOnlyQueue
from galadriel_agent.tools.twitter import TwitterGetPostTool
from galadriel_agent.tools.twitter import TwitterSearchTool
from src.agent.twitter_post_agent import TwitterPostAgent
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.repository.database import DatabaseClient
from src.twitter_client import TwitterClient


async def main(agent_name: str, tweet_id: Optional[str]):
    agent_config = _load_agent_config(agent_name)
    llm_client = LlmClient()
    database_client = DatabaseClient()
    post_agent = TwitterPostAgent(
        agent_config=agent_config,
        llm_client=llm_client,
        database_client=database_client,
        perplexity_client=PerplexityClient(os.getenv("PERPLEXITY_API_KEY", "")),
        twitter_search_tool=TwitterSearchTool(),
        twitter_get_post_tool=TwitterGetPostTool(),
    )

    output_client = OutputClient()
    galadriel_agent = AgentRuntime(
        inputs=[TestingTwitterClient(tweet_id)],
        outputs=[output_client],
        agent=post_agent,
    )
    task = asyncio.create_task(galadriel_agent.run())

    while True:
        await asyncio.sleep(5)
        if output_client.result:
            break
    task.cancel()

    tweet = TwitterPost.from_dict(output_client.result.additional_kwargs)
    print("Got generated tweet: ")
    print(tweet.text)
    should_post = ""
    while should_post not in ["y", "n"]:
        should_post = input("Should post? (y/n): ").strip().lower()

    if should_post == "n":
        print("Skipping posting tweet")
        return
    print("Posting tweet!")

    twitter_client = TwitterClient(
        agent=agent_config,
        database_client=database_client,
    )
    await twitter_client.send(
        Message(content=""),
        output_client.result,
        "",
    )


class TestingTwitterClient(AgentInput):
    tweet_id: str

    def __init__(self, tweet_id: str):
        self.tweet_id = tweet_id

    async def start(self, queue: PushOnlyQueue) -> None:
        await queue.put(
            Message(
                content="",
                type="tweet_original",
                additional_kwargs={
                    "quote_tweet_id": self.tweet_id,
                }
            ),
        )


class OutputClient(AgentOutput):
    result: Optional[Message]

    async def send(self, request: Message, response: Message, proof: str) -> None:
        print("GOT GENERATED TWEET ============================")
        tweet = TwitterPost.from_dict(response.additional_kwargs)
        print(json.dumps(tweet.to_dict(), indent=4))
        self.result = response


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


def _load_agent_config(agent_name: str) -> TwitterAgentConfig:
    _load_dotenv()
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
    parser = argparse.ArgumentParser(
        description="Parse command line arguments.")
    parser.add_argument(
        "--name",
        default="agent",
        help="Specify the agent name. The agent configuration file needs to exist in `agent_configurator/{name}.json`."
    )
    parser.add_argument(
        "--tweet_id",
        default=None,
        required=False,
        help="Specify the tweet ID to generate a quote for."
    )
    args = parser.parse_args()

    asyncio.run(
        main(args.name, args.tweet_id)
    )
