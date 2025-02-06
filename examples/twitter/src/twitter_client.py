import asyncio
import json
import random
from typing import Optional

from galadriel import AgentInput, AgentOutput
from galadriel.connectors.twitter import SearchResult
from galadriel.entities import Message, PushOnlyQueue
from galadriel.logging_utils import get_agent_logger
from galadriel.tools.twitter import TwitterPostTool
from galadriel.tools.twitter import TwitterRepliesTool
from src import utils
from src.models import Memory
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.repository.database import DatabaseClient

logger = get_agent_logger()


class TwitterClient(AgentInput, AgentOutput):
    agent: TwitterAgentConfig

    event_queue: PushOnlyQueue

    database_client: DatabaseClient

    twitter_post_tool: TwitterPostTool
    twitter_replies_tool: TwitterRepliesTool

    post_interval_minutes_min: int
    post_interval_minutes_max: int
    max_conversations_count_for_replies: int

    def __init__(
        self,
        agent: TwitterAgentConfig,
        database_client: DatabaseClient,
        post_interval_minutes_min: int = 90,
        post_interval_minutes_max: int = 180,
        max_conversations_count_for_replies: int = 3,
    ):
        self.agent = agent
        self.twitter_username = self.agent.extra_fields.get("twitter_profile", {}).get(
            "username", "user"
        )

        self.twitter_post_tool = TwitterPostTool()
        self.twitter_replies_tool = TwitterRepliesTool()

        self.database_client = database_client

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max
        self.max_conversations_count_for_replies = max_conversations_count_for_replies

    async def start(self, queue: PushOnlyQueue) -> None:
        self.event_queue = queue
        # Should be configurable: which kind of flows to run
        asyncio.create_task(self._run_post_loop())
        asyncio.create_task(self._run_reply_loop())

    async def send(self, _: Message, response: Message) -> None:
        response_type = response.type
        if not response_type or not response.additional_kwargs:
            return
        if response_type == "tweet":
            await self._post_tweet(TwitterPost.from_dict(response.additional_kwargs))
        if response_type == "tweet_excluded":
            twitter_post = TwitterPost.from_dict(response.additional_kwargs)
            await self.database_client.add_memory(
                Memory(
                    id=f"{utils.get_current_timestamp()}",
                    conversation_id=None,
                    type="tweet_excluded",
                    text=twitter_post.text,
                    topics=twitter_post.topics,
                    timestamp=utils.get_current_timestamp(),
                    search_topic=twitter_post.search_topic,
                    quoted_tweet_id=None,
                    quoted_tweet_username=None,
                )
            )

    async def _run_post_loop(self) -> None:
        tweets = await self.database_client.get_tweets()
        latest_tweet: Optional[Memory] = None
        for tweet in reversed(tweets):
            if not tweet.reply_to_id:
                latest_tweet = tweet
                break
        if last_tweet_timestamp := (latest_tweet and latest_tweet.timestamp):
            minutes_passed = int(
                (utils.get_current_timestamp() - last_tweet_timestamp) / 60
            )
            if minutes_passed > self.post_interval_minutes_min:
                logger.info(
                    f"Last tweet happened {minutes_passed} minutes ago, generating new tweet immediately"
                )
            else:
                sleep_time = random.randint(
                    self.post_interval_minutes_min - minutes_passed,
                    self.post_interval_minutes_max - minutes_passed,
                )
                logger.info(
                    f"Last tweet happened {minutes_passed} minutes ago, waiting for {sleep_time} minutes"
                )
                await asyncio.sleep(sleep_time * 60)

        while True:
            await self.event_queue.put(
                Message(
                    content="",
                    type="tweet_original",
                ),
            )
            sleep_time = random.randint(
                self.post_interval_minutes_min,
                self.post_interval_minutes_max,
            )
            logger.info(f"Next Tweet scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _run_reply_loop(self) -> None:
        # sleep_time = random.randint(
        #     int(self.post_interval_minutes_min / 4),
        #     int(self.post_interval_minutes_max / 4),
        # )
        # await asyncio.sleep(sleep_time * 60)

        while True:
            await self._get_replies()
            sleep_time = random.randint(
                int(self.post_interval_minutes_min / 4),
                int(self.post_interval_minutes_max / 4),
            )
            logger.info(f"Next Tweet replies scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _get_replies(self):
        logger.info("Generating replies")

        # Get all conversations
        tweets = await self.database_client.get_tweets()
        conversations = []
        for tweet in reversed(tweets):
            if (
                # if tweet.id == tweet.conversation_id means it's an original tweet
                tweet.conversation_id is not None
                and tweet.id == tweet.conversation_id
            ):
                conversation_id = tweet.conversation_id
                if (
                    conversation_id not in conversations
                    and conversation_id != "dry_run"
                ):
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
                await self.event_queue.put(
                    Message(
                        content="",
                        conversation_id=conversation_id,
                        type="tweet_reply",
                        additional_kwargs=reply.to_dict(),
                    )
                )

    async def _post_tweet(self, twitter_post: TwitterPost) -> bool:
        try:
            twitter_response = self.twitter_post_tool(
                twitter_post.text, twitter_post.reply_to_id or ""
            )
        except Exception:
            logger.error("Failed to post tweet", exc_info=True)
            return False
        if tweet_id := (
            twitter_response and twitter_response.get("data", {}).get("id")
        ):
            logger.debug(f"Tweet ID: {tweet_id}")
            await self.database_client.add_memory(
                Memory(
                    id=tweet_id,
                    conversation_id=twitter_post.conversation_id or tweet_id,
                    type="tweet",
                    text=twitter_post.text,
                    topics=[],
                    timestamp=utils.get_current_timestamp(),
                    search_topic=twitter_post.search_topic,
                    quoted_tweet_id=twitter_post.quoted_tweet_id,
                    quoted_tweet_username=twitter_post.quoted_tweet_username,
                    reply_to_id=twitter_post.reply_to_id,
                )
            )
            return True
