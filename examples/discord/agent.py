from galadriel.clients.terminal_client import TerminalClient
from galadriel.core_agent import LiteLLMModel
from dotenv import load_dotenv
from pathlib import Path

from character_agent import CharacterAgent
from galadriel.tools.composio_converter import convert_action
from tools import get_time
from galadriel import AgentRuntime
from galadriel.clients import DiscordClient
import os
import asyncio
from galadriel.logging_utils import get_agent_logger


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))


logger = get_agent_logger()

# Setup Discord client which
# - pushes users' messages to the agent
# - sends agent's responses back to the users
discord_client = DiscordClient(guild_id=os.getenv("DISCORD_GUILD_ID"))

# Setup Composio weather tool
# composio_weather_tool = convert_action(os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER")

# Add agent with GPT-4o model and tools helpful to answer Discord users' questions
elon_musk_agent = CharacterAgent(
    character_json_path="agent.json",
    tools=[get_time],
    model=model,
    max_steps=6,
)

# Set up the runtime
runtime = AgentRuntime(
    inputs=[TerminalClient()],
    outputs=[discord_client, TerminalClient()],
    agent=elon_musk_agent,
)

# Run the agent
asyncio.run(runtime.run())
