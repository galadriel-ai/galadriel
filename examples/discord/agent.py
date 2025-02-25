import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from character_agent import CharacterAgent
from galadriel import AgentRuntime, LiteLLMModel
from galadriel.clients import DiscordClient
from galadriel.logging_utils import get_agent_logger
from galadriel.memory.memory_repository import MemoryRepository
from galadriel.state.agent_state_repository import AgentStateRepository
from galadriel.tools.composio_converter import convert_action
from tools import get_time

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))


logger = get_agent_logger()

# Setup Discord client which
# - pushes users' messages to the agent
# - sends agent's responses back to the users
discord_client = DiscordClient(guild_id=os.getenv("DISCORD_GUILD_ID"))

# Setup Composio weather tool
composio_weather_tool = convert_action(os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER")

# Add agent with GPT-4o model and tools helpful to answer Discord users' questions
elon_musk_agent = CharacterAgent(
    character_json_path="agent.json",
    tools=[get_time],
    model=model,
)

# Recover previous agent state from S3
agent_state_repository = AgentStateRepository()
agent_state = agent_state_repository.download_agent_state()
# Create memory repository, using previous state if available
memory_repository = MemoryRepository(
    api_key=os.getenv("OPENAI_API_KEY"), agent_name="elon_musk_agent", memory_folder_path=agent_state.memory_folder_path
)

# Set up the runtime
runtime = AgentRuntime(
    inputs=[discord_client],
    outputs=[discord_client],
    agent=elon_musk_agent,
    memory_repository=memory_repository,
)

# Run the agent
asyncio.run(runtime.run())

# Save memory to local file
memory_repository.save_data_locally(memory_repository.memory_folder_path)

# Save agent state
agent_state_repository.upload_agent_state(agent_state.memory_folder_path)
