import asyncio
import json
import random
from typing import Dict

from galadriel_agent import utils
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.llms.galadriel import GaladrielClient
from galadriel_agent.clients.twitter import SearchResult
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.prompts import format_prompt
from galadriel_agent.prompts import get_default_prompt_state_use_case
from galadriel_agent.tools.twitter import TwitterPostTool
from galadriel_agent.tools.twitter import TwitterRepliesTool

logger = get_agent_logger()

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


class TwitterReplyRunner(GaladrielAgent):
    agent: AgentConfig

    database_client: DatabaseClient
    llm_client: GaladrielClient

    twitter_replies_tool: TwitterRepliesTool
    twitter_post_tool: TwitterPostTool

    post_interval_minutes_min: int
    post_interval_minutes_max: int
    max_conversations_count_for_replies: int

    def __init__(
        self,
        agent: AgentConfig,
        llm_client: GaladrielClient,
        twitter_replies_tool: TwitterRepliesTool,
        twitter_post_tool: TwitterPostTool,
        database_client: DatabaseClient,
        post_interval_minutes_min: int,
        post_interval_minutes_max: int,
        max_conversations_count_for_replies: int,
    ):
        self.agent = agent
        self.twitter_username = self.agent.extra_fields.get("twitter_profile", {}).get(
            "username", "user"
        )

        self.twitter_replies_tool = twitter_replies_tool
        self.twitter_post_tool = twitter_post_tool

        self.llm_client = llm_client
        self.database_client = database_client

        self.post_interval_minutes_min = post_interval_minutes_min
        self.post_interval_minutes_max = post_interval_minutes_max
        self.max_conversations_count_for_replies = max_conversations_count_for_replies

    async def run(self) -> None:
        await self._run_loop()

    async def _run_loop(self) -> None:
        # sleep_time = random.randint(
        #     self.post_interval_minutes_min,
        #     self.post_interval_minutes_max,
        # )
        # await asyncio.sleep(sleep_time * 60)

        while True:
            await self._post_replies()
            sleep_time = random.randint(
                self.post_interval_minutes_min,
                self.post_interval_minutes_max,
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
        response = await self.llm_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages  # type: ignore
        )
        if not response:
            logger.error("No API response from LLM")
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
        reply_response = await self.llm_client.completion(
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
