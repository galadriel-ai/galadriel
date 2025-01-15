from typing import List

from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.s3 import S3Client
from smolagents import ToolCallingAgent, Tool, TOOL_CALLING_SYSTEM_PROMPT
from typing import Optional, List, Callable

logger = get_agent_logger()


class AgentState:
    memories: List[Memory]
    database: DatabaseClient
    # TODO: knowledge_base: KnowledgeBase


class GaladrielAgent(ToolCallingAgent):

    def __init__(
        self,
        # For now can put in what ever you want
        tools: List[Tool],
        model: Callable,
        agent_config: AgentConfig=None,
        database_client: DatabaseClient=None,
        s3_client: S3Client=None,
        system_prompt: Optional[str] = None,
        planning_interval: Optional[int] = None,
        **kwargs,
        # Things consumed by python - OpenAI, Galadriel API, Database etc...
        # This allows the community to add all sorts of clients useful for Agent
        # TODO: not sure yet
        # clients: List[Client],
        # Things consumed by LLMs - calculator, web search etc..
        # This is allows the community to develop all sorts of tools and easy
        # for developers to create new ones
        # TODO: not sure yet
        # tools: List[Tool],
    ):
        if system_prompt is None:
            system_prompt = TOOL_CALLING_SYSTEM_PROMPT
        super().__init__(
            tools=tools,
            model=model,
            system_prompt=system_prompt,
            planning_interval=planning_interval,
            **kwargs,
        )
        self.agent_config = agent_config
        self.database_client = database_client
        self.s3_client = s3_client

    # Gathers all the data that the Agent is using and exporting it as one class
    async def export_state(self) -> AgentState:
        pass

    # Restores the Agent state from one class.
    # Should be called before calling run()
    async def load_state(self, agent_state: AgentState):
        pass

    async def upload_state(self):
        state = self.export_state()
        await self.s3_client.upload_file(state)

    async def restore_state(self):
        state = await self.s3_client.download_file()
        self.load_state(state)
