import datetime
import os
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from requests_oauthlib import OAuth1Session

from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()


@dataclass
class TwitterCredentials:
    consumer_api_key: str
    consumer_api_secret: str
    access_token: str
    access_token_secret: str


@dataclass
class SearchResult:
    id: str
    username: str
    text: str
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    impression_count: int
    # Is this needed?
    referenced_tweets: List[Dict]
    attachments: Optional[Dict]

    @staticmethod
    def from_dict(data: Dict) -> "SearchResult":
        return SearchResult(
            id=data["id"],
            username=data["username"],
            text=data["text"],
            retweet_count=data["retweet_count"],
            reply_count=data["reply_count"],
            like_count=data["like_count"],
            quote_count=data["quote_count"],
            bookmark_count=data["bookmark_count"],
            impression_count=data["impression_count"],
            referenced_tweets=data["referenced_tweets"],
            attachments=data["attachments"],
        )

    def to_dict(self) -> Dict:
        return self.__dict__


class TwitterConnectionError(Exception):
    """Base exception for Twitter connection errors"""


class TwitterAPIError(TwitterConnectionError):
    """Raised when Twitter API requests fail"""


MAX_SEARCH_HISTORY_HOURS = 24


class TwitterApiClient:
    oauth_session: OAuth1Session

    def __init__(self, _credentials: TwitterCredentials):
        super().__init__()
        self.oauth_session = OAuth1Session(
            _credentials.consumer_api_key,
            client_secret=_credentials.consumer_api_secret,
            resource_owner_key=_credentials.access_token,
            resource_owner_secret=_credentials.access_token_secret,
        )

    def post_tweet(self, message: str, reply_to_id: Optional[str] = None) -> Optional[Dict]:
        if os.getenv("DRY_RUN"):
            logger.info(f"Would have posted tweet, reply_id: {reply_to_id or ''}: {message}")
            return {"data": {"id": "dry_run"}}
        json_data: Dict = {"text": message}
        if reply_to_id:
            json_data["reply"] = {}
            json_data["reply"]["in_reply_to_tweet_id"] = reply_to_id
        response = self._make_request("POST", "tweets", json=json_data)
        logger.info(f"Tweet posted successfully: {message}")
        return response

    def search(self, search_query: str) -> List[SearchResult]:
        try:
            response = self._make_request(
                "GET",
                "tweets/search/recent",
                params={
                    "query": search_query,
                    "sort_order": "relevancy",
                    "start_time": get_iso_datetime(MAX_SEARCH_HISTORY_HOURS),
                    "tweet.fields": "public_metrics,text,author_id,referenced_tweets,attachments",
                    "expansions": "author_id",
                    "user.fields": "name,username",
                    "max_results": 20,
                },
            )
            # import json
            # with open("search3.json", "w", encoding="utf-8") as f:
            #     f.write(json.dumps(response))
            #
            # import json
            #
            # with open("search3.json", "r", encoding="utf-8") as f:
            #     response = json.loads(f.read())

            return self._format_search_results(response)
        except Exception:
            logger.error("Error searching tweets", exc_info=True)
            return []

    def get_replies(self, conversation_id: str) -> List[SearchResult]:
        response = self._make_request(
            "GET",
            "tweets/search/recent",
            params={
                "query": f"conversation_id:{conversation_id} -is:retweet",
                "sort_order": "relevancy",
                "tweet.fields": "public_metrics,text,author_id,referenced_tweets,attachments",
                "expansions": "author_id",
                "user.fields": "name,username",
                "max_results": 20,
            },
        )
        # response = {
        #     "data": [
        #         {
        #             "id": "1881270962437636217",
        #             "text": "@daigeagi A wallet was found on the sidewalk, and here’s the story...
        # Someone dropped their $daige token, probably because they realized it was worthless! 😂 @daigeagi",
        #             "referenced_tweets": [
        #                 {"type": "replied_to", "id": "1881254564306845956"}
        #             ],
        #             "author_id": "3060443582",
        #             "public_metrics": {
        #                 "retweet_count": 0,
        #                 "reply_count": 0,
        #                 "like_count": 0,
        #                 "quote_count": 0,
        #                 "bookmark_count": 0,
        #                 "impression_count": 30,
        #             },
        #             "edit_history_tweet_ids": ["1881270962437636217"],
        #         },
        #         {
        #             "id": "1881256725409366334",
        #             "text": "@daigeagi ChatGPT's upgrade is impressive but still operates in isolation.
        # The real game-changer will be multi-agentic systems where AI agents collaborate and enhance
        #  each other's capabilities. Speaking of collaborative AI, you should check out @TrulyADog -
        # they're pioneering fascinating… https://t.co/ZhBMLRm8L0",
        #             "referenced_tweets": [
        #                 {"type": "replied_to", "id": "1881254564306845956"}
        #             ],
        #             "author_id": "3063831743",
        #             "public_metrics": {
        #                 "retweet_count": 0,
        #                 "reply_count": 0,
        #                 "like_count": 2,
        #                 "quote_count": 0,
        #                 "bookmark_count": 0,
        #                 "impression_count": 12,
        #             },
        #             "edit_history_tweet_ids": ["1881256725409366334"],
        #         },
        #     ],
        #     "includes": {
        #         "users": [
        #             {
        #                 "id": "3060443582",
        #                 "name": "BullyAI Solana",
        #                 "username": "bullyai_sol",
        #             },
        #             {
        #                 "id": "3063831743",
        #                 "name": "Laur Science (💙,🧡)",
        #                 "username": "laur_science",
        #             },
        #         ]
        #     },
        #     "meta": {
        #         "newest_id": "1881270962437636217",
        #         "oldest_id": "1881256725409366334",
        #         "result_count": 2,
        #     },
        # }
        return self._format_search_results(response)

    def get_tweet(self, tweet_id: str) -> Optional[SearchResult]:
        response = self._make_request(
            "GET",
            f"tweets/{tweet_id}",
            params={
                "tweet.fields": "public_metrics,text,author_id,referenced_tweets,attachments,conversation_id",
                "expansions": "author_id",
                "user.fields": "name,username",
            },
        )
        result = self._format_search_results(
            {
                "data": [response.get("data", [])],
                "includes": response.get("includes", {}),
            }
        )
        if result:
            return result[0]
        return None

    def _make_request(self, method: Literal["GET", "POST"], endpoint: str, **kwargs) -> Dict:
        logger.debug(f"Making {method} request to {endpoint}")
        try:
            oauth = self.oauth_session
            full_url = f"https://api.twitter.com/2/{endpoint.lstrip('/')}"

            response = getattr(oauth, method.lower())(full_url, **kwargs)

            if response.status_code not in [200, 201]:
                logger.error(f"Request failed: {response.status_code} - {response.text}")
                raise TwitterAPIError(f"Request failed with status {response.status_code}: {response.text}")

            logger.debug(f"Request successful: {response.status_code}")
            return response.json()

        except Exception as e:
            raise TwitterAPIError(f"API request failed: {str(e)}")

    def _format_search_results(self, response: Dict) -> List[SearchResult]:
        formatted_results: List[SearchResult] = []
        for result in response.get("data", []):
            public_metrics = result.get("public_metrics", {})
            matching_users = [user for user in response["includes"]["users"] if user["id"] == result["author_id"]]
            if matching_users:
                formatted_results.append(
                    SearchResult(
                        id=result["id"],
                        username=matching_users[0]["username"],
                        text=result["text"],
                        retweet_count=public_metrics.get("retweet_count", 0),
                        reply_count=public_metrics.get("reply_count", 0),
                        like_count=public_metrics.get("like_count", 0),
                        quote_count=public_metrics.get("quote_count", 0),
                        bookmark_count=public_metrics.get("bookmark_count", 0),
                        impression_count=public_metrics.get("impression_count", 0),
                        referenced_tweets=result.get("referenced_tweets", []),
                        attachments=result.get("attachments"),
                    )
                )
        return formatted_results


def get_iso_datetime(hours_back: int = 0) -> str:
    value = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_back)
    return value.strftime("%Y-%m-%dT%H:%M:%S.000Z")
