import asyncio
import signal
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List
from typing import Optional


from dotenv import load_dotenv as _load_dotenv

from smolagents import CodeAgent as InternalCodeAgent
from smolagents import ToolCallingAgent as InternalToolCallingAgent

from galadriel.domain import generate_proof
from galadriel.domain import publish_proof
from galadriel.domain.validate_solana_payment import SolanaPaymentValidator
from galadriel.domain.prompts import format_prompt
from galadriel.entities import Message
from galadriel.entities import Pricing
from galadriel.entities import PushOnlyQueue
from galadriel.errors import PaymentValidationError
from galadriel.logging_utils import init_logging
from galadriel.logging_utils import get_agent_logger
from galadriel.memory.memory_repository import MemoryRepository

logger = get_agent_logger()

DEFAULT_PROMPT_TEMPLATE = "{{request}}"

DEFAULT_PROMPT_TEMPLATE_WITH_CHAT_MEMORY = """
You are a helpful chatbot assistant.
Here is the chat history: \n\n {{chat_history}} \n
Answer the following question: \n\n {{request}} \n
Please remember the chat history and use it to answer the question, if relevant to the question.
"""


class Agent(ABC):
    """Abstract base class defining the interface for all agent implementations.

    This class serves as a contract that all concrete agent implementations must follow.
    """

    @abstractmethod
    async def execute(self, request: Message, memory: Optional[str] = None) -> Message:
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
        chat_memory: Optional[bool] = True,
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
        self.chat_memory = chat_memory
        self.prompt_template = (
            prompt_template or DEFAULT_PROMPT_TEMPLATE_WITH_CHAT_MEMORY if chat_memory else DEFAULT_PROMPT_TEMPLATE
        )
        format_prompt.validate_prompt_template(self.prompt_template)

    async def execute(self, request: Message, memory: Optional[str] = None) -> Message:
        request_dict = {"request": request.content, "chat_history": memory}
        answer = InternalCodeAgent.run(self, task=format_prompt.execute(self.prompt_template, request_dict))
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
        chat_memory: Optional[bool] = True,
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
        self.chat_memory = chat_memory
        self.prompt_template = (
            prompt_template or DEFAULT_PROMPT_TEMPLATE_WITH_CHAT_MEMORY if chat_memory else DEFAULT_PROMPT_TEMPLATE
        )
        format_prompt.validate_prompt_template(self.prompt_template)

    async def execute(self, request: Message, memory: Optional[str] = None) -> Message:
        request_dict = {"request": request.content, "chat_history": memory}
        answer = InternalToolCallingAgent.run(self, task=format_prompt.execute(self.prompt_template, request_dict))
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
        memory_repository: Optional[MemoryRepository] = None,
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
        self.solana_payment_validator = SolanaPaymentValidator(pricing)  # type: ignore
        self.memory_repository = memory_repository
        self.debug = debug
        self.enable_logs = enable_logs
        self.shutdown_event = asyncio.Event()

        env_path = Path(".") / ".env"
        _load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        if self.enable_logs:
            init_logging(self.debug)
        self._listen_for_stop()

    async def run(self):
        """Start the agent runtime loop.

        Creates an single queue and continuously processes incoming requests.
        Al agent inputs receive the same instance of the queue and append requests to it.
        """
        try:
            input_queue = asyncio.Queue()
            push_only_queue = PushOnlyQueue(input_queue)

            for agent_input in self.inputs:
                # Each agent input receives a queue it can push messages to
                asyncio.create_task(agent_input.start(push_only_queue))

            while not self.shutdown_event.is_set():
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

        def _shutdown_handler():
            self.shutdown_event.set()

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
        if self.solana_payment_validator.pricing:
            try:
                task_and_payment = await self.solana_payment_validator.execute(request)
                request.content = task_and_payment.task
            except PaymentValidationError as e:
                response = Message(content=str(e))
        if not response:
            # Run the agent if no errors occurred so far
            memories = None
            if self.memory_repository:
                try:
                    memories = await self.memory_repository.get_memories(prompt=request.content)
                except Exception as e:
                    logger.error(f"Error getting memories: {e}")
            response = await self.agent.execute(request, memories)
        if response:
            # proof = await self._generate_proof(request, response)
            # await self._publish_proof(request, response, proof)
            if self.memory_repository:
                try:
                    await self.memory_repository.add_memory(request=request, response=response)
                except Exception as e:
                    logger.error(f"Error adding memory: {e}")
            for output in self.outputs:
                await output.send(request, response)

    async def _get_agent_memory(self) -> List[Dict[str, str]]:
        """Retrieve the current state of the agent's inner memory. This is not the chat memories.

        Returns:
            List[Dict[str, str]]: The agent's memory in a serializable format
        """
        return self.agent.write_memory_to_messages(summary_mode=True)  # type: ignore

    async def _save_chat_memories(self, file_name: str) -> None:
        """Save the current state of the agent's chat memories.

        Returns:
            str: The agent's chat memories
        """
        if self.memory_repository:
            return self.memory_repository.save_data_locally(file_name)
        return None

    async def _generate_proof(self, request: Message, response: Message) -> str:
        return generate_proof.execute(request, response)

    async def _publish_proof(self, request: Message, response: Message, proof: str):
        publish_proof.execute(request, response, proof)
