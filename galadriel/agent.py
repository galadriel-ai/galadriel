import asyncio
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List
from typing import Optional
from typing import Set

from pprint import pformat

from dotenv import load_dotenv as _load_dotenv

from galadriel.core_agent import CodeAgent as InternalCodeAgent
from galadriel.core_agent import ToolCallingAgent as InternalToolCallingAgent

from galadriel.domain import generate_proof
from galadriel.domain import publish_proof
from galadriel.domain import validate_solana_payment
from galadriel.domain.prompts import format_prompt
from galadriel.entities import Message
from galadriel.entities import Pricing
from galadriel.entities import PushOnlyQueue
from galadriel.errors import PaymentValidationError
from galadriel.logging_utils import init_logging
from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()

DEFAULT_PROMPT_TEMPLATE = "{{request}}"


class Agent(ABC):
    @abstractmethod
    async def execute(self, request: Message) -> Message:
        raise RuntimeError("Function not implemented")


class AgentInput:
    async def start(self, queue: PushOnlyQueue) -> None:
        pass


class AgentOutput:
    async def send(self, request: Message, response: Message) -> None:
        pass


# pylint:disable=E0102
class CodeAgent(Agent, InternalCodeAgent):

    def __init__(
        self,
        prompt_template: Optional[str] = None,
        flush_memory: Optional[bool] = False,
        **kwargs,
    ):
        InternalCodeAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self.flush_memory = flush_memory

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = InternalCodeAgent.run(
            self,
            task=format_prompt.execute(self.prompt_template, request_dict),
            reset=self.flush_memory,  # retain memory
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


# pylint:disable=E0102
class ToolCallingAgent(Agent, InternalToolCallingAgent):

    def __init__(
        self,
        prompt_template: Optional[str] = None,
        flush_memory: Optional[bool] = False,
        **kwargs,
    ):
        InternalToolCallingAgent.__init__(self, **kwargs)
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self.flush_memory = flush_memory

    async def execute(self, request: Message) -> Message:
        request_dict = {"request": request.content}
        answer = InternalToolCallingAgent.run(
            self,
            task=format_prompt.execute(self.prompt_template, request_dict),
            reset=self.flush_memory,  # retain memory
        )
        return Message(
            content=str(answer),
            conversation_id=request.conversation_id,
            additional_kwargs=request.additional_kwargs,
        )


class AgentRuntime:
    def __init__(
        # pylint:disable=R0917
        self,
        inputs: List[AgentInput],
        outputs: List[AgentOutput],
        agent: Agent,
        pricing: Optional[Pricing] = None,
        debug: bool = False,
        enable_logs: bool = False,
    ):
        self.inputs = inputs
        self.outputs = outputs
        self.agent = agent
        self.pricing = pricing
        self.spent_payments: Set[str] = set()
        self.debug = debug
        self.enable_logs = enable_logs

        env_path = Path(".") / ".env"
        _load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        if self.enable_logs:
            init_logging(self.debug)

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
            if self.debug and self.enable_logs:
                memory = await self._get_memory()
                logger.info(f"Current agent memory: {pformat(memory)}")
        if response:
            # proof = await self._generate_proof(request, response)
            # await self._publish_proof(request, response, proof)
            for output in self.outputs:
                await output.send(request, response)

    async def _get_memory(self) -> List[Dict[str, str]]:
        return self.agent.write_memory_to_messages(summary_mode=True)

    async def _generate_proof(self, request: Message, response: Message) -> str:
        return generate_proof.execute(request, response)

    async def _publish_proof(self, request: Message, response: Message, proof: str):
        publish_proof.execute(request, response, proof)
