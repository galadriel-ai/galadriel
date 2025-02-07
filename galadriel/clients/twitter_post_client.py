from galadriel import AgentOutput
from galadriel.entities import Message
from galadriel.tools.twitter import TwitterPostTool


class TwitterPostClient(AgentOutput):
    """
    Basic Client to post tweets on Twitter, expects the current env values to be present:
    TWITTER_CONSUMER_API_KEY
    TWITTER_CONSUMER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET

    For more info about these see: https://developer.x.com/

    Enables posting Tweets, and posting replies to tweets
    For replying the `response: Message` should have additional_kwargs including:
    ```
        {
            "in_reply_to_id": tweet_id_to_reply_to  # str
        }
    ```
    """

    def __init__(self):
        self.twitter_post_tool = TwitterPostTool()

    async def send(self, request: Message, response: Message) -> None:
        self.twitter_post_tool(
            response.content,
            in_reply_to_id=(response.additional_kwargs or {}).get("in_reply_to_id")
        )
