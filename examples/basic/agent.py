import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent = CodeAgent(
    model=model,
    tools=[
        DuckDuckGoSearchTool()
    ]
)

client = SimpleMessageClient("Explain A", "Explain B")

runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

asyncio.run(runtime.run())
