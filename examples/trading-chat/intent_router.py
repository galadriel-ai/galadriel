import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent, ToolCallingAgent
from galadriel.clients import ChatUIClient
from galadriel.memory.memory_store import MemoryStore
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
)

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
- For onchain operations (swap) use the trading agent
- When you use the trading agent, follow these rules:
    1. Return ONLY the raw JSON output from the tool WITHOUT any additional commentary, explanation, or formatting.
    2. DO NOT suggest additional steps or alternatives - execute exactly what the user requests.
    3. If token addresses are provided, use them directly. If token symbols are provided, use the most common/verified addresses.
- For ALL other requests (market research, pricing questions), use the research_agent
- When in doubt, default to the research_agent
- Do not modify or interpret the user's request - pass it to the specialized agent as-is
- Every user input, no matter how simple, must be routed to one of the specialized agents

## Response Format
Return the specialized agent's response without any modifications
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

research_agent = CodeAgent(
    model=model,
    tools=[
        coingecko.GetMarketDataPerCategoriesTool(),
        coingecko.GetCoinMarketDataTool(),
        coingecko.GetCoinHistoricalDataTool(),
        dexscreener.GetTokenDataTool(),
    ],
    max_steps=4,
    verbosity_level=2,
    name="research_agent",
    description="""A team member that can help with any reasearch.
""",
    provide_run_summary=True,
)
research_agent.prompt_templates["managed_agent"]["task"] = MANAGED_AGENT_TASK_PROMPT

TRADING_AGENT_PROMPT = """You are executor of onchain operations

IMPORTANT INSTRUCTIONS FOR TOKEN SWAPS:
1. When a user asks to swap tokens, IMMEDIATELY use the jupiter_prepare_swap tool with the provided parameters.
2. DO NOT ask for confirmation before executing the swap - proceed directly.
3. Return ONLY the raw JSON output from the tool WITHOUT any additional commentary, explanation, or formatting.
4. DO NOT suggest additional steps or alternatives - execute exactly what the user requests.
5. If token addresses are provided, use them directly. If token symbols are provided, use the most common/verified addresses.

Common token addresses:
- SOL: "So11111111111111111111111111111111111111112"
- USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
- BONK: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
- JUP: "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"

You have been submitted this task by your manager.
---
Task:
{{task}}
---
"""

solana_wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))

trading_agent = CodeAgent(
    model=model,
    tools=[
        jupiter.PrepareSwapTokenTool(solana_wallet),
    ],
    max_steps=4,
    verbosity_level=2,
    name="trading_chat",
    description="""A team member that can execute any onchain operation like tokens swap.
""",
    provide_run_summary=True,
)
trading_agent.prompt_templates["managed_agent"]["task"] = TRADING_AGENT_PROMPT

intent_router = ToolCallingAgent(
    prompt_template=PROMPT,
    model=model,
    tools=[],
    max_steps=3,
    verbosity_level=2,
    managed_agents=[research_agent, trading_agent],
)

terminal_client = ChatUIClient()

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
