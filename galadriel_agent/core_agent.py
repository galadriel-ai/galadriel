from smolagents import *
from smolagents.agents import LogLevel
from smolagents import CodeAgent as SmolAgentCodeAgent
from smolagents import ToolCallingAgent as SmolAgentToolCallingAgent
from galadriel_agent.entities import Message


class Agent(MultiStepAgent):
    async def run(self, request: Message) -> Message:
        answer = super().run(request.content)
        return Message(
            content=answer,
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs
        )


class CodeAgent(Agent, SmolAgentCodeAgent):
    pass


class ToolCallingAgent(Agent, SmolAgentToolCallingAgent):
    pass

