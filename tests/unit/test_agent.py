from typing import Dict
from typing import List
from unittest.mock import MagicMock

from galadriel_agent import agent
from galadriel_agent.agent import AgentConfig
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.agent import UserAgent
from galadriel_agent.clients.client import Client
from galadriel_agent.clients.client import PushOnlyQueue
from galadriel_agent.entities import Message
from galadriel_agent.memory.in_memory import InMemoryShortTermMemory

CONVERSATION_ID = "ci1"
RESPONSE_MESSAGE = Message(content="goodbye")


class MockUserAgent(UserAgent):

    def __init__(self):
        self.called_messages: List[Message] = []

    async def run(self, request: Message) -> Message:
        self.called_messages.append(request)
        return RESPONSE_MESSAGE


class MockClient(Client):

    def __init__(self):
        self.output_requests: List[Message] = []
        self.output_responses: List[Message] = []
        self.output_proofs: List[str] = []

    async def start(self, queue: PushOnlyQueue) -> Dict:
        pass

    async def post_output(self, request: Message, response: Message, proof: str):
        self.output_requests.append(request)
        self.output_responses.append(response)
        self.output_proofs.append(proof)


def setup_function():
    agent.publish_proof = MagicMock()
    agent.generate_proof = MagicMock()
    agent.generate_proof.execute.return_value = "mock_proof"


async def test_adds_history():
    short_term_memory = InMemoryShortTermMemory()
    message = Message(content="hello", conversation_id=CONVERSATION_ID)
    short_term_memory.add(message)
    user_agent = MockUserAgent()
    galadriel_agent = GaladrielAgent(
        agent_config=AgentConfig(),
        clients=[],
        user_agent=user_agent,
        short_term_memory=short_term_memory,
    )
    request = Message(
        content="world",
        conversation_id=CONVERSATION_ID,
    )
    await galadriel_agent.run_request(request)
    expected = Message(content="hello world", conversation_id=CONVERSATION_ID)
    assert user_agent.called_messages[0] == expected


async def test_publishes_proof():
    user_agent = MockUserAgent()
    galadriel_agent = GaladrielAgent(
        agent_config=AgentConfig(),
        clients=[],
        user_agent=user_agent,
    )
    request = Message(
        content="hello",
        conversation_id=CONVERSATION_ID,
    )
    await galadriel_agent.run_request(request)
    agent.publish_proof.execute.assert_called_with(
        request, RESPONSE_MESSAGE, "mock_proof"
    )


async def test_post_output_to_client():
    user_agent = MockUserAgent()
    client = MockClient()
    galadriel_agent = GaladrielAgent(
        agent_config=AgentConfig(),
        clients=[client],
        user_agent=user_agent,
    )
    request = Message(
        content="hello",
        conversation_id=CONVERSATION_ID,
    )
    await galadriel_agent.run_request(request)
    assert client.output_requests[0] == request
    assert client.output_responses[0] == RESPONSE_MESSAGE
    assert client.output_proofs[0] == "mock_proof"
