import asyncio
import os
from pathlib import Path

from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent, LiteLLMModel
from galadriel.clients import SimpleMessageClient
from galadriel.tools import DuckDuckGoSearchTool
from galadriel.tools.terminal import (
    ReadFileTool,
    WriteFileTool,
    RunCommandTool,
    RunCommandInBackgroundTool,
    SendKeyTool,
    TypeTextTool,
)

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Add agent with GPT-4o model and DuckDuckGo search tool
sandbox = Sandbox()

agent = CodeAgent(
    model=model,
    tools=[
        DuckDuckGoSearchTool(),
        ReadFileTool(sandbox),
        WriteFileTool(sandbox),
        RunCommandTool(sandbox),
        RunCommandInBackgroundTool(sandbox),
        SendKeyTool(sandbox),
        TypeTextTool(sandbox),
    ],
)

# Add basic client which sends two messages to the agent and prints agent's result
client = SimpleMessageClient("List the contents of the current directory")

# Set up the runtime
runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())
