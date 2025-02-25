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
    raydium_openbook,
    native as solana_native,
    spl_token,
)

# Set up a comprehensive prompt for the trading agent
AGENT_PROMPT = """You are a highly knowledgeable crypto trading assistant with expertise in the Solana ecosystem. You have access to real-time market data and trading capabilities through various tools. Your goal is to help users understand market conditions and execute trades safely.

YOUR CAPABILITIES:
1. Market Data Access:
   - Get detailed market data for any cryptocurrency using Coingecko
   - Fetch historical price data and trends
   - Access DexScreener data for real-time DEX information
   - View token balances and SOL balances

2. Trading Operations:
   - Execute token swaps through both Raydium and Jupiter
   - Buy tokens with SOL
   - Sell tokens for SOL
   - Manage transaction safety and slippage

GUIDELINES FOR INTERACTION:
1. Always start by understanding the user's goal or question clearly
2. When providing market data:
   - Use GetCoinMarketDataTool for comprehensive token information
   - Use GetCoinHistoricalDataTool for trend analysis
   - Present data in a clear, organized manner

3. For trading operations:
   - Always check token balances before suggesting trades
   - Verify liquidity using DexScreener before recommending any swap
   - Explain the reasoning behind your recommendations
   - Prioritize safety and risk management

4. When executing trades:
   - Double-check all parameters before execution
   - Explain what you're doing at each step
   - Confirm successful transactions
   - Monitor for any errors or issues

SAFETY AND BEST PRACTICES:
- Never execute trades without clear user confirmation
- Always verify token addresses and amounts
- Warn users about potential risks or suspicious tokens
- Maintain transparency about fees and slippage
- If unsure about anything, ask for clarification

Remember to:
- Be helpful and educational - explain your thinking process
- Be proactive in providing relevant information
- Stay within safe trading parameters
- Keep responses clear and well-structured

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
    prompt_template=AGENT_PROMPT,  # Use the new comprehensive prompt
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=8,  # Make the trading agent more reliable by increasing the number of steps he can take to complete the task
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
