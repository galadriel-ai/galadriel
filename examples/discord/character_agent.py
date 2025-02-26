from pathlib import Path
from typing import AsyncGenerator, Optional

from rich.text import Text

from galadriel import ToolCallingAgent, LogLevel, stream_agent_response
from galadriel.domain.prompts.format_prompt import load_agent_template
from galadriel.entities import Message

DISCORD_SYSTEM_PROMPT = """
{{system}}

# Areas of Expertise
{{knowledge}}

# About {{agent_name}}:
{{bio}}
{{lore}}
{{topics}}

# Task: You received a new message on discord from {{user_name}}. You must reply in the voice and style of {{agent_name}}, here's the message:
{{message}}

# Chat History:
{{chat_history}}

Be very brief, and concise, add a statement in your voice.
Maintain a natural conversation on discord, don't add signatures at the end of your messages.
Don't overuse emojis.
Please remember the chat history and use it to answer the question.
"""


class CharacterAgent(ToolCallingAgent):
    def __init__(self, character_json_path: str, **kwargs):
        ToolCallingAgent.__init__(self, **kwargs)
        try:
            self.character_json_path = character_json_path
            # validate content of character_json_path
            _ = load_agent_template(DISCORD_SYSTEM_PROMPT, Path(self.character_json_path))
        except Exception as e:
            self.logger.log(Text(f"Error validating character file: {e}"), level=LogLevel.ERROR)
            raise e

    async def execute(
        self, message: Message, memory: Optional[str] = None, stream: bool = False
    ) -> AsyncGenerator[Message, None]:
        try:
            # Load the agent template on every execution to ensure randomness
            character_prompt = load_agent_template(DISCORD_SYSTEM_PROMPT, Path(self.character_json_path))
            task_message = character_prompt.replace("{{message}}", message.content).replace(
                "{{user_name}}", message.additional_kwargs["author"]
            )
            if memory:
                task_message = task_message.replace("{{chat_history}}", memory)
            if not stream:
                answer = ToolCallingAgent.run(self, task=task_message)
                yield Message(
                    content=str(answer),
                    conversation_id=message.conversation_id,
                    additional_kwargs=message.additional_kwargs,
                )
                return
            # Stream is enabled
            async for message in stream_agent_response(
                agent_run=ToolCallingAgent.run(self, task=task_message, stream=True),
                conversation_id=message.conversation_id,
                additional_kwargs=message.additional_kwargs,
                model=self.model,
            ):
                yield message
        except Exception as e:
            self.logger.log(Text(f"Error processing message: {e}"), level=LogLevel.ERROR)
            return
