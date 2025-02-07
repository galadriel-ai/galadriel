from galadriel.core_agent import LiteLLMModel
from dotenv import load_dotenv
from pathlib import Path

from discord_agent import ElonMuskAgent
from galadriel.tools.composio_converter import convert_action
from tools import get_time
from galadriel import AgentRuntime
from galadriel.clients import DiscordClient, TerminalClient, GradioClient
import os
import asyncio
from galadriel.logging_utils import get_agent_logger


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))


logger = get_agent_logger()

discord_client = DiscordClient(guild_id=os.getenv("DISCORD_GUILD_ID"))
terminal_client = TerminalClient()
composio_weather_tool = convert_action(
    os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER"
)

elon_musk_agent = ElonMuskAgent(
    character_json_path="agent.json",
    tools=[composio_weather_tool, get_time],
    model=model,
    max_steps=6,
)

agent = AgentRuntime(
    inputs=[terminal_client],
    outputs=[terminal_client],
    agent=elon_musk_agent,
)

asyncio.run(agent.run())
