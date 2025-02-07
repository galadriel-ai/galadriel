import logging
from typing import Dict
from typing import List
from typing import Optional

from galadriel.agent import AgentInput
from galadriel.agent import AgentOutput
from galadriel.connectors.twitter import TwitterApiClient
from galadriel.connectors.twitter import TwitterCredentials
from galadriel.entities import HumanMessage
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue


class TwitterMentionClient(TwitterApiClient, AgentInput, AgentOutput):
    def __init__(
        self, _credentials: TwitterCredentials, user_id: str, logger: Optional[logging.Logger] = None
    ):
        super().__init__(_credentials)
        self.user_id = user_id
        self.logger = logger or logging.getLogger("twitter_mention_client")

    async def start(self, queue: PushOnlyQueue) -> None:
        mentions = await self._fetch_mentions(self.user_id)
        for mention in mentions:
            message = HumanMessage(
                content=mention,
                conversation_id=mention["conversation_id"],
                additional_kwargs={
                    "tweet_id": mention["tweet_id"],
                    "author": mention["author_id"],
                },
            )
            await queue.put(message)

    async def send(self, request: Message, response: Message) -> None:
        if request.additional_kwargs and (
            tweet_id := request.additional_kwargs.get("tweet_id")
        ):
            await self._post_reply(tweet_id, response.content)

    async def _fetch_mentions(self, user_id: str) -> List[Dict]:
        try:
            response = self._make_request(
                "GET",
                f"users/{user_id}/mentions",
                params={
                    "tweet.fields": "id,author_id,conversation_id,text",
                    "user.fields": "name,username",
                    "max_results": 20,
                },
            )
            tweets = response.get("data", [])
            return tweets
        except Exception as e:
            self.logger.error(f"Failed to fetch mentions: {e}")
            return []

    async def _post_reply(self, reply_to_id: str, message: str) -> Optional[Dict]:
        response = self._make_request(
            "POST",
            "tweets",
            json={"text": message, "reply": {"in_reply_to_tweet_id": reply_to_id}},
        )
        self.logger.info(f"Tweet posted successfully: {message}")
        return response
