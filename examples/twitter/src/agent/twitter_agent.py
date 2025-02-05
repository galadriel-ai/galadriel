import os
from typing import Literal
from typing import Optional

from galadriel import Agent
from galadriel.connectors.llm import LlmClient
from galadriel.connectors.perplexity import PerplexityClient
from galadriel.entities import Message
from galadriel.logging_utils import get_agent_logger
from galadriel.tools.twitter import TwitterGetPostTool
from galadriel.tools.twitter import TwitterSearchTool
from src.agent.twitter_post_agent import TwitterPostAgent
from src.agent.twitter_reply_agent import TwitterReplyAgent
from src.models import TwitterAgentConfig
from src.repository.database import DatabaseClient

logger = get_agent_logger()


class TwitterAgent(Agent):
    reply_agent: Optional[TwitterReplyAgent]
    post_agent: Optional[TwitterPostAgent]

    def __init__(
        self,
        agent_config: TwitterAgentConfig,
        llm_client: LlmClient,
        database_client: DatabaseClient,
        original_tweet_type: Optional[Literal["perplexity", "search"]] = None,
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
                twitter_get_post_tool=TwitterGetPostTool(),
                tweet_type=original_tweet_type,
            )
        else:
            logger.warning(
                "Missing PERPLEXITY_API_KEY in .env, skipping TwitterPostAgent initialization"
            )

    async def execute(self, request: Message) -> Message:
        try:
            request_type = request.type
            if request_type:
                if request_type and request_type == "tweet_reply" and self.reply_agent:
                    return await self.reply_agent.execute(request)
                if (
                    request_type
                    and request_type == "tweet_original"
                    and self.post_agent
                ):
                    return await self.post_agent.execute(request)
        except Exception as e:
            logger.error("Error in twitter_agent", exc_info=True)
        return Message(content="")
