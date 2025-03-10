import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    native as solana_native,
    spl_token,
)


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

TRADING_AGENT_PROMPT = """You are a highly knowledgeable crypto trading assistant with expertise in the Solana ecosystem. You have access to real-time market data and trading capabilities through various tools. 
Your goal is to help users understand market conditions and execute trades safely.

IMPORTANT INSTRUCTIONS FOR TOKEN SWAPS:
1. When a user asks to swap/trade tokens, IMMEDIATELY call the jupiter_build_swap_transaction tool with the provided parameters, and return the raw JSON output from the tool as final answer WITHOUT any additional commentary, explanation, or formatting.
2. DO NOT convert the amount from SOL to lamports - use the amount in SOL directly.
3. DO NOT ask for confirmation before executing the swap - proceed directly.
4. DO NOT suggest additional steps or alternatives - execute exactly what the user requests.
5. If token addresses are provided, use them directly. If unknown token symbols are provided, use the dexscreener search_token_pair tool to get the most common/verified addresses.

Common token addresses:
- SOL: "So11111111111111111111111111111111111111112"
- USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
- BONK: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
- JUP: "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"

When you get new question, see memory for previous answers. Here is the chat history: \n\n {{chat_history}} \n 
Answer this: {{request}}
"""

solana_wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))

trading_agent = CodeAgent(
    model=model,
    tools=[
        solana_native.GetSOLBalanceTool(solana_wallet),
        spl_token.GetTokenBalanceTool(solana_wallet),
        dexscreener.SearchTokenPairTool(),
        jupiter.BuildSwapTransactionTool(solana_wallet),
    ],
    max_steps=4,
    verbosity_level=2,
    name="trading_chat",
    description="""A team member that can execute any onchain operation like tokens swap.
""",
    provide_run_summary=True,
)
trading_agent.prompt_templates["managed_agent"]["task"] = TRADING_AGENT_PROMPT
