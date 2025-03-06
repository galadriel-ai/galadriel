import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.onchain.solana import jupiter


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

TRADING_AGENT_PROMPT = """
You're a helpful agent named '{{name}}' and you are an expert in executing onchain operations.

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
