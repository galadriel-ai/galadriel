import asyncio
import json
import random
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from galadriel_agent.agent import Agent
from galadriel_agent.connectors.llm import LlmClient
from galadriel_agent.connectors.perplexity import PerplexityClient
from galadriel_agent.connectors.twitter import SearchResult
from galadriel_agent.domain.prompts import format_prompt
from galadriel_agent.entities import Message
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.tools.twitter import TwitterSearchTool
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.prompts import get_default_prompt_state_use_case
from src.prompts import get_search_query
from src.repository.database import DatabaseClient
from src.responses import format_response

logger = get_agent_logger()

PROMPT_TEMPLATE = """# Areas of Expertise
{{knowledge}}

# About {{agent_name}} (@{{twitter_user_name}}):
{{bio}}
{{lore}}
{{topics}}

{{post_directions}}

# Task: Generate a post in the voice and style and perspective of {{agent_name}} @{{twitter_user_name}}.
Write a 1-3 sentence post that is tech-savvy based on the latest trending news you read, here's what you read:

"{{perplexity_content}}"

Here are the citations, where you read about this:
{{perplexity_sources}}

You have to address what you read directly. Be brief, and concise, add a statement in your voice. The total character count MUST be less than 280. No emojis. Use \n\n (double spaces) between statements.
"""

PROMPT_QUOTE_TEMPLATE = """
# Areas of Expertise
{{knowledge}}

# About {{agent_name}} (@{{twitter_user_name}}):
{{bio}}
{{lore}}
{{topics}}

{{post_directions}}

# Task: Generate a post/reply in the voice, style and perspective of {{agent_name}} (@{{twitter_user_name}}) while using the thread of tweets as additional context:

Thread of Tweets You Are Replying To:
{{quote}}
"""

TWEET_RETRY_COUNT = 3
# How many tweets between last quote from the same user
QUOTED_USER_REOCCURRENCE_LIMIT = 3


