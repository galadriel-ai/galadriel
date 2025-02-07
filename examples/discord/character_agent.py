import json
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from rich.text import Text

from galadriel import ToolCallingAgent
from galadriel.core_agent import LogLevel
from galadriel.core_agent import Tool
from galadriel.domain.prompts.format_prompt import load_agent_template
from galadriel.entities import AgentMessage
from galadriel.entities import Message

DISCORD_SYSTEM_PROMPT = """
{{system}}

# Areas of Expertise
{{knowledge}}

# About {{agent_name}}:
{{bio}}
{{lore}}
{{topics}}

# Task: You are chatting with {{user_name}} on discord. You must reply to the incoming message in the voice and style of {{agent_name}}:
{{message}}

Be very brief, and concise, add a statement in your voice.
"""


class CharacterAgent(ToolCallingAgent):
    def __init__(
        self,
        character_json_path: str,
        tools: List[Tool],
        model: Callable[[List[Dict[str, str]]], str],
        system_prompt: Optional[str] = None,
        tool_description_template: Optional[str] = None,
        max_steps: int = 6,
        tool_parser: Optional[Callable] = None,
        add_base_tools: bool = False,
        verbosity_level: int = 1,
        grammar: Optional[Dict[str, str]] = None,
        managed_agents: Optional[List] = None,
        step_callbacks: Optional[List[Callable]] = None,
        planning_interval: Optional[int] = None,
    ):
        super().__init__(
            tools=tools,
            model=model,
            system_prompt=system_prompt,
            tool_description_template=tool_description_template,
            max_steps=max_steps,
            tool_parser=tool_parser,
            add_base_tools=add_base_tools,
            verbosity_level=verbosity_level,
            grammar=grammar,
            managed_agents=managed_agents,
            step_callbacks=step_callbacks,
            planning_interval=planning_interval,
        )

        # Discord-specific initialization
        self.character_json_path = character_json_path
        try:
            self.character_prompt, self.character_name = load_agent_template(
                DISCORD_SYSTEM_PROMPT, Path(self.character_json_path)
            )
        except Exception as e:
            self.logger.log(
                Text(f"Error loading agent json: {e}"), level=LogLevel.ERROR
            )

    async def execute(self, message: Message) -> Message:
        try:
            task_message = self.character_prompt.replace(
                "{{message}}", message.content
            ).replace("{{user_name}}", message.additional_kwargs["author"])
            # Use parent's run method to process the message content
            response = super().run(
                task=task_message,
                stream=False,
                reset=False,  # retain memory
            )

            # Extract message text if response is in JSON format
            response_text = str(response)
            try:
                response_json = json.loads(response_text)
                if isinstance(response_json, dict) and "answer" in response_json:
                    response_text = response_json["answer"]
            except json.JSONDecodeError:
                pass  # Not JSON format, use original response

            return AgentMessage(
                content=response_text,
                conversation_id=message.conversation_id,
            )
        except Exception as e:
            self.logger.log(
                Text(f"Error processing message: {e}"), level=LogLevel.ERROR
            )
            return None
