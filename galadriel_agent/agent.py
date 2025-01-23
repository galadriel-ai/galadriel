import asyncio
from typing import List, Dict

from galadriel_agent.clients.client import Client
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.s3 import S3Client
from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import AgentConfig
from galadriel_agent.models import Memory

logger = get_agent_logger()


class AgentState:
    memories: List[Memory]
    database: DatabaseClient
    # TODO: knowledge_base: KnowledgeBase


class UserAgent:
    async def run(self, request: Dict) -> Dict:
        raise RuntimeError("Function not implemented")

class AgentState:
    memories: List[Memory]
    database: DatabaseClient
    # TODO: knowledge_base: KnowledgeBase

# This is just a rough sketch on how the GaladrielAgent itself will be implemented
# This is not meant to be read or modified by the end developer
class GaladrielAgent:
    def __init__(
        self,
        agent_config: AgentConfig,
        clients: Client,
        user_agent: UserAgent,
        s3_client: S3Client 
    ):
        self.agent_config = agent_config
        self.clients = clients
        self.user_agent = user_agent
        self.s3_client = s3_client

    async def run(self):
        client_input_queue = asyncio.Queue()
        for client in self.clients:
            asyncio.create_task(client.start(client_input_queue))

        await self.load_state(agent_state=None)
        while True:
            request = await client_input_queue.get()
            response = await self.user_agent.run(request)
            if response:
                proof = await self.generate_proof(request, response)
                await self.publish_proof(proof)
                for client in self.clients:
                    await client.post_output(request, response, proof)
            #await self.upload_state()

    async def generate_proof(self, request: Dict, response: Dict) -> str:
        pass

    async def publish_proof(self, proof: str):
        pass

    # State management functions
    async def export_state(self) -> AgentState:
        pass

    async def load_state(self, agent_state: AgentState):
        pass

    async def upload_state(self):
        state = self.export_state()
        await self.s3_client.upload_file(state)

    async def restore_state(self):
        state = await self.s3_client.download_file()
        self.load_state(state)
