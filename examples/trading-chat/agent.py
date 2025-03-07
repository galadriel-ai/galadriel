import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.clients import TerminalClient
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
    coingecko.GetMarketDataPerCategoriesTool(),
    coingecko.GetCoinMarketDataTool(),
    coingecko.GetCoinHistoricalDataTool(),
    dexscreener.GetTokenDataTool(),
    solana_native.GetSOLBalanceTool(solana_wallet),
    spl_token.GetTokenBalanceTool(solana_wallet),
    raydium.SwapTokenTool(solana_wallet),
    jupiter.SwapTokenTool(solana_wallet),
]

# Create a trading agent
trading_agent = CodeAgent(
    prompt_template=AGENT_PROMPT,  # Use the new comprehensive prompt
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=6,  # Make the trading agent more reliable by increasing the number of steps he can take to complete the task
)

client = TerminalClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[client],
    outputs=[client],
    agent=trading_agent,
)

# Run the agent
asyncio.run(runtime.run())
