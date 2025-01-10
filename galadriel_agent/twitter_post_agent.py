import asyncio
import json
import random
from pathlib import Path
from typing import Dict
from typing import List

from galadriel_agent.responses import format_response

from galadriel_agent import utils
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.galadriel import GaladrielClient
from galadriel_agent.clients.perplexity import PerplexityClient
from galadriel_agent.clients.twitter import TwitterClient
from galadriel_agent.clients.twitter import TwitterCredentials
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.logging_utils import init_logging
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.prompts import format_prompt
from galadriel_agent.prompts import get_search_query

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


class TwitterPostAgent(GaladrielAgent):
    agent: AgentConfig

    perplexity_client: PerplexityClient
    galadriel_client: GaladrielClient
    twitter_client: TwitterClient
    database_client: DatabaseClient

    post_interval_minutes_min: int
    post_interval_minutes_max: int

    # pylint: disable=R0917:
    def __init__(
        self,
        api_key: str,
        agent_name: str,
        perplexity_api_key: str,
        twitter_credentials: TwitterCredentials,
        post_interval_minutes_min: int = 90,
        post_interval_minutes_max: int = 180,
    ):
        agent_path = Path("agent_configurator") / f"{agent_name}.json"
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_dict = json.loads(f.read())

        init_logging(agent_dict.get("settings", {}).get("debug"))

        missing_fields: List[str] = [
            field
            for field in AgentConfig.required_fields()
            if not agent_dict.get(field)
        ]
        if missing_fields:
            raise KeyError(
                f"Character file is missing required fields: {', '.join(missing_fields)}"
            )
        # TODO: validate types
        self.agent = AgentConfig.from_json(agent_dict)

        self.galadriel_client = GaladrielClient(api_key=api_key)
        self.perplexity_client = PerplexityClient(perplexity_api_key)
        self.twitter_client = TwitterClient(twitter_credentials)
        self.database_client = DatabaseClient(None)

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max

    async def run(self):
        logger.info("Running agent!")

        latest_tweet = await self.database_client.get_latest_tweet()
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
            await self._post_tweet()
            sleep_time = random.randint(
                self.post_interval_minutes_min,
                self.post_interval_minutes_max,
            )
            logger.info(f"Next Tweet scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _post_tweet(self):
        if random.random() < 0.4:
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
        response = await self.galadriel_client.completion(
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
            twitter_response = await self.twitter_client.post_tweet(formatted_message)
            if tweet_id := (
                twitter_response and twitter_response.get("data", {}).get("id")
            ):
                logger.debug(f"Tweet ID: {tweet_id}")
                await self.database_client.add_memory(
                    Memory(
                        id=tweet_id,
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
        results = await self.twitter_client.search()
        if not results:
            logger.info("Failed to get twitter search results")
            return False
        filtered_tweets = await self._filter_quote_candidates(results)
        if not filtered_tweets:
            logger.info("No relevant tweets found, skipping")
            return False

        quoted_tweet_id = filtered_tweets[0].id
        quoted_tweet_username = filtered_tweets[0].username
        quote_url = f"https://x.com/{quoted_tweet_username}/status/{quoted_tweet_id}"

        prompt_state = await self._get_reply_prompt_state(filtered_tweets[0].text)
        prompt = format_prompt.execute(PROMPT_QUOTE_TEMPLATE, prompt_state)
        logger.debug(f"Got full formatted quote prompt: \n{prompt}")

        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        response = await self.galadriel_client.completion(
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
            twitter_response = await self.twitter_client.post_tweet(message)
            if tweet_id := (
                twitter_response and twitter_response.get("data", {}).get("id")
            ):
                logger.debug(f"Tweet ID: {tweet_id}")
                await self.database_client.add_memory(
                    Memory(
                        id=tweet_id,
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
        data = await self._get_default_prompt_state()

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

    async def _get_reply_prompt_state(self, quote: str) -> Dict:
        data = await self._get_default_prompt_state()
        data["quote"] = quote
        return data

    async def _get_default_prompt_state(self) -> Dict:
        topics = await self._get_topics()
        return {
            "knowledge": self._get_formatted_knowledge(),
            "agent_name": self.agent.name,
            "twitter_user_name": self.agent.extra_fields.get("twitter_profile", {}).get(
                "username", "user"
            ),
            "bio": self._get_formatted_bio(),
            "lore": self._get_formatted_lore(),
            # This is kind of hacky, needed to get the "topics_data" to save it later
            "topics": self._get_formatted_topics(topics),
            "topics_data": topics,
            "post_directions": self._get_formatted_post_directions(),
        }

    def _get_formatted_knowledge(self):
        shuffled_knowledge = random.sample(
            self.agent.knowledge, len(self.agent.knowledge)
        )
        return "\n".join(shuffled_knowledge[:3])

    def _get_formatted_bio(self) -> str:
        bio = self.agent.bio
        return " ".join(random.sample(bio, min(len(bio), 3)))

    def _get_formatted_lore(self) -> str:
        lore = self.agent.lore
        shuffled_lore = random.sample(lore, len(lore))
        selected_lore = shuffled_lore[:10]
        return "\n".join(selected_lore)

    async def _get_topics(self) -> List[str]:
        topics = self.agent.topics
        recently_used_topics = []
        latest_tweet = await self.database_client.get_latest_tweet()
        if latest_tweet and latest_tweet.topics:
            recently_used_topics = latest_tweet.topics
        available_topics = [
            topic for topic in topics if topic not in recently_used_topics
        ]
        shuffled_topics = random.sample(available_topics, len(available_topics))

        return shuffled_topics[:5]

    def _get_formatted_topics(self, selected_topics: List[str]) -> str:
        formatted_topics = ""
        for index, topic in enumerate(selected_topics):
            if index == len(selected_topics) - 2:
                formatted_topics += topic + " and "
            elif index == len(selected_topics) - 1:
                formatted_topics += topic
            else:
                formatted_topics += topic + ", "
        return f"{self.agent.name} is interested in {formatted_topics}"

    def _get_formatted_post_directions(self) -> str:
        style = self.agent.style
        merged_styles = "\n".join(style.get("all", []) + style.get("post", []))
        return self._add_header(
            f"# Post Directions for {self.agent.name}", merged_styles
        )

    def _add_header(self, header: str, body: str) -> str:
        if not body:
            return ""
        full_header = ""
        if header:
            full_header = header + "\n"
        return f"{full_header}{body}\n"

    async def _filter_quote_candidates(self, results):
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
        return filtered_tweets
