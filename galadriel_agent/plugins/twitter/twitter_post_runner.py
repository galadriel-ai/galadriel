import asyncio
import json
import random
from typing import Dict
from typing import List
from typing import Optional

from galadriel_agent import utils
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.llms.galadriel import GaladrielClient
from galadriel_agent.clients.perplexity import PerplexityClient
from galadriel_agent.clients.twitter import SearchResult
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.prompts import format_prompt
from galadriel_agent.prompts import get_default_prompt_state_use_case
from galadriel_agent.prompts import get_search_query
from galadriel_agent.responses import format_response
from galadriel_agent.tools.twitter import TwitterPostTool
from galadriel_agent.tools.twitter import TwitterSearchTool

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


class TwitterPostRunner(GaladrielAgent):
    agent: AgentConfig

    database_client: DatabaseClient
    llm_client: GaladrielClient

    twitter_post_tool: TwitterPostTool
    # TODO: Optional?
    twitter_search_tool: TwitterSearchTool

    perplexity_client: PerplexityClient

    post_interval_minutes_min: int
    post_interval_minutes_max: int

    def __init__(
        self,
        agent: AgentConfig,
        llm_client: GaladrielClient,
        twitter_post_tool: TwitterPostTool,
        twitter_search_tool: TwitterSearchTool,
        database_client: DatabaseClient,
        perplexity_client: PerplexityClient,
        post_interval_minutes_min: int,
        post_interval_minutes_max: int,
    ):
        self.agent = agent

        self.llm_client = llm_client
        self.database_client = database_client

        self.twitter_post_tool = twitter_post_tool
        self.twitter_search_tool = twitter_search_tool

        self.perplexity_client = perplexity_client

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max

    async def run(self) -> None:
        await self._run_loop()

    async def _run_loop(self) -> None:
        tweets = await self.database_client.get_tweets()
        latest_tweet: Optional[Memory] = None
        for tweet in reversed(tweets):
            if not tweet.reply_to_id:
                latest_tweet = tweet
                break
        if last_tweet_timestamp := (latest_tweet and latest_tweet.timestamp):
            minutes_passed = int(
                (utils.get_current_timestamp() - last_tweet_timestamp) / 60
            )
            if minutes_passed > self.post_interval_minutes_min:
                logger.info(
                    f"Last tweet happened {minutes_passed} minutes ago, generating new tweet immediately"
                )
            else:
                sleep_time = random.randint(
                    self.post_interval_minutes_min - minutes_passed,
                    self.post_interval_minutes_max - minutes_passed,
                )
                logger.info(
                    f"Last tweet happened {minutes_passed} minutes ago, waiting for {sleep_time} minutes"
                )
                await asyncio.sleep(sleep_time * 60)

        while True:
            await self._generate_original_tweet()
            sleep_time = random.randint(
                self.post_interval_minutes_min,
                self.post_interval_minutes_max,
            )
            logger.info(f"Next Tweet scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _generate_original_tweet(self):
        # TODO:
        # if random.random() < 0.4:
        if random.random() < 0:
            is_post_quote_success = await self._post_quote()
            if not is_post_quote_success:
                await self._post_perplexity_tweet_with_retries()
        else:
            await self._post_perplexity_tweet_with_retries()

    async def _post_perplexity_tweet_with_retries(self):
        for i in range(TWEET_RETRY_COUNT):
            is_success = await self._post_perplexity_tweet()
            if is_success:
                break
            if i < TWEET_RETRY_COUNT:
                logger.info(
                    f"Failed to post tweet, retrying, attempts made: {i + 1}/{TWEET_RETRY_COUNT}"
                )
                await asyncio.sleep(i * 5)

    async def _post_perplexity_tweet(self) -> bool:
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
            return False
        if response and response.choices and response.choices[0].message:
            message = response.choices[0].message.content or ""
            formatted_message = format_response.execute(message)
            if not formatted_message:
                await self.database_client.add_memory(
                    Memory(
                        id=f"{utils.get_current_timestamp()}",
                        conversation_id=None,
                        type="tweet_excluded",
                        text=message,
                        topics=prompt_state.get("topics_data", []),
                        timestamp=utils.get_current_timestamp(),
                        search_topic=prompt_state.get("search_topic"),
                        quoted_tweet_id=None,
                        quoted_tweet_username=None,
                    )
                )
                return False
            twitter_response = self.twitter_post_tool(formatted_message, "")
            if tweet_id := (
                twitter_response and twitter_response.get("data", {}).get("id")
            ):
                logger.debug(f"Tweet ID: {tweet_id}")
                await self.database_client.add_memory(
                    Memory(
                        id=tweet_id,
                        conversation_id=tweet_id,
                        type="tweet",
                        text=formatted_message,
                        topics=prompt_state.get("topics_data", []),
                        timestamp=utils.get_current_timestamp(),
                        search_topic=prompt_state.get("search_topic"),
                        quoted_tweet_id=None,
                        quoted_tweet_username=None,
                    )
                )
                return True
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return False

    async def _post_quote(self) -> bool:
        logger.info("Generating tweet with quote")
        # TODO: check if exists etc, part of what kind of flow to do
        results = self.twitter_search_tool()
        if not results:
            logger.info("Failed to get twitter search results")
            return False
        formatted_results = [SearchResult.from_dict(r) for r in json.loads(results)]
        filtered_tweets = await self._filter_quote_candidates(formatted_results)
        if not filtered_tweets:
            logger.info("No relevant tweets found, skipping")
            return False

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
            return False
        if (
            response.choices
            and response.choices[0].message
            and response.choices[0].message.content
        ):
            message = response.choices[0].message.content + " " + quote_url
            twitter_response = self.twitter_post_tool(message, "")
            if tweet_id := (
                twitter_response and twitter_response.get("data", {}).get("id")
            ):
                logger.debug(f"Tweet ID: {tweet_id}")
                await self.database_client.add_memory(
                    Memory(
                        id=tweet_id,
                        conversation_id=tweet_id,
                        type="tweet",
                        text=message,
                        topics=prompt_state.get("topics_data", []),
                        timestamp=utils.get_current_timestamp(),
                        search_topic=None,
                        quoted_tweet_id=quoted_tweet_id,
                        quoted_tweet_username=quoted_tweet_username,
                    )
                )
                return True
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return False

    async def _get_post_prompt_state(self) -> Dict:
        # TODO: need to update prompt etc etc
        data = await get_default_prompt_state_use_case.execute(
            self.agent, self.database_client,
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
            self.agent, self.database_client,
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
