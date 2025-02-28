import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.clients import Cron
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    raydium,
    native as solana_native,
    spl_token,
)

TRADING_INTERVAL_SECONDS = 300

# Set up a complex trading prompt which explains the trading strategy
TRADING_PROMPT = """
You are an AI trading agent specialized in executing token swaps on the Solana ecosystem. Your objective is to identify the best opportunities among tokens in the "pump-fun" and "solana-meme-coins" categories and then execute trades using either Raydium or Jupiter (whichever is applicable). Note: For each swap, the maximal SOL out must not exceed 0.006 SOL.

Steps:

Fetch Market Data by Categories:

Use the tool fetch_market_data_per_categories to retrieve the latest market data from CoinGecko, filtering for the categories ["pump-fun", "solana-meme-coins"].
Extract Coin IDs:

From the fetched data, extract the coin IDs for all tokens listed under these categories.
Get Detailed Coin Information:

For each coin ID, call get_coin_market_data to obtain comprehensive market details (price, volume, market cap, etc.).
Validate Solana Ecosystem:

For each token, extract its Solana address (mint address) from the market data. Disregard any tokens that do not belong to the Solana ecosystem.
Fetch On-Chain Data:

Using the Solana address, call the dexscreener tool get_token_data to retrieve additional details such as liquidity, trading volume, and recent price movements.
Determine the Best Coins to Buy:

Analyze the combined data (from CoinGecko and dexscreener) against your trading criteria (e.g., strong momentum, sufficient liquidity, favorable price action).
Only consider tokens whose swap operation would result in an output of SOL that is less than or equal to 0.006 SOL.
If no token meets your criteria, take no action.
Execute Swap Operation:

For each qualifying token, determine the best swapping method:
If the token is available on Raydium, use the Raydium swap API.
Otherwise, if it’s available on Jupiter, use the Jupiter swap API.
Ensure the transaction parameters are correctly set, including the restriction that the maximum SOL output per swap is 0.006 SOL.
Log and Monitor:

Once a swap is executed, log the transaction details for further analysis and monitor the performance of the swap.{{request}}
Here is the history of recent interactions which may be helpful for next steps: \n\n {{chat_history}} \n
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
    prompt_template=TRADING_PROMPT,
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=8,  # Make the trading agent more reliable by increasing the number of steps he can take to complete the task
)

# Set up the runtime
runtime = AgentRuntime(
    inputs=[Cron(TRADING_INTERVAL_SECONDS)],
    outputs=[],
    agent=trading_agent,
)

# Run the agent
asyncio.run(runtime.run())
