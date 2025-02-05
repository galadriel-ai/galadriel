import argparse
import asyncio
import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from galadriel import AgentRuntime
from galadriel.connectors.llm import LlmClient
from src.agent.twitter_agent import TwitterAgent
from src.models import TwitterAgentConfig
from src.repository.database import DatabaseClient
from src.twitter_client import TwitterClient


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


async def main(
    agent_name: str
):
    agent_config = _load_agent_config(agent_name)

    galadriel_client = LlmClient()
    database_client = DatabaseClient()
    twitter_client = TwitterClient(
        agent=agent_config,
        database_client=database_client,
    )

    # Set up my own agent
    twitter_agent = TwitterAgent(
        agent_config=agent_config,
        llm_client=galadriel_client,
        database_client=database_client,
    )

    runtime = AgentRuntime(
        inputs=[twitter_client],
        outputs=[twitter_client],
        agent=twitter_agent,
    )
    await runtime.run()


def _load_agent_config(
    agent_name: str
) -> TwitterAgentConfig:
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
        description="Run an agent with a specified configuration file.")
    parser.add_argument(
        "--name",
        default="agent",
        help="Specify the agent name. The agent configuration file needs to exist in `agent_configurator/{name}.json`."
    )
    args = parser.parse_args()

    asyncio.run(main(args.name))
