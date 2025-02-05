from typing import Dict
from typing import List
from typing import Optional

from galadriel import AgentInput, AgentOutput
from galadriel.connectors.twitter import TwitterApiClient
from galadriel.connectors.twitter import TwitterCredentials
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue


class TwitterMentionClient(TwitterApiClient, AgentInput, AgentOutput):
    def __init__(self, _credentials: TwitterCredentials, user_id: str):
        super().__init__(_credentials)
        self.user_id = user_id

    async def start(self, queue: PushOnlyQueue) -> None:
        mentions = await self._fetch_mentions(self.user_id)
        for mention in mentions:
            message = Message(content=mention)
            await queue.put(message)

    async def send(self, request: Message, response: Message, proof: str) -> None:
        await self._post_reply(
            response.additional_kwargs["reply_to_id"], response.content
        )

    async def _fetch_mentions(self, user_id: str) -> List[Dict]:
        try:
            response = await self._make_request(
                "GET",
                f"users/{user_id}/mentions",
                params={
                    "tweet.fields": "id,author_id,conversation_id,text",
                    "user.fields": "name,username",
                    "max_results": 20,
                },
            )
            tweets = response.get("data", [])
            print(tweets)
            return tweets
        except Exception as e:
            print(f"Error fetching mentions: {e}")
            return []

    async def _post_reply(self, reply_to_id: str, message: str) -> Optional[Dict]:
        response = await self._make_request(
            "POST",
            "tweets",
            json={"text": message, "reply": {"in_reply_to_tweet_id": reply_to_id}},
        )
        print(f"Tweet posted successfully: {message}")
        return response
