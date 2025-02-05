from typing import Optional
from smolagents import *
from smolagents.agents import LogLevel
from smolagents import CodeAgent as SmolAgentCodeAgent
from smolagents import ToolCallingAgent as SmolAgentToolCallingAgent
from galadriel_agent.entities import Message
from galadriel_agent.agent import Agent
from galadriel_agent.domain.prompts import format_prompt


DEFAULT_PROMPT_TEMPLATE = "{{request}}"


class CodeAgent(Agent, SmolAgentCodeAgent):

    def __init__(self, prompt_template: Optional[str], **kwargs):
        SmolAgentCodeAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = SmolAgentCodeAgent.run(
            self, format_prompt.execute(self.prompt_template, request_dict)
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


class ToolCallingAgent(Agent, SmolAgentToolCallingAgent):

    def __init__(self, prompt_template: Optional[str], **kwargs):
        SmolAgentCodeAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = SmolAgentCodeAgent.run(
            self, format_prompt.execute(self.prompt_template, request_dict)
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )
