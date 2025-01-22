import asyncio
import json
from pathlib import Path
from typing import List
from typing import Optional

from smolagents import Tool

from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.llms.galadriel import GaladrielClient
from galadriel_agent.clients.perplexity import PerplexityClient
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.logging_utils import init_logging
from galadriel_agent.models import AgentConfig
from galadriel_agent.plugins.twitter.twitter_post_runner import TwitterPostRunner
from galadriel_agent.plugins.twitter.twitter_reply_runner import TwitterReplyRunner
from galadriel_agent.tools.twitter import TWITTER_POST_TOOL_NAME
from galadriel_agent.tools.twitter import TWITTER_REPLIES_TOOL_NAME
from galadriel_agent.tools.twitter import TWITTER_SEARCH_TOOL_NAME
from galadriel_agent.tools.twitter import TwitterPostTool
from galadriel_agent.tools.twitter import TwitterRepliesTool
from galadriel_agent.tools.twitter import TwitterSearchTool

logger = get_agent_logger()


class TwitterPostAgent(GaladrielAgent):
    twitter_reply_runner: Optional[TwitterReplyRunner]

    twitter_post_tool: Tool
    twitter_search_tool: Optional[Tool]
    twitter_replies_tool: Optional[Tool]

    agent_runners: List[GaladrielAgent] = []

    # pylint: disable=R0917:
    def __init__(
        self,
        agent_name: str,
        perplexity_api_key: str,
        tools: List[Tool],
        post_interval_minutes_min: int = 90,
        post_interval_minutes_max: int = 180,
        max_conversations_count_for_replies: int = 3,
    ):
        # super().__init__()
        agent_path = Path("agent_configurator") / f"{agent_name}.json"
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_dict = json.loads(f.read())

        init_logging(agent_dict.get("settings", {}).get("debug"))

        missing_fields: List[str] = [
            field
            for field in AgentConfig.required_fields()
            if not agent_dict.get(field)
        ]
        if missing_fields:
            raise KeyError(
                f"Character file is missing required fields: {', '.join(missing_fields)}"
            )
        # TODO: validate types
        agent = AgentConfig.from_json(agent_dict)

        galadriel_client = GaladrielClient()

        database_client = DatabaseClient(None)

        # Initialize tools
        tool_names = [t.name for t in tools]
        twitter_post_tool: TwitterPostTool
        if TWITTER_POST_TOOL_NAME in tool_names:
            twitter_post_tool = [t for t in tools if t.name == TWITTER_POST_TOOL_NAME][0]
        else:
            raise Exception("Missing tool for posting tweets, exiting")

        if TWITTER_SEARCH_TOOL_NAME in tool_names:
            twitter_search_tool: TwitterSearchTool = [t for t in tools if t.name == TWITTER_SEARCH_TOOL_NAME][0]
            self.agent_runners.append(
                TwitterPostRunner(
                    agent=agent,
                    llm_client=galadriel_client,
                    twitter_post_tool=twitter_post_tool,
                    twitter_search_tool=twitter_search_tool,
                    database_client=database_client,
                    # TODO: from .env
                    perplexity_client=PerplexityClient(perplexity_api_key),
                    post_interval_minutes_min=post_interval_minutes_min,
                    post_interval_minutes_max=post_interval_minutes_max,
                )
            )
        if TWITTER_REPLIES_TOOL_NAME in tool_names:
            self.twitter_replies_tool: TwitterRepliesTool = [t for t in tools if t.name == TWITTER_REPLIES_TOOL_NAME][0]
            self.agent_runners.append(
                TwitterReplyRunner(
                    agent=agent,
                    llm_client=galadriel_client,
                    twitter_replies_tool=self.twitter_replies_tool,
                    twitter_post_tool=twitter_post_tool,
                    database_client=database_client,
                    post_interval_minutes_min=int(post_interval_minutes_min / 4),
                    post_interval_minutes_max=int(post_interval_minutes_max / 4),
                    max_conversations_count_for_replies=max_conversations_count_for_replies
                )
            )

    async def run(self):
        logger.info("Running agents!")
        tasks = [agent.run() for agent in self.agent_runners]
        await asyncio.gather(*tasks)
