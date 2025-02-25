from typing import AsyncGenerator, Dict, Optional
from typing import List
from unittest.mock import MagicMock, AsyncMock

import pytest

from galadriel import AgentRuntime, Agent, AgentInput, AgentOutput
from galadriel import agent
from galadriel.entities import Message, PushOnlyQueue, Pricing
from galadriel.errors import PaymentValidationError

CONVERSATION_ID = "ci1"
RESPONSE_MESSAGE = Message(content="goodbye")


class MockAgent(Agent):
    def __init__(self):
        self.called_messages: List[Message] = []

    async def execute(self, request: Message, memory: Optional[str] = None) -> Message:
        self.called_messages.append(request)
        return RESPONSE_MESSAGE

    async def execute_stream(self, request: Message, memory: Optional[str] = None) -> AsyncGenerator[Message, None]:
        self.called_messages.append(request)
        yield RESPONSE_MESSAGE


class MockAgentInput(AgentInput):
    async def start(self, queue: PushOnlyQueue) -> Dict:
        pass


class MockAgentOutput(AgentOutput):
    def __init__(self):
        self.output_requests: List[Message] = []
        self.output_responses: List[Message] = []
        # self.output_proofs: List[str] = []

    async def send(self, request: Message, response: Message):
        self.output_requests.append(request)
        self.output_responses.append(response)
        # self.output_proofs.append(proof)


def setup_function():
    agent.publish_proof = MagicMock()
    agent.generate_proof = MagicMock()
    agent.generate_proof.execute.return_value = "mock_proof"


@pytest.mark.skip(reason="Proof publishing functionality not yet implemented")
async def test_publishes_proof():
    user_agent = MockAgent()
    runtime = AgentRuntime(
        inputs=[],
        outputs=[],
        agent=user_agent,
    )
    request = Message(
        content="hello",
        conversation_id=CONVERSATION_ID,
    )
    await runtime._run_request(request)
    agent.publish_proof.execute.assert_called_with(request, RESPONSE_MESSAGE, "mock_proof")


async def test_post_output_to_client():
    user_agent = MockAgent()
    input_client = MockAgentInput()
    output_client = MockAgentOutput()
    runtime = AgentRuntime(
        inputs=[input_client],
        outputs=[output_client],
        agent=user_agent,
    )
    request = Message(
        content="hello",
        conversation_id=CONVERSATION_ID,
    )
    await runtime._run_request(request)
    assert output_client.output_requests[0] == request
    assert output_client.output_responses[0] == RESPONSE_MESSAGE
    # assert output_client.output_proofs[0] == "mock_proof"


async def test_payment_validation():
    """Test payment validation flow."""
    user_agent = MockAgent()
    pricing = Pricing(cost=0.1, wallet_address="HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH")
    runtime = AgentRuntime(inputs=[], outputs=[], agent=user_agent, pricing=pricing)

    # Mock successful payment validation
    runtime.solana_payment_validator.execute = AsyncMock(
        return_value=AsyncMock(task="validated task", signature="sig123")
    )

    request = Message(content="test with payment sig123")
    await runtime._run_request(request)

    assert len(user_agent.called_messages) == 1
    assert user_agent.called_messages[0].content == "validated task"


async def test_payment_validation_failure():
    """Test payment validation failure."""
    user_agent = MockAgent()
    output_client = MockAgentOutput()
    pricing = Pricing(cost=0.1, wallet_address="HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH")
    runtime = AgentRuntime(inputs=[], outputs=[output_client], agent=user_agent, pricing=pricing)

    # Mock failed payment validation
    runtime.solana_payment_validator.execute = AsyncMock(side_effect=PaymentValidationError("Invalid payment"))

    request = Message(content="test with invalid payment")
    await runtime._run_request(request)

    assert output_client.output_responses == []
    assert len(user_agent.called_messages) == 0
