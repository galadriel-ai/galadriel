from typing import Optional

from galadriel import AgentOutput
from galadriel.entities import Message, Proof
from galadriel.tools.twitter import TwitterPostTool


class TwitterPostClient(AgentOutput):
    """A client for posting tweets to Twitter.

    This class implements the AgentOutput interface to enable posting tweets
    to Twitter, including both new tweets and replies to existing tweets.
    It uses TwitterPostTool to handle the actual Twitter API interactions.

    Required Environment Variables:
        TWITTER_CONSUMER_API_KEY
        TWITTER_CONSUMER_API_SECRET
        TWITTER_ACCESS_TOKEN
        TWITTER_ACCESS_TOKEN_SECRET

    For more information about Twitter API credentials, see:
    https://developer.x.com/
    """

    def __init__(self):
        """Initialize the Twitter post client.

        Creates an instance of TwitterPostTool for handling Twitter API
        interactions.
        """
        self.twitter_post_tool = TwitterPostTool()

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Post a tweet or reply to Twitter.

        Posts the response content as a tweet. If the response includes
        an in_reply_to_id in its additional_kwargs, the tweet will be
        posted as a reply to the specified tweet.

        Args:
            request (Message): The original request message (unused)
            response (Message): The message to post as a tweet

        Note:
            To post a reply, the response.additional_kwargs should include:
            {
                "in_reply_to_id": "tweet_id_to_reply_to"  # str
            }
        """
        self.twitter_post_tool(
            response.content,
            in_reply_to_id=(response.additional_kwargs or {}).get("in_reply_to_id"),
        )
