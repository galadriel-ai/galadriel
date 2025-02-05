import asyncio
from galadriel import AgentRuntime, CodeAgent
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool
from galadriel.clients import SimpleMessageClient
from galadriel.entities import Message

from galadriel.clients import SimpleMessageClient

model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent = CodeAgent(
    model=model,
    tools=[
        DuckDuckGoSearchTool()
    ]
)

client = SimpleMessageClient("Explain the concept of blockchain")

runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

asyncio.run(runtime.run())