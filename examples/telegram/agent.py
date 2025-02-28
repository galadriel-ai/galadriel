import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from character_agent import CharacterAgent
from galadriel import AgentRuntime, LiteLLMModel
from galadriel.clients import TelegramClient
from galadriel.logging_utils import get_agent_logger
from galadriel.memory.memory_store import MemoryStore
from galadriel.tools.composio_converter import convert_action
from tools import get_time

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

logger = get_agent_logger()

# Set up Telegram client which
# - pushes users' messages to the agent
# - sends agent's responses back to the users
telegram_client = TelegramClient(token=os.getenv("TELEGRAM_TOKEN"), logger=logger)

# Setup Composio weather tool
composio_weather_tool = convert_action(os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER")

# Add agent with GPT-4o model and tools helpful to answer Discord users' questions
elon_musk_agent = CharacterAgent(
    character_json_path="agent.json",
    tools=[composio_weather_tool, get_time],
    model=model,
)

# Set up the runtime
runtime = AgentRuntime(
    inputs=[telegram_client],
    outputs=[telegram_client],
    agent=elon_musk_agent,
    memory_store=MemoryStore(
        api_key=os.getenv("OPENAI_API_KEY"), embedding_model="text-embedding-3-large", agent_name="elon_musk_agent"
    ),
)

# Run the agent
asyncio.run(runtime.run())
