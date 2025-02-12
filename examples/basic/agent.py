import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Add agent with GPT-4o model and DuckDuckGo search tool
agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
)

# Add basic client which sends two messages to the agent and prints agent's result
client = SimpleMessageClient("What is the capital of Estonia?", "What's the price of Solana today?")

# Set up the runtime
runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())
