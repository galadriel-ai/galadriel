from smolagents import *
from smolagents.agents import LogLevel
from smolagents import CodeAgent as SmolAgentCodeAgent
from smolagents import ToolCallingAgent as SmolAgentToolCallingAgent
from galadriel_agent.entities import Message


class Agent:
    async def run(self, request: Message) -> Message:
        raise RuntimeError("Function not implemented")


class CodeAgent(SmolAgentCodeAgent, Agent):
    pass


class ToolCallingAgent(SmolAgentToolCallingAgent, Agent):
    pass

