from galadriel.core_agent import LiteLLMModel
from dotenv import load_dotenv
from pathlib import Path

from character_agent import TwitterCharacterAgent
from galadriel.tools.composio_converter import convert_action
from tools import get_time
from galadriel import AgentRuntime
from galadriel.clients import TwitterPostClient, Cron
import os
import asyncio
from galadriel.logging_utils import get_agent_logger


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))


logger = get_agent_logger()


twitter_post_client = TwitterPostClient()

composio_weather_tool = convert_action(os.getenv("COMPOSIO_API_KEY"), "WEATHERMAP_WEATHER")

elon_musk_agent = TwitterCharacterAgent(
    character_json_path="agent.json",
    tools=[composio_weather_tool, get_time],
    model=model,
    max_steps=6,
)

runtime = AgentRuntime(
    inputs=[Cron(10)],
    outputs=[twitter_post_client],
    agent=elon_musk_agent,
)

asyncio.run(runtime.run())
