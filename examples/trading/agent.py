import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime
from galadriel.agent import CodeAgent
from galadriel.core_agent import LiteLLMModel
from galadriel.clients import Cron
from galadriel.tools.web3.market_data import market_data_devnet
from galadriel.tools.web3.onchain.solana import raydium_cpmm
from galadriel.tools.web3.onchain.solana import common as solana_common

TRADING_INTERVAL_SECONDS = 300

# Set up a complex trading prompt which explains the trading strategy
TRADING_PROMPT = """
        You are an expert crypto trading advisor. Based on the user's portfolio, current market data, and trading patterns, your task is to suggest one of three actions for each token: Buy, Sell, or Hold. Follow these steps to determine the decision and execute the trade:
        1. Understand the user's position: Evaluate the current holdings of the user (e.g., Alice has 10 SOL).
        2. Analyze market data for each token: Consider the following for decision-making:
           - Price Trends: Evaluate recent price changes (e.g., m5, h1, h6, h24).
           - Volume: Look for significant trading volume changes in the last 24 hours.
           - Liquidity: Assess the token's liquidity to ensure ease of trade.
           - Transaction Trends: Check buy and sell counts to detect market sentiment.
        3. Compare market data with the user's holdings:
           - Recommend Buy if the token shows strong potential (e.g., price dip with high trading volume).
           - Recommend Sell if the price has significantly increased, or there are signs of weakening demand.
           - Recommend Hold if the token's market position is stable or no clear trend is observed.
        4. Based on the analysis, provide a decision for each token in the user's portfolio.
        5. Execute the trade: Use the relevant tools to perform the recommended action (Buy or Sell) for each token.
        """

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Prepare a Web3 specific toolkit, relevant for the trading agent
tools = [
    market_data_devnet.fetch_market_data,
    raydium_cpmm.BuyTokenWithSolTool(),
    solana_common.GetAdminWalletAddressTool(),
    solana_common.GetUserBalanceTool(),
]

# Create a trading agent
trading_agent = CodeAgent(
    prompt_template=TRADING_PROMPT,
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=8,
)

# Set up the runtime
runtime = AgentRuntime(
    inputs=[Cron(TRADING_INTERVAL_SECONDS)],
    outputs=[],
    agent=trading_agent,
)

# Run the agent
asyncio.run(runtime.run())
