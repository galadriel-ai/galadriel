import logging
from typing import Dict
from typing import List
from typing import Optional

from galadriel.agent import AgentInput
from galadriel.agent import AgentOutput
from galadriel.connectors.twitter import TwitterApiClient
from galadriel.connectors.twitter import TwitterCredentials
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue
from galadriel.entities import Proof


class TwitterMentionClient(TwitterApiClient, AgentInput, AgentOutput):
    """A client for handling Twitter mentions and responses.

    This class extends TwitterApiClient and implements both AgentInput and AgentOutput
    interfaces to provide bidirectional communication with Twitter. It monitors mentions
    of the authenticated user and can post replies to tweets.

    Attributes:
        user_id (str): The Twitter user ID to monitor for mentions
        logger (logging.Logger): Logger instance for tracking client activities
    """

    def __init__(
        self,
        _credentials: TwitterCredentials,
        user_id: str,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the Twitter mentions client.

        Args:
            _credentials (TwitterCredentials): Authentication credentials for Twitter API
            user_id (str): The Twitter user ID to monitor for mentions
            logger (Optional[logging.Logger]): Custom logger instance. If None,
                                             creates a default logger
        """
        super().__init__(_credentials)
        self.user_id = user_id
        self.logger = logger or logging.getLogger("twitter_mention_client")

    async def start(self, queue: PushOnlyQueue) -> None:
        """Begin monitoring Twitter mentions and queueing them for processing.

        Fetches recent mentions of the authenticated user and converts them
        to Message objects for processing by the agent.

        Args:
            queue (PushOnlyQueue): Queue for storing messages to be processed

        Note:
            Each mention is converted to a Message with the tweet's text,
            conversation ID, and additional metadata including the tweet ID
            and author ID.
        """
        mentions = await self._fetch_mentions(self.user_id)
        for mention in mentions:
            message = Message(
                content=mention["text"],
                conversation_id=mention["conversation_id"],
                additional_kwargs={
                    "tweet_id": mention["tweet_id"],
                    "author": mention["author_id"],
                },
            )
            await queue.put(message)

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Post a reply to a Twitter mention.

        If the original request contains a tweet_id, posts the response
        as a reply to that tweet.

        Args:
            request (Message): The original mention message containing the tweet_id
            response (Message): The response to post as a reply

        Note:
            The response will only be posted if the original request contains
            a valid tweet_id in its additional_kwargs.
        """
        if request.additional_kwargs and (tweet_id := request.additional_kwargs.get("tweet_id")):
            await self._post_reply(tweet_id, response.content)

    async def _fetch_mentions(self, user_id: str) -> List[Dict]:
        """Fetch recent mentions of the specified user from Twitter.

        Retrieves up to 20 recent mentions of the user, including tweet ID,
        author ID, conversation ID, and text content.

        Args:
            user_id (str): The Twitter user ID to fetch mentions for

        Returns:
            List[Dict]: A list of mention data dictionaries

        Raises:
            Exception: If the Twitter API request fails

        Note:
            The API request includes tweet and user fields for comprehensive
            mention data.
        """
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
        """Post a reply to a specific tweet.

        Args:
            reply_to_id (str): The ID of the tweet to reply to
            message (str): The content of the reply tweet

        Returns:
            Optional[Dict]: The Twitter API response data if successful

        Note:
            Logs a success message when the tweet is posted successfully.
        """
        response = self._make_request(
            "POST",
            "tweets",
            json={"text": message, "reply": {"in_reply_to_tweet_id": reply_to_id}},
        )
        self.logger.info(f"Tweet posted successfully: {message}")
        return response
