import asyncio
import os
from galadriel import AgentRuntime, Agent, ToolCallingAgent
from galadriel.clients import TestClient
from galadriel.core_agent import LiteLLMModel
from galadriel.entities import Message
from galadriel.tools.composio_converter import convert_action
from dotenv import load_dotenv
from pathlib import Path


def _initialize_test_client():
    message1 = Message(
        content="What's the weather like in Tallinn?",
        conversation_id="conversationid123",
        additional_kwargs={"id": "id123", "author_id": "authorid123"},
    )
    message2 = Message(
        content="What's the weather like in Paris?",
        conversation_id="conversationid123",
        additional_kwargs={"id": "id124", "author_id": "authorid123"},
    )
    return TestClient(messages=[message1, message2])


# Load environment variables
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

# Initialize test client
test_client = _initialize_test_client()

# Initialize agent
composio_weather_tool = convert_action(
    os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER"
)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
weather_agent = ToolCallingAgent(tools=[composio_weather_tool], model=model)

agent = AgentRuntime(
    inputs=[test_client],
    outputs=[test_client],
    agent=weather_agent,
)

# Run agent
asyncio.run(agent.run())
