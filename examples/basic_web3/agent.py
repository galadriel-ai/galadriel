import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent, AgentOutput
from galadriel.clients import SimpleMessageClient, Cron
from galadriel.entities import Message
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent = CodeAgent(
    prompt_template="Help users with their trading questions: {{request}}?",
    model=model,
    tools=[
        DuckDuckGoSearchTool()
    ]
)

client = SimpleMessageClient(
    "What is the market sentiment these days?",
    interval_seconds=20 # Optional parameter to specify the interval between messages. The default is 60 sec.
)


runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

asyncio.run(runtime.run())
