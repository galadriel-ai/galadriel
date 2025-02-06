import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import List
from typing import Optional

from dotenv import load_dotenv

from galadriel.agent import AgentInput
from galadriel.agent import AgentOutput
from galadriel.agent import AgentRuntime
from galadriel.connectors.llm import LlmClient
from galadriel.connectors.perplexity import PerplexityClient
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue
from galadriel.tools.twitter import TwitterGetPostTool
from galadriel.tools.twitter import TwitterSearchTool
from src.agent.twitter_post_agent import TwitterPostAgent
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.repository.database import DatabaseClient
from src.twitter_client import TwitterClient


async def main(
    agent_name: str,
    tweet_id: Optional[str],
    context_file: Optional[str],
):
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

    input_client = TestingTwitterClient(
        tweet_id,
        context_file,
    )
    output_client = OutputClient()
    galadriel_agent = AgentRuntime(
        inputs=[input_client],
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
    tweet_id: Optional[str]
    context: Optional[str]

    def __init__(
        self,
        tweet_id: Optional[str],
        context_file: Optional[str],
    ):
        self.tweet_id = tweet_id
        if context_file:
            with open(context_file, "r", encoding="utf-8") as f:
                self.context = f.read()
        if not self.tweet_id and not self.context:
            raise Exception("Either `tweet_id` or `context_file` file is needed")

    async def start(self, queue: PushOnlyQueue) -> None:
        if self.tweet_id:
            await queue.put(
                Message(
                    content="",
                    type="tweet_original",
                    additional_kwargs={
                        "quote_tweet_id": self.tweet_id,
                    },
                ),
            )
        if self.context:
            await queue.put(
                Message(
                    content="",
                    type="tweet_original",
                    additional_kwargs={
                        "tweet_context": self.context,
                    },
                ),
            )


class OutputClient(AgentOutput):
    result: Optional[Message]

    def __init__(self):
        self.result = None

    async def send(self, request: Message, response: Message) -> None:
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
        description="Generate a tweet manually with a tweet to quote."
    )
    parser.add_argument(
        "--name",
        default="agent",
        help="Specify the agent name. The agent configuration file needs to exist in `agent_configurator/{name}.json`.",
    )
    parser.add_argument(
        "--tweet_id",
        default=None,
        required=False,
        help="Specify the tweet ID to generate a quote for.",
    )
    parser.add_argument(
        "--context_file",
        default=None,
        required=False,
        help="Specify the file path for the context to generate a tweet about.",
    )
    args = parser.parse_args()

    tweet_id = args.tweet_id
    context_file = args.context_file
    if not tweet_id and not context_file:
        raise Exception("Either --tweet_id or --context_file is necessary.")

    asyncio.run(main(args.name, tweet_id, context_file))
