import asyncio
import signal
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import AsyncGenerator, Dict, List
from typing import Optional

from dotenv import load_dotenv as _load_dotenv

from smolagents import CodeAgent as InternalCodeAgent
from smolagents import ToolCallingAgent as InternalToolCallingAgent
from smolagents import ActionStep

from galadriel.domain.extract_step_logs import pull_messages_from_step
from galadriel.domain.validate_solana_payment import SolanaPaymentValidator
from galadriel.domain.prompts import format_prompt
from galadriel.entities import Message, Proof
from galadriel.entities import Pricing
from galadriel.entities import PushOnlyQueue
from galadriel.errors import PaymentValidationError
from galadriel.logging_utils import init_logging
from galadriel.logging_utils import get_agent_logger
from galadriel.memory.memory_store import MemoryStore
from galadriel.proof.prover import Prover
from galadriel.state.agent_state_repository import AgentStateRepository

logger = get_agent_logger()

DEFAULT_PROMPT_TEMPLATE = """
You are a helpful chatbot assistant.
Here is the chat history: \n\n {{chat_history}} \n
Answer the following question: \n\n {{request}} \n
Please remember the chat history and use it to answer the question, if relevant to the question.
Maintain a natural conversation, don't add signatures at the end of your messages.
Call the final_answer tool if you have a final answer to the question.
"""


