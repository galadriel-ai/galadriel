import asyncio
import json
import random
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

from smolagents import Tool

from galadriel_agent import utils
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.galadriel import GaladrielClient
from galadriel_agent.clients.perplexity import PerplexityClient
from galadriel_agent.clients.twitter import SearchResult
from galadriel_agent.clients.twitter import TwitterCredentials
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.logging_utils import init_logging
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.prompts import format_prompt
from galadriel_agent.prompts import get_default_prompt_state_use_case
from galadriel_agent.prompts import get_search_query
from galadriel_agent.responses import format_response
from galadriel_agent.tools.twitter import TWITTER_POST_TOOL_NAME
from galadriel_agent.tools.twitter import TWITTER_REPLIES_TOOL_NAME
from galadriel_agent.tools.twitter import TWITTER_SEARCH_TOOL_NAME
from galadriel_agent.utils import format_timestamp

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

PROMPT_SHOULD_REPLY_TEMPLATE = """# INSTRUCTIONS: Determine if {{agent_name}} (@{{twitter_user_name}}) should respond to the message and participate in the conversation. Do not comment. Just respond with "true" or "false".

Response options are RESPOND, IGNORE and STOP.

- {{agent_name}} should RESPOND to messages directed at them
- {{agent_name}} should RESPOND to conversations relevant to their background
- {{agent_name}} should IGNORE irrelevant messages
- {{agent_name}} should IGNORE very short messages unless directly addressed
- {{agent_name}} should STOP if asked to stop
- {{agent_name}} should STOP if conversation is concluded
- {{agent_name}} is in a room with other users and wants to be conversational, but not annoying.

IMPORTANT:
- {{agent_name}} (aka @{{twitter_user_name}}) is particularly sensitive about being annoying, so if there is any doubt, it is better to IGNORE than to RESPOND.
- For users not in the priority list, {{agent_name}} (@{{twitter_user_name}}) should err on the side of IGNORE rather than RESPOND if in doubt.

Recent Posts:
{{recent_posts}}

Current Post:
{{current_post}}

Thread of Tweets You Are Replying To:
{{formatted_conversation}}

# INSTRUCTIONS: Respond with [RESPOND] if {{agent_name}} should respond, or [IGNORE] if {{agent_name}} should not respond to the last message and [STOP] if {{agent_name}} should stop participating in the conversation.
The available options are [RESPOND], [IGNORE], or [STOP]. Choose the most appropriate option.
If {{agent_name}} is talking too much, you can choose [IGNORE]

Your response must include one of the options.
"""

PROMPT_REPLY_TEMPLATE = """
# Areas of Expertise
{{knowledge}}

# About {{agent_name}} (@{{twitter_user_name}}):
{{bio}}
{{lore}}
{{topics}}

{{post_directions}}

Recent interactions between {{agent_name}} and other users:

{{recent_posts}}

# TASK: Generate a post/reply in the voice, style and perspective of {{agent_name}} (@{{twitter_user_name}}) while using the thread of tweets as additional context:

Current Post:
{{current_post}}

Thread of Tweets You Are Replying To:
{{formatted_conversation}}

Here is the current post text again.
{{current_post}}
"""

TWEET_RETRY_COUNT = 3
# How many tweets between last quote from the same user
QUOTED_USER_REOCCURRENCE_LIMIT = 3


