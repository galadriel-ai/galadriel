from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


@dataclass
class AgentConfig:
    pass


@dataclass
class AgentState:
    pass


class UserAgent:

    async def run(self, request: Dict) -> Dict:
        raise RuntimeError("Function not implemented")


# Client interface, client itself can be Twitter, Discord, CLI, API etc...
class Client:

    async def get_input(self) -> Dict:
        pass

    async def post_output(self, response: Dict, proof: str):
        pass


# This is just a rough sketch on how the GaladrielAgent itself will be implemented
# This is not meant to be read or modified by the end developer
class GaladrielAgent:

    def __init__(
        self,
        agent_config: AgentConfig,
        client: Client,
        user_agent: UserAgent
    ):
        self.agent_config = agent_config
        self.client = client
        self.user_agent = user_agent

        env_path = Path(".") / ".env"
        load_dotenv(dotenv_path=env_path)

    async def run(self):
        await self.load_state("")
        while True:
            request = await self.client.get_input()
            response = await self.user_agent.run(request)
            if response:
                proof = await self.generate_proof(request, response)
                await self.publish_proof(proof)
                await self.client.post_output(response, proof)

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
