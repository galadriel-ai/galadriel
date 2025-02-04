from typing import Dict
from typing import Optional

from galadriel import Agent
from galadriel.connectors.llm import LlmClient
from galadriel.connectors.twitter import SearchResult
from galadriel.domain.prompts import format_prompt
from galadriel.entities import Message
from galadriel.logging_utils import get_agent_logger
from src.models import TwitterAgentConfig
from src.models import TwitterPost
from src.prompts import get_default_prompt_state_use_case
from src.repository.database import DatabaseClient
from src.responses import format_response

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


class TwitterReplyAgent(Agent):
    agent: TwitterAgentConfig

    database_client: DatabaseClient
    llm_client: LlmClient

    def __init__(
        self,
        agent_config: TwitterAgentConfig,
        llm_client: LlmClient,
        database_client: DatabaseClient,
    ):
        self.agent = agent_config

        self.llm_client = llm_client
        self.database_client = database_client

    async def execute(self, request: Message) -> Message:
        request_type = request.type
        if request_type and request_type == "tweet_reply":
            conversation_id = request.conversation_id
            reply = SearchResult.from_dict(request.additional_kwargs)
            response = await self._handle_reply(conversation_id, reply)
            if response:
                return response
            raise Exception("Error running agent")
        elif request_type == "tweet_original":
            pass
        logger.debug(
            f"TwitterClient got unexpected request_type: {request_type}, skipping"
        )

    async def _handle_reply(
        self, reply_to_id: str, reply: SearchResult
    ) -> Optional[Message]:
        tweets = await self.database_client.get_tweets()
        filtered_tweets = [t for t in tweets if t.id == reply_to_id]
        if not len(filtered_tweets):
            return None

        prompt_state = await get_default_prompt_state_use_case.execute(
            self.agent,
            self.database_client,
        )
        prompt_state[
            "current_post"
        ] = f"""ID: ${reply.id}
    From: @{reply.username}
    Text: {reply.text}"""
        # TODO: "current_post" should be the original post, and "formatted_conversation" should contain the reply(ies)
        prompt_state["formatted_conversation"] = ""

        prompt = format_prompt.execute(PROMPT_SHOULD_REPLY_TEMPLATE, prompt_state)

        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        response = await self.llm_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages  # type: ignore
        )
        if not response:
            logger.error("No API response from LLM")
            return None
        if (
            response.choices
            and response.choices[0].message
            and response.choices[0].message.content
        ):
            message = response.choices[0].message.content
            # Is this check good enough?
            if (
                "RESPOND".lower() not in message.lower()
                and "true" not in message.lower()
            ):
                return None

            return await self._generate_reply(prompt_state, reply_to_id, reply)
        else:
            logger.error(
                f"Unexpected API response from Galadriel: \n{response.to_json()}"
            )
        return None

    async def _generate_reply(
        self, prompt_state: Dict, conversation_id: str, reply: SearchResult
    ) -> Optional[Message]:
        prompt = format_prompt.execute(PROMPT_REPLY_TEMPLATE, prompt_state)
        logger.debug(f"Got full formatted reply prompt: \n{prompt}")

        messages = [
            {"role": "system", "content": self.agent.system},
            {"role": "user", "content": prompt},
        ]
        reply_response = await self.llm_client.completion(
            self.agent.settings.get("model", "gpt-4o"), messages
        )
        if not reply_response:
            logger.error("No API reply_response from Galadriel")
            return None
        if (
            reply_response.choices
            and reply_response.choices[0].message
            and reply_response.choices[0].message.content
        ):
            reply_message = reply_response.choices[0].message.content
            formatted_reply_message = format_response.execute(reply_message)
            if not formatted_reply_message:
                return Message(
                    content="",
                    conversation_id=None,
                    type="tweet_excluded",
                    additional_kwargs=TwitterPost(
                        type="tweet_excluded",
                        conversation_id=conversation_id,
                        text=reply_message,
                        reply_to_id=reply.id,
                    ).to_dict(),
                )
            return Message(
                content="",
                conversation_id=None,
                type="tweet",
                additional_kwargs=TwitterPost(
                    type="tweet",
                    conversation_id=conversation_id,
                    text=reply_message,
                    reply_to_id=reply.id,
                ).to_dict(),
            )
        return None
