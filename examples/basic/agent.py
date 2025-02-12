import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient, ShutdownAfter
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Add agent with GPT-4o model and DuckDuckGo search tool
agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
)

# Add basic client which sends messages to the agent and prints agent's result
message_client = SimpleMessageClient("What is the capital of Estonia?", "What's the price of Solana today?")

# Set up the runtime with both message client and shutdown client
runtime = AgentRuntime(
    agent=agent,
    inputs=[message_client, ShutdownAfter(seconds=5)],
    outputs=[message_client],
)

# Run the agent
asyncio.run(runtime.run())