class TwitterPostAgent(Agent):
    agent: TwitterAgentConfig

    database_client: DatabaseClient
    llm_client: LlmClient

    twitter_search_tool: Optional[TwitterSearchTool]

    perplexity_client: PerplexityClient

    post_interval_minutes_min: int
    post_interval_minutes_max: int

    tweet_type: Optional[Literal["perplexity", "search"]]

    def __init__(
        self,
        agent_config: TwitterAgentConfig,
        llm_client: LlmClient,
        database_client: DatabaseClient,
        perplexity_client: PerplexityClient,
        twitter_search_tool: Optional[TwitterSearchTool] = None,
        tweet_type: Optional[Literal["perplexity", "search"]] = None
    ):
        self.agent = agent_config

        self.llm_client = llm_client
        self.database_client = database_client

        self.perplexity_client = perplexity_client

        self.twitter_search_tool = twitter_search_tool

        self.tweet_type = tweet_type

    async def execute(self, request: Message) -> Message:
        request_type = request.type
        if request_type and request_type == "tweet_original":
            response = await self._generate_original_tweet()
            if response:
                return response
            raise Exception("Error running agent")
        logger.debug(
            f"TwitterClient got unexpected request_type: {request_type}, skipping"
        )

    async def _generate_original_tweet(self) -> Message:
        if self.tweet_type:
            if self.tweet_type == "perplexity":
                response = await self._post_perplexity_tweet_with_retries()
            else:
                response = await self._post_quote()
            if not response:
                raise Exception("Error generating tweet")
            return response

        if random.random() < 0.4 and self.twitter_search_tool:
            response = await self._post_quote()
            if response:
                return response
            response = await self._post_perplexity_tweet_with_retries()
        else:
            response = await self._post_perplexity_tweet_with_retries()
        if response:
            return response
        raise Exception("Error running agent")

    async def _post_perplexity_tweet_with_retries(self) -> Optional[Message]:
        for i in range(TWEET_RETRY_COUNT):
            response = await self._post_perplexity_tweet()
            if response:
                return response
            if i < TWEET_RETRY_COUNT:
                logger.info(
                    f"Failed to post tweet, retrying, attempts made: {i + 1}/{TWEET_RETRY_COUNT}"
                )
                await asyncio.sleep(i * 5)

    async def _post_perplexity_tweet(self) -> Optional[Message]:
        logger.info("Generating tweet with perplexity")
        prompt_state = await self._get_post_prompt_state()

        prompt = format_prompt.execute(PROMPT_TEMPLATE, prompt_state)
        logger.debug(f"Got full formatted prompt: \n{prompt}")

        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        response = await self.llm_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages  # type: ignore
        )
        if not response:
            logger.error("No API response from Galadriel")
            return None
        if response and response.choices and response.choices[0].message:
            message = response.choices[0].message.content or ""
            formatted_message = format_response.execute(message)
            if not formatted_message:
                return Message(
                    content="",
                    conversation_id=None,
                    type="tweet_excluded",
                    additional_kwargs=TwitterPost(
                        type="tweet_excluded",
                        conversation_id=None,
                        text=message,
                        topics=prompt_state.get("topics_data", []),
                        search_topic=prompt_state.get("search_topic"),
                        quoted_tweet_id=None,
                        quoted_tweet_username=None,
                    ).to_dict(),
                )

            return Message(
                content="",
                conversation_id=None,
                type="tweet",
                additional_kwargs=TwitterPost(
                    type="tweet",
                    conversation_id=None,
                    text=formatted_message,
                    topics=prompt_state.get("topics_data", []),
                    search_topic=prompt_state.get("search_topic"),
                    quoted_tweet_id=None,
                    quoted_tweet_username=None,
                ).to_dict(),
            )
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return None

    async def _post_quote(self) -> Optional[Message]:
        logger.info("Generating tweet with quote")
        results = self.twitter_search_tool(
            self.agent.extra_fields["twitter_profile"].get("search_query", "")
        )
        if not results:
            logger.info("Failed to get twitter search results")
            return None
        formatted_results = [SearchResult.from_dict(r) for r in json.loads(results)]
        filtered_tweets = await self._filter_quote_candidates(formatted_results)
        if not filtered_tweets:
            logger.info("No relevant tweets found, skipping")
            return None

        quoted_tweet_id = filtered_tweets[0].id
        quoted_tweet_username = filtered_tweets[0].username
        quote_url = f"https://x.com/{quoted_tweet_username}/status/{quoted_tweet_id}"

        prompt_state = await self._get_quote_prompt_state(filtered_tweets[0].text)
        prompt = format_prompt.execute(PROMPT_QUOTE_TEMPLATE, prompt_state)
        logger.debug(f"Got full formatted quote prompt: \n{prompt}")

        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        response = await self.llm_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages  # type: ignore
        )
        if not response:
            logger.error("No API response from Galadriel")
            return None
        if (
            response.choices
            and response.choices[0].message
            and response.choices[0].message.content
        ):
            message = response.choices[0].message.content
            formatted_message = format_response.execute(message)
            if not formatted_message:
                return Message(
                    content="",
                    conversation_id=None,
                    type="tweet_excluded",
                    additional_kwargs=TwitterPost(
                        type="tweet_excluded",
                        conversation_id=None,
                        text=message,
                        topics=prompt_state.get("topics_data", []),
                        search_topic=None,
                        quoted_tweet_id=quoted_tweet_id,
                        quoted_tweet_username=quoted_tweet_username,
                    ).to_dict(),
                )
            formatted_message = formatted_message + " " + quote_url
            return Message(
                content="",
                conversation_id=None,
                type="tweet",
                additional_kwargs=TwitterPost(
                    type="tweet",
                    conversation_id=None,
                    text=formatted_message,
                    topics=prompt_state.get("topics_data", []),
                    search_topic=None,
                    quoted_tweet_id=quoted_tweet_id,
                    quoted_tweet_username=quoted_tweet_username,
                ).to_dict(),
            )
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return None

    async def _get_post_prompt_state(self) -> Dict:
        data = await get_default_prompt_state_use_case.execute(
            self.agent,
            self.database_client,
        )

        search_query = await get_search_query.execute(self.agent, self.database_client)
        data["search_topic"] = search_query.topic
        perplexity_result = await self.perplexity_client.search_topic(
            search_query.query
        )
        if perplexity_result:
            data["perplexity_content"] = perplexity_result.content
            data["perplexity_sources"] = perplexity_result.sources
        else:
            # What to do if perplexity call fails?
            data["perplexity_content"] = ""
            data["perplexity_sources"] = ""

        return data

    async def _get_quote_prompt_state(self, quote: str) -> Dict:
        data = await get_default_prompt_state_use_case.execute(
            self.agent,
            self.database_client,
        )
        data["quote"] = quote
        return data

    async def _filter_quote_candidates(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        filtered_tweets = [
            tweet
            for tweet in results
            if ("https:" not in tweet.text and tweet.attachments is None)
        ]
        existing_tweets = await self.database_client.get_tweets()
        existing_quoted_ids = [
            t.quoted_tweet_id for t in existing_tweets if t.quoted_tweet_id
        ]
        filtered_tweets = [
            tweet for tweet in filtered_tweets if tweet.id not in existing_quoted_ids
        ]

        recently_quoted_users: List[str] = []
        for tweet in reversed(existing_tweets):
            if username := tweet.quoted_tweet_username:
                recently_quoted_users.append(username)
            if len(recently_quoted_users) >= QUOTED_USER_REOCCURRENCE_LIMIT:
                break
        filtered_tweets = [
            tweet
            for tweet in filtered_tweets
            if tweet.username not in recently_quoted_users
        ]

        return filtered_tweets
