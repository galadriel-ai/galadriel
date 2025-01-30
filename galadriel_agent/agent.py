import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Optional

from dotenv import load_dotenv

from galadriel_agent.domain import add_conversation_history
from galadriel_agent.domain import generate_proof
from galadriel_agent.domain import publish_proof
from galadriel_agent.entities import Message
from galadriel_agent.entities import PushOnlyQueue
from galadriel_agent.entities import ShortTermMemory
from galadriel_agent.logging_utils import init_logging
from galadriel_agent.storage.s3 import S3Client


@dataclass
class AgentConfig:
    pass


class Agent:
    async def run(self, request: Message) -> Message:
        raise RuntimeError("Function not implemented")


class AgentInput:
    async def start(self, queue: PushOnlyQueue) -> None:
        pass


class AgentOutput:
    async def send(self, request: Message, response: Message, proof: str) -> None:
        pass


class AgentState:
    # TODO: knowledge_base: KnowledgeBase
    pass


# This is just a rough sketch on how the GaladrielAgent itself will be implemented
# This is not meant to be read or modified by the end developer
class AgentRuntime:
    def __init__(
        # pylint:disable=R0917
        self,
        agent_config: Optional[AgentConfig],
        inputs: List[AgentInput],
        outputs: List[AgentOutput],
        agent: Agent,
        s3_client: Optional[S3Client] = None,
        short_term_memory: Optional[ShortTermMemory] = None,
    ):
        self.agent_config = agent_config
        self.inputs = inputs
        self.outputs = outputs
        self.agent = agent
        self.s3_client = s3_client
        self.short_term_memory = short_term_memory

        env_path = Path(".") / ".env"
        load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        init_logging(False)

    async def run(self):
        input_queue = asyncio.Queue()
        push_only_queue = PushOnlyQueue(input_queue)
        for agent_input in self.inputs:
            asyncio.create_task(agent_input.start(push_only_queue))

        await self.load_state(agent_state=None)
        while True:
            request = await input_queue.get()
            await self.run_request(request)
            # await self.upload_state()

    async def run_request(self, request: Message):
        request = await self._add_conversation_history(request)
        response = await self.agent.run(request)
        if response:
            proof = await self._generate_proof(request, response)
            await self._publish_proof(request, response, proof)
            for output in self.outputs:
                await output.send(request, response, proof)

    async def _add_conversation_history(self, request: Message) -> Message:
        if self.short_term_memory:
            return add_conversation_history.execute(request, self.short_term_memory)
        return request

    async def _generate_proof(self, request: Message, response: Message) -> str:
        return generate_proof.execute(request, response)

    async def _publish_proof(self, request: Message, response: Message, proof: str):
        publish_proof.execute(request, response, proof)

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
