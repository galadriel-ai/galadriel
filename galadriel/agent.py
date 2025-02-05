import asyncio
from pathlib import Path
from typing import List
from typing import Optional
from typing import Set

from dotenv import load_dotenv
from smolagents import *
from smolagents.agents import LogLevel
from galadriel.domain import add_conversation_history
from galadriel.domain import generate_proof
from galadriel.domain import publish_proof
from galadriel.domain import validate_solana_payment
from galadriel.domain.prompts import format_prompt
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue
from galadriel.entities import Pricing
from galadriel.entities import ShortTermMemory
from galadriel.errors import PaymentValidationError
from galadriel.logging_utils import init_logging

from smolagents import CodeAgent as InternalCodeAgent
from smolagents import ToolCallingAgent as InternalToolCallingAgent

DEFAULT_PROMPT_TEMPLATE = "{{request}}"

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


class CodeAgent(Agent, InternalCodeAgent):

    def __init__(self, prompt_template: Optional[str], **kwargs):
        InternalCodeAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = InternalCodeAgent.run(
            self, format_prompt.execute(self.prompt_template, request_dict)
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


class ToolCallingAgent(Agent, InternalToolCallingAgent):

    def __init__(self, prompt_template: Optional[str], **kwargs):
        InternalToolCallingAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = InternalToolCallingAgent.run(
            self, format_prompt.execute(self.prompt_template, request_dict)
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


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
