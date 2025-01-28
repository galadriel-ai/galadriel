from smolagents.models import LiteLLMModel
from dotenv import load_dotenv
from pathlib import Path

from discord_agent import DiscordMultiStepAgent
from tools import get_weather, get_time
from galadriel_agent.clients.memory_repository import memory_repository
from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.discord_bot import DiscordClient
import os
import asyncio
from galadriel_agent.logging_utils import get_agent_logger


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))


logger = get_agent_logger()

discord_client = DiscordClient(guild_id=os.getenv("DISCORD_GUILD_ID"), logger=logger)

discord_agent = DiscordMultiStepAgent(
    memory_repository=memory_repository,
    character_json_path="./agent_configuration/example_elon_musk.json",
    tools=[get_weather, get_time],
    model=model,
    max_steps=6,
)

agent = GaladrielAgent(
    agent_config=None,
    clients=[discord_client],
    user_agent=discord_agent,
    s3_client=None,
)

asyncio.run(agent.run())