class TwitterPostAgent(GaladrielAgent):
    agent: AgentConfig

    perplexity_client: PerplexityClient
    galadriel_client: GaladrielClient
    database_client: DatabaseClient

    twitter_post_tool: Tool
    twitter_search_tool: Optional[Tool]
    twitter_replies_tool: Optional[Tool]

    post_interval_minutes_min: int
    post_interval_minutes_max: int

    # pylint: disable=R0917:
    def __init__(
        self,
        api_key: str,
        agent_name: str,
        perplexity_api_key: str,
        twitter_credentials: TwitterCredentials,
        tools: List[Tool],
        post_interval_minutes_min: int = 90,
        post_interval_minutes_max: int = 180,
        max_conversations_count_for_replies: int = 3,
    ):
        # super().__init__()
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

        self.twitter_username = self.agent.extra_fields.get("twitter_profile", {}).get(
            "username", "user"
        )

        self.galadriel_client = GaladrielClient(api_key=api_key)
        self.perplexity_client = PerplexityClient(perplexity_api_key)

        # Initialize tools
        tool_names = [t.name for t in tools]
        if TWITTER_POST_TOOL_NAME in tool_names:
            self.twitter_post_tool = [t for t in tools if t.name == TWITTER_POST_TOOL_NAME][0]
        else:
            raise Exception("Missing tool for posting tweets, exiting")
        if TWITTER_SEARCH_TOOL_NAME in tool_names:
            self.twitter_search_tool = [t for t in tools if t.name == TWITTER_SEARCH_TOOL_NAME][0]
        if TWITTER_REPLIES_TOOL_NAME in tool_names:
            self.twitter_replies_tool = [t for t in tools if t.name == TWITTER_REPLIES_TOOL_NAME][0]

        self.database_client = DatabaseClient(None)

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max
        self.max_conversations_count_for_replies = max_conversations_count_for_replies

    async def run(self):
        logger.info("Running agent!")

        # TODO: what to do with this event loop?
        #  Need to start replying as well
        # await self._run_posting_loop()
        await self._run_reply_loop()

    async def _run_reply_loop(self):
        # sleep_time = random.randint(
        #     int(self.post_interval_minutes_min / 4),
        #     int(self.post_interval_minutes_max / 4),
        # )
        # await asyncio.sleep(sleep_time * 60)

        while True:
            await self._post_replies()
            sleep_time = random.randint(
                int(self.post_interval_minutes_min / 4),
                int(self.post_interval_minutes_max / 4),
            )
            logger.info(f"Next Tweet replies scheduled in {sleep_time} minutes.")
            await asyncio.sleep(sleep_time * 60)

    async def _post_replies(self):
        logger.info("Generating replies")
        reply_count = 0

        # Get all conversations
        tweets = await self.database_client.get_tweets()
        conversations = []
        for tweet in reversed(tweets):
            if (
                tweet.quoted_tweet_username is None and tweet.quoted_tweet_id is None
                and tweet.conversation_id is not None
            ):
                conversation_id = tweet.conversation_id
                if conversation_id not in conversations and conversation_id != "dry_run":
                    conversations.append(conversation_id)
            if len(conversations) > self.max_conversations_count_for_replies:
                break

        for conversation_id in conversations:
            replies = self.twitter_replies_tool(conversation_id)
            if not len(replies):
                continue

            formatted_replies = [SearchResult.from_dict(r) for r in json.loads(replies)]
            for reply in formatted_replies:
                if reply.username == self.twitter_username:
                    continue
                existing_response = [t for t in tweets if t.reply_to_id == reply.id]
                if len(existing_response):
                    continue
                is_success = await self._handle_reply(conversation_id, reply)
                if is_success:
                    reply_count += 1

    async def _handle_reply(self, reply_to_id: str, reply: SearchResult) -> bool:

        tweets = await self.database_client.get_tweets()
        filtered_tweets = [t for t in tweets if t.id == reply_to_id]
        if not len(filtered_tweets):
            return False

        prompt_state = await get_default_prompt_state_use_case.execute(
            self.agent, self.database_client,
        )
        prompt_state["current_post"] = f"""ID: ${reply.id}
  From: @{reply.username}
  Text: {reply.text}"""
        # "TODO":
        prompt_state["formatted_conversation"] = ""

        prompt = format_prompt.execute(PROMPT_SHOULD_REPLY_TEMPLATE, prompt_state)
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
            message = response.choices[0].message.content
            # Is this check good enough?
            if "RESPOND" not in message:
                return False

            return await self._generate_reply(prompt_state, reply_to_id, reply)
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return False

    async def _generate_reply(self, prompt_state: Dict, conversation_id: str, reply: SearchResult) -> bool:
        prompt = format_prompt.execute(PROMPT_REPLY_TEMPLATE, prompt_state)
        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        reply_response = await self.galadriel_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages  # type: ignore
        )
        if not reply_response:
            logger.error("No API reply_response from Galadriel")
            return False
        if (
            reply_response.choices
            and reply_response.choices[0].message
            and reply_response.choices[0].message.content
        ):
            reply_message = reply_response.choices[0].message.content
            twitter_response = self.twitter_post_tool(reply_message, reply.id)
            if tweet_id := (
                twitter_response and twitter_response.get("data", {}).get("id")
            ):
                logger.debug(f"Tweet ID: {tweet_id}")
                await self.database_client.add_memory(
                    Memory(
                        id=tweet_id,
                        conversation_id=conversation_id,
                        type="tweet",
                        text=reply_message,
                        topics=prompt_state.get("topics_data", []),
                        timestamp=utils.get_current_timestamp(),
                        search_topic=None,
                        quoted_tweet_id=None,
                        quoted_tweet_username=None,
                        reply_to_id=reply.id,
                    )
                )
                return True
        return False

    async def _run_posting_loop(self):
        # # TODO: needs to be latest NON-reply
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
        if random.random() < 2:
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
            twitter_response = self.twitter_post_tool(formatted_message)
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
            twitter_response = self.twitter_post_tool(message)
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
