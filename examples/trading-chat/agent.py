import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.clients import TerminalClient, ChatUIClient
from galadriel.clients.simple_message_client import SimpleMessageClient
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    raydium,
    native as solana_native,
    spl_token,
)

# Set up a comprehensive prompt for the trading agent
AGENT_PROMPT = """You are a highly knowledgeable crypto trading assistant with expertise in the Solana ecosystem. You have access to real-time market data and trading capabilities through various tools. 
Your goal is to help users understand market conditions and execute trades safely.

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

When you get new question, see memory for previous answers. Here is the chat history: \n\n {{chat_history}} \n 
Answer this: {{request}}
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
    # coingecko.GetMarketDataPerCategoriesTool(),
    # coingecko.GetCoinMarketDataTool(),
    # coingecko.GetCoinHistoricalDataTool(),
    dexscreener.GetTokenDataTool(),
    jupiter.PrepareSwapTokenTool(solana_wallet),
]

# Create a trading agent
trading_agent = CodeAgent(
    prompt_template=AGENT_PROMPT,  # Use the new comprehensive prompt
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    chat_memory=True,
    max_steps=3
)

client = ChatUIClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[client],
    outputs=[client],
    agent=trading_agent,
)

# Run the agent
asyncio.run(runtime.run())
