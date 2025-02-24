import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.clients import Cron, TerminalClient
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    raydium_openbook,
    native as solana_native,
    spl_token,
)

TRADING_INTERVAL_SECONDS = 300

# Set up a complex trading prompt which explains the trading strategy
TRADING_CHAT_PROMPT = """
You are an AI trading agent specialized in executing token swaps on the Solana ecosystem. Your objective is to help the user finding the best opportunities among tokens in the given category they ask about and then execute trades using either Raydium or Jupiter (whichever is applicable). Note: For each swap, the maximal SOL out must not exceed 0.006 SOL.

In order to execute Swap Operation:
    For each qualifying token, determine the best swapping method:
    If the token is available on Raydium, use the Raydium swap API.
    Otherwise, if it’s available on Jupiter, use the Jupiter swap API.

You have access to Coingecko's market data.
{{request}}
"""

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

solana_wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))

# Prepare a Web3 specific toolkit, relevant for the trading agent
tools = [
    coingecko.GetMarketDataPerCategoriesTool(),
    coingecko.GetCoinMarketDataTool(),
    coingecko.GetCoinHistoricalDataTool(),
    dexscreener.GetTokenDataTool(),
    solana_native.GetSOLBalanceTool(solana_wallet),
    spl_token.GetTokenBalanceTool(solana_wallet),
    raydium_openbook.BuyTokenWithSolTool(solana_wallet),
    raydium_openbook.SellTokenForSolTool(solana_wallet),
    jupiter.SwapTokenTool(solana_wallet),
]

# Create a trading agent
trading_agent = CodeAgent(
    prompt_template=TRADING_CHAT_PROMPT,
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=8,  # Make the trading agent more reliable by increasing the number of steps he can take to complete the task
)

client = TerminalClient() # To be replaced with Gradio

# Set up the runtime
runtime = AgentRuntime(
    inputs=[client],
    outputs=[client],
    agent=trading_agent,
)

# Run the agent
asyncio.run(runtime.run())
