"""
This module provides tools for interacting with Twitter's API, enabling
posting tweets, searching tweets, retrieving replies, and fetching specific
tweets.

Key Features:
- Post tweets and replies
- Search tweets by query
- Get replies to specific tweets
- Fetch individual tweets by ID

Required Environment Variables:
    TWITTER_CONSUMER_API_KEY: Twitter API consumer key
    TWITTER_CONSUMER_API_SECRET: Twitter API consumer secret
    TWITTER_ACCESS_TOKEN: Twitter access token
    TWITTER_ACCESS_TOKEN_SECRET: Twitter access token secret
"""

import json
import os
from typing import Dict, Optional

from galadriel.tools import Tool
from galadriel.connectors.twitter import TwitterApiClient, TwitterCredentials
from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()

# Tool name constants
TWITTER_POST_TOOL_NAME = "twitter_post_tool"
TWITTER_SEARCH_TOOL_NAME = "twitter_search_tool"
TWITTER_REPLIES_TOOL_NAME = "twitter_replies_tool"
TWITTER_GET_POST_TOOL_NAME = "twitter_get_post_tool"


class CredentialsException(Exception):
    """Exception raised for Twitter credentials issues.

    Raised when required Twitter API credentials are missing or invalid.
    """


class TwitterPostTool(TwitterApiClient, Tool):
    """Tool for posting tweets to Twitter.

    Enables posting new tweets and replies to existing tweets using
    Twitter's API v2.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = TWITTER_POST_TOOL_NAME
    description = (
        "This is a tool that posts a tweet to twitter. It returns a boolean indicating if the posting was successful."
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
        """Initialize the Twitter post tool.

        Args:
            _credentials (Optional[TwitterCredentials]): Twitter API credentials.
                If None, credentials are loaded from environment variables.

        Raises:
            CredentialsException: If required credentials are missing
        """
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, tweet: str, in_reply_to_id: str) -> Dict:  # pylint:disable=W0221
        """Post a tweet or reply to Twitter.

        Args:
            tweet (str): The content of the tweet to post
            in_reply_to_id (str): ID of tweet to reply to, or empty string

        Returns:
            Dict: Response data from Twitter API

        Note:
            Returns empty dict if posting fails
        """
        response = self.post_tweet(tweet, in_reply_to_id)
        return response or {}


class TwitterSearchTool(TwitterApiClient, Tool):
    """Tool for searching tweets on Twitter.

    Enables searching for tweets using Twitter's API v2 search functionality.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

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
        """Initialize the Twitter search tool.

        Args:
            _credentials (Optional[TwitterCredentials]): Twitter API credentials.
                If None, credentials are loaded from environment variables.

        Raises:
            CredentialsException: If required credentials are missing
        """
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, search_query: str) -> str:  # pylint:disable=W0221
        """Search for tweets matching a query.

        Args:
            search_query (str): The search query to execute

        Returns:
            str: JSON string containing search results
        """
        results = self.search(search_query)
        formatted_results = [r.to_dict() for r in results]
        return json.dumps(formatted_results)


class TwitterRepliesTool(TwitterApiClient, Tool):
    """Tool for retrieving replies to a tweet.

    Enables fetching all replies to a specific tweet using Twitter's API v2.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = TWITTER_REPLIES_TOOL_NAME
    description = "This is a tool that gets replies to a tweet. It returns a list of results."
    inputs = {
        "conversation_id": {
            "type": "string",
            "description": "The conversation ID. It is set after the original tweet ID",
        },
    }
    output_type = "string"

    def __init__(self, _credentials: Optional[TwitterCredentials] = None):
        """Initialize the Twitter replies tool.

        Args:
            _credentials (Optional[TwitterCredentials]): Twitter API credentials.
                If None, credentials are loaded from environment variables.

        Raises:
            CredentialsException: If required credentials are missing
        """
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, conversation_id: str) -> str:  # pylint:disable=W0221
        """Fetch replies to a specific tweet.

        Args:
            conversation_id (str): ID of the conversation to fetch replies from

        Returns:
            str: JSON string containing reply tweets
        """
        results = self.get_replies(conversation_id)
        formatted_results = [r.to_dict() for r in results]
        return json.dumps(formatted_results)


class TwitterGetPostTool(TwitterApiClient, Tool):
    """Tool for retrieving a specific tweet by ID.

    Enables fetching a single tweet's content and metadata using Twitter's API v2.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = TWITTER_GET_POST_TOOL_NAME
    description = (
        "This is a tool that gets a specific twitter post by its' ID. "
        "If the ID is wrong it will return an empty string."
    )
    inputs = {
        "tweet_id": {
            "type": "string",
            "description": "The tweet ID.",
        },
    }
    output_type = "string"

    def __init__(self, _credentials: Optional[TwitterCredentials] = None):
        """Initialize the Twitter get post tool.

        Args:
            _credentials (Optional[TwitterCredentials]): Twitter API credentials.
                If None, credentials are loaded from environment variables.

        Raises:
            CredentialsException: If required credentials are missing
        """
        if not _credentials:
            credentials = _get_credentials_from_env()
        else:
            credentials = _credentials
        super().__init__(credentials)

    def forward(self, tweet_id: str) -> str:  # pylint:disable=W0221
        """Fetch a specific tweet by ID.

        Args:
            tweet_id (str): The ID of the tweet to fetch

        Returns:
            str: JSON string containing tweet data, or empty string if not found
        """
        result = self.get_tweet(tweet_id)
        if not result:
            return ""
        formatted_result = result.to_dict()
        return json.dumps(formatted_result)


def _get_credentials_from_env() -> TwitterCredentials:
    """Get Twitter API credentials from environment variables.

    Returns:
        TwitterCredentials: Credentials object containing API keys and tokens

    Raises:
        CredentialsException: If any required credentials are missing

    Note:
        Required environment variables:
        - TWITTER_CONSUMER_API_KEY
        - TWITTER_CONSUMER_API_SECRET
        - TWITTER_ACCESS_TOKEN
        - TWITTER_ACCESS_TOKEN_SECRET
    """
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
