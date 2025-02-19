import asyncio
import signal
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List
from typing import Optional
from typing import Set

from pprint import pformat

from dotenv import load_dotenv as _load_dotenv

from smolagents import CodeAgent as InternalCodeAgent
from smolagents import ToolCallingAgent as InternalToolCallingAgent

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
    """Abstract base class defining the interface for all agent implementations.

    This class serves as a contract that all concrete agent implementations must follow.
    """

    @abstractmethod
    async def execute(self, request: Message) -> Message:
        """Process a single request and generate a response.
        The processing can be a single LLM call or involve multiple agentic steps, like CodeAgent.

        Args:
            request (Message): The input message to be processed

        Returns:
            Message: The agent's response message
        """
        raise RuntimeError("Function not implemented")


class AgentInput:
    """Base class for handling input sources to the agent runtime.

    Implementations of this class define how inputs are received and queued
    for processing by the agent.
    """

    async def start(self, queue: PushOnlyQueue) -> None:
        """Begin receiving inputs and pushing them to the processing queue.

        Args:
            queue (PushOnlyQueue): Queue to which input messages should be pushed
        """


class AgentOutput:
    """Base class for handling agent output destinations.

    Implementations of this class define how processed responses are delivered
    to their final destination.
    """

    async def send(self, request: Message, response: Message) -> None:
        """Send a processed response to its destination.

        Args:
            request (Message): The original request that generated the response
            response (Message): The response to be delivered
        """


class AgentState:
    # TODO: knowledge_base: KnowledgeBase
    pass


# pylint:disable=E0102
class CodeAgent(Agent, InternalCodeAgent):
    """
    This class combines the abstract Agent interface with the functionality of an internal
    CodeAgent from the smolagents package. It formats the request using a provided template,
    executes the internal code agent's run method, and returns a response message. Memory is
    kept between requests by default.
    """

    def __init__(
        self,
        prompt_template: Optional[str] = None,
        flush_memory: Optional[bool] = False,
        **kwargs,
    ):
        """Initialize the CodeAgent.

        Args:
            prompt_template (Optional[str]): Template used to format input requests.
                The template should contain {{request}} where the input message should be inserted.
                Example: "Answer the following question: {{request}}"
                If not provided, defaults to "{{request}}"
            flush_memory (Optional[bool]): If True, clears memory between requests. Defaults to False.
            **kwargs: Additional arguments passed to InternalCodeAgent

        Example:
            agent = CodeAgent(
                prompt_template="You are a helpful assistant. Please answer: {{request}}",
                model="gpt-4",
            )
            response = await agent.execute(Message(content="What is Python?"))
        """
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
    """
    Similar to CodeAgent, this class wraps an internal ToolCallingAgent from the smolagents
    package. It formats the request, executes the tool-calling agent, and returns the response.
    Memory is kept between requests by default.
    """

    def __init__(
        self,
        prompt_template: Optional[str] = None,
        flush_memory: Optional[bool] = False,
        **kwargs,
    ):
        """
        Initialize the ToolCallingAgent.

        Args:
            prompt_template (Optional[str]): Template used to format input requests.
                The template should contain {{request}} where the input message should be inserted.
                Example: "Use available tools to answer: {{request}}"
                If not provided, defaults to "{{request}}"
            flush_memory (Optional[bool]): If True, clears memory between requests. Defaults to False.
            **kwargs: Additional arguments passed to InternalToolCallingAgent including available tools

        Example:
            agent = ToolCallingAgent(
                prompt_template="You have access to tools. Please help with: {{request}}",
                model="gpt-4",
            )
            response = await agent.execute(Message(content="What's the weather in Paris?"))
        """
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
    """Runtime environment for executing agent workflows.

    Manages the lifecycle of agent execution including input processing,
    payment validation, response generation, and output delivery.
    """

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
        """Initialize the AgentRuntime.

        Args:
            inputs (List[AgentInput]): Input sources for the agent
            outputs (List[AgentOutput]): Output destinations for responses
            agent (Agent): The agent implementation to use
            pricing (Optional[Pricing]): Payment configuration if required
            debug (bool): Enable debug mode
            enable_logs (bool): Enable logging
        """
        self.inputs = inputs
        self.outputs = outputs
        self.agent = agent
        self.pricing = pricing
        self.spent_payments: Set[str] = set()
        self.debug = debug
        self.enable_logs = enable_logs
        self.is_running: bool = False

        env_path = Path(".") / ".env"
        _load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        if self.enable_logs:
            init_logging(self.debug)

    async def run(self):
        """Start the agent runtime loop.

        Creates an single queue and continuously processes incoming requests.
        Al agent inputs receive the same instance of the queue and append requests to it.
        """
        try:
            self.is_running = True
            input_queue = asyncio.Queue()
            push_only_queue = PushOnlyQueue(input_queue)

            for agent_input in self.inputs:
                # Each agent input receives a queue it can push messages to
                asyncio.create_task(agent_input.start(push_only_queue))

            while self.is_running:
                # Get the next request from the queue
                request = await input_queue.get()
                # Process the request
                await self._run_request(request)
        finally:
            self.is_running = False
            await self.upload_state()

    async def stop(self):
        self.is_running = False

    async def _listen_for_stop(self):
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def _shutdown_handler():
            shutdown_event.set()

        try:
            loop.add_signal_handler(signal.SIGTERM, _shutdown_handler)
        except NotImplementedError:
            # Signal handling may not be supported on some platforms (e.g., Windows)
            logger.warning("SIGTERM signal handling is not supported on this platform.")


    async def _run_request(self, request: Message):
        """Process a single request through the agent pipeline.

        Handles payment validation, agent execution, and response delivery.

        Args:
            request (Message): The request to process
        """
        response = None
        # Handle payment validation
        if self.pricing:
            try:
                task_and_payment = validate_solana_payment.execute(self.pricing, self.spent_payments, request)
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
        """Retrieve the current state of the agent's memory.

        Returns:
            List[Dict[str, str]]: The agent's memory in a serializable format
        """
        return self.agent.write_memory_to_messages(summary_mode=True)  # type: ignore

    async def _generate_proof(self, request: Message, response: Message) -> str:
        return generate_proof.execute(request, response)

    async def _publish_proof(self, request: Message, response: Message, proof: str):
        publish_proof.execute(request, response, proof)
