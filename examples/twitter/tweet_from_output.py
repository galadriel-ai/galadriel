import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import Cron
from galadriel.clients.twitter_post_client import TwitterPostClient
from galadriel.core_agent import LiteLLMModel

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
llm_model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

POST_INTERVAL_SECONDS = 5

AGENT_PROMPT = """
You are a humorous Twitter user. 
Generate a short tweet (1-2 sentences). About any topic.
"""

agent = CodeAgent(
    prompt_template=AGENT_PROMPT,
    model=llm_model,
    tools=[],
)

runtime = AgentRuntime(
    agent=agent,
    inputs=[Cron(POST_INTERVAL_SECONDS)],
    outputs=[TwitterPostClient()],
)

asyncio.run(runtime.run())
