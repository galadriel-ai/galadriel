from smolagents import *
from smolagents.agents import LogLevel
from smolagents import CodeAgent as SmolAgentCodeAgent
from smolagents import ToolCallingAgent as SmolAgentToolCallingAgent
from galadriel_agent.entities import Message
from galadriel_agent.agent import Agent


class CodeAgent(Agent, SmolAgentCodeAgent):
    async def execute(self, request: Message) -> Message:
        answer = SmolAgentCodeAgent.run(self, request.content)
        return Message(
            content=answer,
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


class ToolCallingAgent(Agent, SmolAgentToolCallingAgent):
    async def execute(self, request: Message) -> Message:
        answer = SmolAgentToolCallingAgent.run(self, request.content)
        return Message(
            content=answer,
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )
