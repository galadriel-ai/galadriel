import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import List
from typing import Literal

from dotenv import load_dotenv

from galadriel import AgentInput
from galadriel import AgentOutput
from galadriel import AgentRuntime
from galadriel.connectors.llm import LlmClient
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue
from src.agent.twitter_agent import TwitterAgent
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.repository.database import DatabaseClient


async def main(request_type: Literal["perplexity", "search"], count: int):
    agent_config = _load_agent_config()

    galadriel_client = LlmClient()
    database_client = DatabaseClient()

    # Set up my own agent
    twitter_agent = TwitterAgent(
        agent_config=agent_config,
        llm_client=galadriel_client,
        database_client=database_client,
        original_tweet_type=request_type,
    )

    os.makedirs("data", exist_ok=True)
    results_file = f"data/{int(time.time())}_results.json"
    output_client = OutputClient(results_file)
    runtime = AgentRuntime(
        inputs=[TestingTwitterClient(count)],
        outputs=[output_client],
        agent=twitter_agent,
    )
    task = asyncio.create_task(runtime.run())

    while True:
        await asyncio.sleep(5)
        if output_client.count >= count:
            break
    task.cancel()
    print(f"Results saved in {results_file}")


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


class TestingTwitterClient(AgentInput):

    def __init__(self, count: int):
        self.count = count

    async def start(self, queue: PushOnlyQueue) -> None:
        for _ in range(self.count):
            await queue.put(
                Message(
                    content="",
                    type="tweet_original",
                ),
            )


class OutputClient(AgentOutput):

    def __init__(self, file_name: str):
        self.count = 0
        self.file_name = file_name
        with open(self.file_name, "w", encoding="utf-8") as f:
            f.write(json.dumps([]))

    async def send(self, request: Message, response: Message) -> None:
        print("GOT GENERATED TWEET ============================")
        tweet = TwitterPost.from_dict(response.additional_kwargs)
        print(json.dumps(tweet.to_dict(), indent=4))
        try:
            with open(self.file_name, "r", encoding="utf-8") as f:
                results = json.loads(f.read())
            results.append(tweet.to_dict())
            with open(self.file_name, "w", encoding="utf-8") as f:
                f.write(json.dumps(results, indent=4))
        except:
            pass
        self.count += 1


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
    parser = argparse.ArgumentParser(
        description="Generate tweets without posting them."
    )
    parser.add_argument(
        "--type",
        choices=["perplexity", "search"],
        default="perplexity",
        help="Specify the type (perplexity or search). Defaults to perplexity.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Specify the count as an integer. Defaults to 5.",
    )

    args = parser.parse_args()

    print(f"Type: {args.type}")
    print(f"Count: {args.count}")
    asyncio.run(main(args.type, args.count))
