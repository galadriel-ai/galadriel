import asyncio
from typing import Dict, List, Optional

from galadriel_agent.clients.client import Client
from galadriel_agent.clients.twitter import TwitterClient
from galadriel_agent.clients.twitter import TwitterCredentials


class TwitterMentionClient(TwitterClient, Client):
    def __init__(self, _credentials: TwitterCredentials, user_id: str):
        super().__init__(_credentials)
        self.user_id = user_id

    async def start(self, queue: asyncio.Queue) -> Dict:
        mentions = await self._fetch_mentions(self.user_id)
        for mention in mentions:
            await queue.put(mention)
        return {}

    async def post_output(self, request: Dict, response: Dict, proof: str):
        await self._post_reply(response["reply_to_id"], response["text"])

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