class Agent(ABC):
    """Abstract base class defining the interface for all agent implementations.

    This class serves as a contract that all concrete agent implementations must follow.
    """

    @abstractmethod
    async def execute(
        self, request: Message, memory: Optional[str] = None, stream: bool = False
    ) -> AsyncGenerator[Message, None]:
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

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Send a processed response to its destination.

        Args:
            request (Message): The original request that generated the response
            response (Message): The response to be delivered
            proof (Proof): The proof of the response's authenticity
        """


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
        format_prompt.validate_prompt_template(self.prompt_template)

    async def execute(  # type: ignore
        self, request: Message, memory: Optional[str] = None, stream: bool = False
    ) -> AsyncGenerator[Message, None]:
        request_dict = {"request": request.content, "chat_history": memory}
        formatted_task = format_prompt.execute(self.prompt_template, request_dict)

        if not stream:
            answer = InternalCodeAgent.run(self, task=formatted_task)

            yield Message(
                content=str(answer),
                conversation_id=request.conversation_id,
                additional_kwargs={
                    **(request.additional_kwargs or {}),
                    "role": "assistant",
                    "type": "completion_message",
                },
                final=True,
            )
            return
        # Stream is enabled
        async for message in stream_agent_response(
            agent_run=InternalCodeAgent.run(self, task=formatted_task, stream=True),
            conversation_id=request.conversation_id,  # type: ignore
            additional_kwargs=request.additional_kwargs,
            model=self.model,
        ):
            yield message


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
        format_prompt.validate_prompt_template(self.prompt_template)

    async def execute(  # type: ignore
        self, request: Message, memory: Optional[str] = None, stream: bool = False
    ) -> AsyncGenerator[Message, None]:
        request_dict = {"request": request.content, "chat_history": memory}
        formatted_task = format_prompt.execute(self.prompt_template, request_dict)

        if not stream:
            answer = InternalToolCallingAgent.run(self, task=formatted_task)
            yield Message(
                content=str(answer),
                conversation_id=request.conversation_id,
                additional_kwargs={
                    **(request.additional_kwargs or {}),
                    "role": "assistant",
                    "type": "completion_message",
                },
                final=True,
            )
            return
        # Stream is enabled
        async for message in stream_agent_response(
            agent_run=InternalToolCallingAgent.run(self, task=formatted_task, stream=True),
            conversation_id=request.conversation_id,  # type: ignore
            additional_kwargs=request.additional_kwargs,
            model=self.model,
        ):
            yield message


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
        memory_store: Optional[MemoryStore] = MemoryStore(),
        debug: bool = False,
        enable_logs: bool = True,
    ):
        """Initialize the AgentRuntime.

        Args:
            inputs (List[AgentInput]): Input sources for the agent
            outputs (List[AgentOutput]): Output destinations for responses
            agent (Agent): The agent implementation to use
            solana_payment_validator (SolanaPaymentValidator): Payment validator
            debug (bool): Enable debug mode
            enable_logs (bool): Enable logging
        """
        self.inputs = inputs
        self.outputs = outputs
        self.agent = agent
        self.solana_payment_validator = SolanaPaymentValidator(pricing)  # type: ignore
        self.memory_store = memory_store
        self.debug = debug
        self.enable_logs = enable_logs
        self.shutdown_event = asyncio.Event()
        self.agent_state_repository = AgentStateRepository()
        try:
            self.prover: Optional[Prover] = Prover()
        except Exception as e:
            self.prover = None
            logger.error(f"Error initializing prover: {e}. Proofs will not be generated.")
        env_path = Path(".") / ".env"
        _load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        if self.enable_logs:
            init_logging(self.prover, self.debug)

    async def run(self, stream: bool = False):
        """Start the agent runtime loop.

        Creates an single queue and continuously processes incoming requests.
        Al agent inputs receive the same instance of the queue and append requests to it.
        """
        logger.info("Agent runtime started")
        input_queue = asyncio.Queue()  # type: ignore
        push_only_queue = PushOnlyQueue(input_queue)

        # Listen for shutdown event
        await self._listen_for_stop()

        # Download agent state from S3 if long term memory is enabled
        await self._load_agent_state()

        # Start agent inputs
        # Create tasks for all inputs and track them
        input_tasks = [
            asyncio.create_task(self._safe_client_start(agent_input, push_only_queue)) for agent_input in self.inputs
        ]

        while not self.shutdown_event.is_set():
            active_tasks = [task for task in input_tasks if not task.done()]
            if not active_tasks:
                logger.info("All input clients finished. Stopping the runtime...")
                self.stop()
                break
            # Get the next request from the queue
            try:
                request = await asyncio.wait_for(input_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            # Process the request
            await self._run_request(request, stream)

        await self._save_agent_state()
        logger.info("Agent runtime Stopped.")

    def stop(self):
        self.shutdown_event.set()

    async def _listen_for_stop(self):
        loop = asyncio.get_running_loop()

        def _shutdown_handler():
            self.stop()

        try:
            loop.add_signal_handler(signal.SIGTERM, _shutdown_handler)
        except NotImplementedError:
            # Signal handling may not be supported on some platforms (e.g., Windows)
            logger.warning("SIGTERM signal handling is not supported on this platform.")

    async def _run_request(self, request: Message, stream: bool):
        """Process a single request through the agent pipeline.

        Handles payment validation, agent execution, and response delivery.

        Args:
            request (Message): The request to process
        """
        task_and_payment, response = None, None
        # Handle payment validation
        if self.solana_payment_validator.pricing:
            try:
                task_and_payment = await self.solana_payment_validator.execute(request)
                request.content = task_and_payment.task
            except PaymentValidationError:
                logger.error("Payment validation error", exc_info=True)
            except Exception:
                logger.error("Unexpected error during payment validation", exc_info=True)
        # Run the agent if payment validation passed or not required
        if task_and_payment or not self.solana_payment_validator.pricing:
            memories = None
            proof: Optional[Proof] = None
            if self.memory_store:
                try:
                    memories = await self.memory_store.get_memories(prompt=request.content)
                except Exception as e:
                    logger.error(f"Error getting memories: {e}")
            try:
                async for response in self.agent.execute(request, memories, stream=stream):  # type: ignore
                    if response.final and self.prover:
                        try:
                            proof = await self.prover.generate_proof(request, response)
                        except Exception as e:
                            logger.error(f"Error generating proof: {e}")
                            raise e
                    for output in self.outputs:
                        try:
                            await output.send(request, response, proof)
                        except Exception:
                            logger.error(
                                "Failed to send streaming response via output",
                                exc_info=True,
                            )
            except Exception:
                logger.error("Error during agent execution", exc_info=True)
        # Send the response to the outputs
        if response:
            if proof and self.prover:
                await self.prover.publish_proof(request, response, proof)
            if self.memory_store:
                try:
                    await self.memory_store.add_memory(request=request, response=response)
                except Exception as e:
                    logger.error(f"Error adding memory: {e}")

    async def _get_agent_memory(self) -> List[Dict[str, str]]:
        """Retrieve the current state of the agent's inner memory. This is not the chat memories.

        Returns:
            List[Dict[str, str]]: The agent's memory in a serializable format
        """
        return self.agent.write_memory_to_messages(summary_mode=True)  # type: ignore

    async def _safe_client_start(self, agent_input: AgentInput, queue: PushOnlyQueue):
        try:
            await agent_input.start(queue)
        except Exception as e:
            logger.error(f"Input client {agent_input.__class__.__name__} failed", exc_info=True)
            raise e

    async def _save_chat_memories(self, file_name: str) -> None:
        """Save the current state of the agent's chat memories.

        Returns:
            str: The agent's chat memories
        """
        if self.memory_store:
            return self.memory_store.save_data_locally(file_name)
        return None

    async def _load_agent_state(self):
        """Load agent state from persistent storage if available."""
        if not (self.memory_store and self.memory_store.vector_store):
            logger.debug("Skipping memory loading: vector store not configured")
            return False

        try:
            logger.info("Attempting to load agent state from storage")
            agent_state = self.agent_state_repository.download_agent_state()

            if not agent_state:
                logger.info("No existing agent state found in storage")
                return False

            self.memory_store.load_memory_from_folder(agent_state.memory_folder_path)
            logger.info(f"Successfully loaded agent memory from {agent_state.memory_folder_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load agent memory: {e}", exc_info=self.debug)
            return False

    async def _save_agent_state(self):
        """Save agent state to persistent storage if vector store is configured."""
        if not (self.memory_store and self.memory_store.vector_store):
            logger.debug("Skipping state saving: vector store not configured")
            return False

        try:
            state_folder_path = "/tmp/agent_state"
            logger.info(f"Saving agent state to {state_folder_path}")

            self.memory_store.save_data_locally(state_folder_path)
            self.agent_state_repository.upload_agent_state(state_folder_path)

            logger.info("Successfully saved and uploaded agent state")
            return True

        except Exception as e:
            logger.error(f"Failed to save agent state: {e}", exc_info=self.debug)
            return False


async def stream_agent_response(
    agent_run,
    conversation_id: str,
    additional_kwargs: Optional[Dict] = None,
    model=None,
) -> AsyncGenerator[Message, None]:
    """Stream responses from an agent run.

    Args:
        agent_run: Iterator from agent.run(task, stream=True)
        conversation_id: ID to maintain conversation context
        additional_kwargs: Additional message parameters
        model: Optional model instance for token tracking
    """
    total_input_tokens = 0
    total_output_tokens = 0
    for step_log in agent_run:
        # Track tokens if model provides them
        if model and getattr(model, "last_input_token_count", None) is not None:
            total_input_tokens += model.last_input_token_count
            total_output_tokens += model.last_output_token_count
            if isinstance(step_log, ActionStep):
                step_log.input_token_count = model.last_input_token_count
                step_log.output_token_count = model.last_output_token_count
        async for message in pull_messages_from_step(
            step_log,
            conversation_id=conversation_id,
            additional_kwargs=additional_kwargs,
        ):
            yield message
    # final message
    yield Message(
        content=f"\n**Final answer:**\n{step_log.to_string()}\n",
        conversation_id=conversation_id,
        additional_kwargs={
            **(additional_kwargs or {}),
            "role": "assistant",
            "type": "completion_message",
        },
        final=True,
    )
