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
        You are an expert crypto trading advisor. Based on the user's portfolio, current market data, and trading patterns, your task is to suggest one of three actions for each token: Buy, Sell, or Hold, and execute your decision using the available tools.
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
