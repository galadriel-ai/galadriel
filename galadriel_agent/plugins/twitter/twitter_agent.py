import os
from typing import Dict
from typing import Optional

from galadriel_agent.agent import UserAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.llms.galadriel import GaladrielClient
from galadriel_agent.clients.perplexity import PerplexityClient
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import TwitterAgentConfig
from galadriel_agent.plugins.twitter.twitter_post_agent import TwitterPostAgent
from galadriel_agent.plugins.twitter.twitter_reply_agent import TwitterReplyAgent
from galadriel_agent.tools.twitter import TwitterSearchTool

logger = get_agent_logger()


class TwitterAgent(UserAgent):
    reply_agent: Optional[TwitterReplyAgent]
    post_agent: Optional[TwitterPostAgent]

    def __init__(
        self,
        agent_config: TwitterAgentConfig,
        llm_client: GaladrielClient,
        database_client: DatabaseClient,
    ):
        self.reply_agent = TwitterReplyAgent(
            agent_config=agent_config,
            llm_client=llm_client,
            database_client=database_client,
        )
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if perplexity_api_key:
            self.post_agent = TwitterPostAgent(
                agent_config=agent_config,
                llm_client=llm_client,
                database_client=database_client,
                perplexity_client=PerplexityClient(perplexity_api_key),
                twitter_search_tool=TwitterSearchTool(),
            )
        else:
            logger.warning("Missing PERPLEXITY_API_KEY in .env, skipping TwitterPostAgent initialization")

    async def run(self, request: Dict) -> Dict:
        request_type = request.get("type")
        if request_type == "tweet_reply" and self.reply_agent:
            return await self.reply_agent.run(request)
        if request_type == "tweet_original" and self.post_agent:
            return await self.post_agent.run(request)
