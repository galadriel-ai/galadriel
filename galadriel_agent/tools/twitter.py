import json
import os
from typing import Dict
from typing import Optional

from galadriel_agent.core_agent import Tool

from galadriel_agent.connectors.twitter import TwitterApiClient
from galadriel_agent.connectors.twitter import TwitterCredentials
from galadriel_agent.logging_utils import get_agent_logger

logger = get_agent_logger()

TWITTER_POST_TOOL_NAME = "twitter_post_tool"
TWITTER_SEARCH_TOOL_NAME = "twitter_search_tool"
TWITTER_REPLIES_TOOL_NAME = "twitter_replies_tool"


class CredentialsException(Exception):
    pass


class TwitterPostTool(TwitterApiClient, Tool):
    name = TWITTER_POST_TOOL_NAME
    description = (
        "This is a tool that posts a tweet to twitter. "
        "It returns a boolean indicating if the posting was successful."
    )
    inputs = {
        "tweet": {"type": "string", "description": "The tweet to post to twitter"},
        "in_reply_to_id": {
            "type": "string",
            "description": "The tweet ID to respond to, empty string for NOT replying",
        },
    }
    output_type = "object"

    def __init__(self, _credentials: Optional[TwitterCredentials] = None):
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, tweet: str, in_reply_to_id: str) -> Dict:  # pylint:disable=W0221
        response = self.post_tweet(tweet, in_reply_to_id)
        return response or {}


class TwitterSearchTool(TwitterApiClient, Tool):
    name = TWITTER_SEARCH_TOOL_NAME
    description = "This is a tool that searches tweets. It returns a list of results."
    inputs = {
        "search_query": {
            "type": "string",
            "description": "Search query supported by the Twitter API",
        },
    }
    output_type = "string"

    def __init__(self, _credentials: Optional[TwitterCredentials] = None):
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, search_query: str) -> str:  # pylint:disable=W0221
        results = self.search(search_query)
        return json.dumps(results)


class TwitterRepliesTool(TwitterApiClient, Tool):
    name = TWITTER_REPLIES_TOOL_NAME
    description = (
        "This is a tool that gets replies to a tweet. It returns a list of results."
    )
    inputs = {
        "conversation_id": {
            "type": "string",
            "description": "The conversation ID. It is set after the original tweet ID",
        },
    }
    output_type = "string"

    def __init__(self, _credentials: Optional[TwitterCredentials] = None):
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    # Hacky solution..
    def forward(self, conversation_id: str) -> str:  # pylint:disable=W0221
        results = self.get_replies(conversation_id)
        return json.dumps(results)


def _get_credentials_from_env() -> TwitterCredentials:
    if (
        not os.getenv("TWITTER_CONSUMER_API_KEY")
        or not os.getenv("TWITTER_CONSUMER_API_SECRET")
        or not os.getenv("TWITTER_ACCESS_TOKEN")
        or not os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    ):
        raise CredentialsException("Missing Twitter environment variables")
    return TwitterCredentials(
        consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY", ""),
        consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET", ""),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
    )
