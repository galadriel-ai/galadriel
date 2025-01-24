import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import List

from galadriel_agent.clients.client import Client
from galadriel_agent.clients.client import PushOnlyQueue
from galadriel_agent.clients.s3 import S3Client
from dotenv import load_dotenv


@dataclass
class AgentConfig:
    pass


class UserAgent:

    async def run(self, request: Dict) -> Dict:
        raise RuntimeError("Function not implemented")


class AgentState:
    # TODO: knowledge_base: KnowledgeBase
    pass


# This is just a rough sketch on how the GaladrielAgent itself will be implemented
# This is not meant to be read or modified by the end developer
class GaladrielAgent:
    def __init__(
        self,
        agent_config: AgentConfig,
        clients: List[Client],
        user_agent: UserAgent,
        s3_client: S3Client
    ):
        self.agent_config = agent_config
        self.clients = clients
        self.user_agent = user_agent
        self.s3_client = s3_client

        env_path = Path(".") / ".env"
        load_dotenv(dotenv_path=env_path)

    async def run(self):
        client_input_queue = asyncio.Queue()
        push_only_queue = PushOnlyQueue(client_input_queue)
        for client in self.clients:
            asyncio.create_task(client.start(push_only_queue))

        await self.load_state("")
        while True:
            request = await client_input_queue.get()
            response = await self.user_agent.run(request)
            if response:
                proof = await self.generate_proof(request, response)
                await self.publish_proof(proof)
                for client in self.clients:
                    await client.post_output(response, proof)

            await self.upload_state()

    async def generate_proof(self, request: Dict, response: Dict) -> str:
        return "mock_proof"

    async def publish_proof(self, proof: str):
        pass

    # State management functions
    async def export_state(self) -> AgentState:
        pass

    async def load_state(self, agent_state: AgentState):
        pass

    async def upload_state(self):
        state = await self.export_state()
        # upload(state)

    async def restore_state(self):
        # state = download()
        await self.load_state("state")
