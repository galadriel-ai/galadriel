import asyncio
import json
import random
from typing import Dict

from galadriel_agent import utils
from galadriel_agent.agent import Client
from galadriel_agent.agent import PushOnlyQueue
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.twitter import SearchResult
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.models import TwitterPost
from galadriel_agent.tools.twitter import TwitterPostTool
from galadriel_agent.tools.twitter import TwitterRepliesTool

logger = get_agent_logger()


class TwitterClient(Client):
    agent: AgentConfig

    event_queue: PushOnlyQueue

    database_client: DatabaseClient

    twitter_replies_tool: TwitterRepliesTool
    twitter_post_tool: TwitterPostTool

    post_interval_minutes_min: int
    post_interval_minutes_max: int
    max_conversations_count_for_replies: int

    def __init__(
        self,
        agent: AgentConfig,
        database_client: DatabaseClient,
        post_interval_minutes_min: int = 90,
        post_interval_minutes_max: int = 180,
        max_conversations_count_for_replies: int = 3,
    ):
        self.agent = agent
        self.twitter_username = self.agent.extra_fields.get("twitter_profile", {}).get(
            "username", "user"
        )

        self.twitter_replies_tool = TwitterRepliesTool()
        self.twitter_post_tool = TwitterPostTool()

        self.database_client = database_client

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max
        self.max_conversations_count_for_replies = max_conversations_count_for_replies

    async def start(self, queue: PushOnlyQueue) -> None:
        self.event_queue = queue
        await self._run_loop()

    async def post_output(self, response: Dict, proof: str) -> None:
        if response.get("type") == "tweet":
            await self._post_tweet(TwitterPost.from_dict(response))

    async def _run_loop(self) -> None:
        # sleep_time = random.randint(
        #     int(self.post_interval_minutes_min / 4),
        #     int(self.post_interval_minutes_max / 4),
        # )
        # await asyncio.sleep(sleep_time * 60)

        while True:
            await self._post_replies()
            sleep_time = random.randint(
                int(self.post_interval_minutes_min / 4),
                int(self.post_interval_minutes_max / 4),
            )
            logger.info(f"Next Tweet replies scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _post_replies(self):
        logger.info("Generating replies")

        # Get all conversations
        tweets = await self.database_client.get_tweets()
        conversations = []
        for tweet in reversed(tweets):
            if (
                tweet.quoted_tweet_username is None and tweet.quoted_tweet_id is None
                and tweet.conversation_id is not None
            ):
                conversation_id = tweet.conversation_id
                if conversation_id not in conversations and conversation_id != "dry_run":
                    conversations.append(conversation_id)
            if len(conversations) > self.max_conversations_count_for_replies:
                break

        for conversation_id in conversations:
            replies = self.twitter_replies_tool(conversation_id)
            if not len(replies):
                continue

            formatted_replies = [SearchResult.from_dict(r) for r in json.loads(replies)]
            reply_to_ids = []
            for reply in formatted_replies:
                if reply.username == self.twitter_username:
                    continue
                existing_response = [t for t in tweets if t.reply_to_id == reply.id]
                if len(existing_response) or reply.id in reply_to_ids:
                    continue
                reply_to_ids.append(reply.id)
                # TODO: data format etc
                await self.event_queue.put({
                    "type": "reply",
                    "conversation_id": conversation_id,
                    "reply": reply.to_dict(),
                })

    async def _post_tweet(self, twitter_post: TwitterPost):
        twitter_response = self.twitter_post_tool(twitter_post.text, twitter_post.reply_to_id or "")
        if tweet_id := (
            twitter_response and twitter_response.get("data", {}).get("id")
        ):
            logger.debug(f"Tweet ID: {tweet_id}")
            await self.database_client.add_memory(
                Memory(
                    id=tweet_id,
                    conversation_id=twitter_post.conversation_id,
                    type="tweet",
                    text=twitter_post.text,
                    topics=[],
                    timestamp=utils.get_current_timestamp(),
                    search_topic=None,
                    quoted_tweet_id=None,
                    quoted_tweet_username=None,
                    reply_to_id=twitter_post.reply_to_id,
                )
            )
            return True
