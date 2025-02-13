import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import Cron
from galadriel.core_agent import LiteLLMModel
from galadriel.tools.twitter import TwitterPostTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
llm_model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

POST_INTERVAL_SECONDS = 5

AGENT_PROMPT = """
You are a humorous Twitter user. 
Every time you are called:
1. Generate a short tweet (1-2 sentences). About any topic.
2. Post the tweet.
"""

agent = CodeAgent(
    prompt_template=AGENT_PROMPT,
    model=llm_model,
    tools=[TwitterPostTool()],
)

runtime = AgentRuntime(
    agent=agent,
    inputs=[Cron(POST_INTERVAL_SECONDS)],
    outputs=[],  # No output, posting happens inside Agent
)

asyncio.run(runtime.run())
