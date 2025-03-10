import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent, ToolCallingAgent
from galadriel.clients import TerminalClient
from galadriel.memory.memory_store import MemoryStore

PROMPT = """
You are an intelligent intent routing system designed to analyze user requests and direct them to the most appropriate specialized agent.

## Your Core Function
1. Carefully analyze the user's request to identify the primary intent
2. Select the most appropriate specialized agent to handle this intent
3. Route the request to that agent
4. Return the response from the specialized agent to the user

## Context
### Chat History:
{{chat_history}}

### Current Request:
{{request}}

## Guidelines
- You MUST ALWAYS route the request to one of the provided specialized agents - NEVER respond directly
- For calculation-related requests (math, numbers, conversions), use the calculator_agent
- For ALL other requests (opinions, preferences, statements, questions), use the sentiment_agent
- When in doubt, default to the sentiment_agent
- Do not modify or interpret the user's request - pass it to the specialized agent as-is
- Every user input, no matter how simple, must be routed to one of the specialized agents

## Response Format
1. Briefly identify the detected intent (1 sentence)
2. Name the specialized agent you're routing to
3. Return the specialized agent's response
"""

MANAGED_AGENT_TASK_PROMPT = """
You're a helpful agent named '{{name}}'.
You have been submitted this task by your manager.
---
Task:
{{task}}
---
Provide your manager with your best answer to the task. It should be a short sentence.

Put all these in your final_answer tool, everything that you do not pass as an argument to final_answer will be lost.
And even if your task resolution is not successful, please return as much context as possible, so that your manager can act upon this feedback.
"""

load_dotenv(dotenv_path=Path(".") / ".env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

calculator_agent = CodeAgent(
    model=model,
    tools=[],
    max_steps=4,
    verbosity_level=2,
    name="calculator_agent",
    description="""A team member that can help with basic calculations.""",
    provide_run_summary=True,
)
calculator_agent.prompt_templates["managed_agent"]["task"] = MANAGED_AGENT_TASK_PROMPT

sentiment_agent = CodeAgent(
    model=model,
    tools=[],
    max_steps=4,
    verbosity_level=2,
    name="sentiment_agent",
    description="""A team member that can help with sentiment analysis even if the user's request is not directly related to sentiment.""",
    provide_run_summary=True,
)
sentiment_agent.prompt_templates["managed_agent"]["task"] = MANAGED_AGENT_TASK_PROMPT

intent_router = ToolCallingAgent(
    prompt_template=PROMPT,
    model=model,
    tools=[],
    max_steps=3,
    verbosity_level=2,
    managed_agents=[calculator_agent, sentiment_agent],
)

terminal_client = TerminalClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[terminal_client],
    outputs=[terminal_client],
    memory_store=MemoryStore(
        api_key=os.getenv("OPENAI_API_KEY"),
        embedding_model="text-embedding-3-large",
        agent_name="trading_agent",
        short_term_memory_limit=4,
    ),
    agent=intent_router,
)

# Run the agent
asyncio.run(runtime.run(stream=False))
