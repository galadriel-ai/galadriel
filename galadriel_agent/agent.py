import asyncio
from pathlib import Path
from typing import List
from typing import Optional
from typing import Set

from dotenv import load_dotenv

from galadriel_agent.domain import add_conversation_history
from galadriel_agent.domain import generate_proof
from galadriel_agent.domain import publish_proof
from galadriel_agent.domain import validate_solana_payment
from galadriel_agent.entities import Message
from galadriel_agent.entities import PushOnlyQueue
from galadriel_agent.entities import Pricing
from galadriel_agent.entities import ShortTermMemory
from galadriel_agent.errors import PaymentValidationError
from galadriel_agent.logging_utils import init_logging


class Agent:
    async def execute(self, request: Message) -> Message:
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
        inputs: List[AgentInput],
        outputs: List[AgentOutput],
        agent: Agent,
        short_term_memory: Optional[ShortTermMemory] = None,
        pricing: Optional[Pricing] = None,
    ):
        self.inputs = inputs
        self.outputs = outputs
        self.agent = agent
        self.pricing = pricing
        self.short_term_memory = short_term_memory
        self.spent_payments: Set[str] = set()

        env_path = Path(".") / ".env"
        load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        init_logging(False)

    async def run(self):
        input_queue = asyncio.Queue()
        push_only_queue = PushOnlyQueue(input_queue)
        for agent_input in self.inputs:
            asyncio.create_task(agent_input.start(push_only_queue))

        while True:
            request = await input_queue.get()
            await self.run_request(request)
            # await self.upload_state()

    async def run_request(self, request: Message):
        request = await self._add_conversation_history(request)

        response = None
        # Handle payment validation
        if self.pricing:
            try:
                task_and_payment = validate_solana_payment.execute(
                    self.pricing, self.spent_payments, request
                )
                request.content = task_and_payment.task
            except PaymentValidationError as e:
                response = Message(content=str(e))
        if not response:
            # Run the agent if no errors occurred so far
            response = await self.agent.execute(request)
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
