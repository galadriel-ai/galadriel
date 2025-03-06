import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.clients import Cron, ChatUIClient, DiscordClient, TerminalClient
from galadriel.entities import Message, PushOnlyQueue
from galadriel.memory.memory_store import MemoryStore
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    raydium,
    native as solana_native,
    spl_token,
)

TRADING_INTERVAL_SECONDS = 600

PROMPT = """
You are a helpful trading agent collaborating with a human trader in the Solana ecosystem.

### Chat History:
{{chat_history}}

### Request:
{{request}}

Use the chat history to provide relevant insights. Your goal is to identify the best trading opportunities while ensuring human confirmation before executing any trade. This is crucial.

**Guidelines:**
- Present trade analysis and top 3 concrete investment options, always inclue a 4th option to not trade.
- Make each option short (couple of sentences max) and add data to support the option if possible.
- Confirm with the trader before executing any trade by checking the most recent chat history.
- If confirmation is being given in the current request, proceed with execution; otherwise, ask again.
- Maintain a chat-like conversation with the human trader, this is also important.
- Chat history is important but it might be empty at the beginning of the conversation.
- VERY IMPORTANT: if you have the final answer, wrap it in the appropriate manner using a code block function. call the final_answer tool with a string as argument.

"""

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

solana_wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))

tools = [
    coingecko.GetMarketDataPerCategoriesTool(),
    coingecko.GetCoinMarketDataTool(),
    coingecko.GetCoinHistoricalDataTool(),
    dexscreener.GetTokenDataTool(),
]

trading_agent = CodeAgent(
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    max_steps=10,
    verbosity_level=2,
    # planning_interval=4,
    name="trading_agent",
    description="""A team member that is a trading agent specialized in executing token swaps on the Solana ecosystem. 
He can identify the best opportunities among tokens in the "pump-fun" and "solana-meme-coins" categories and execute trades using either Raydium or Jupiter (whichever is applicable). 
Note: For each swap, the maximal SOL out must not exceed 0.006 SOL.
Provide him as much context as possible.
""",
    provide_run_summary=True,
)
trading_agent.prompt_templates["managed_agent"]["task"] += """
Your goal is to execute a trade on the Solana ecosystem, focusing on the "pump-fun" and "solana-meme-coins" categories. Swaps are executed via Raydium or Jupiter, ensuring that each trade outputs no more than 0.006 SOL.
Trading Execution Plan:
1. Market Data Collection
   - Fetch market data for "pump-fun" and "solana-meme-coins" categories from CoinGecko
   - Extract coin IDs from the results
2. Token Analysis
   - Get detailed market data for each coin ID
   - Verify tokens belong to Solana ecosystem by checking mint addresses
   - Fetch on-chain data using dexscreener for liquidity, volume, and price movements
3. Opportunity Identification
   - Analyze tokens based on momentum, liquidity, and price action
   - Filter for tokens where swap would output ≤ 0.006 SOL
   - Skip execution if no suitable tokens found
4. Trade Execution
   - For qualifying tokens, determine optimal swap method:
     * Use Raydium if available
     * Otherwise use Jupiter
   - Execute swap with appropriate parameters
   - Ensure maximum SOL output is capped at 0.006 SOL
5. Transaction Monitoring
   - Log transaction details
   - Monitor performance of executed swaps
Additionally, if after some searching you find out that you need more information to answer the question, you can use `final_answer` with your request for clarification as argument to request for more information.
VERY IMPORTANT: if you have the final answer, wrap it in the appropriate manner using a code block function. call the final_answer tool with a string as argument."""

manager_agent = CodeAgent(
    prompt_template=PROMPT,
    model=model,
    tools=[],
    add_base_tools=True,
    max_steps=6,
    verbosity_level=2,
    # planning_interval=4,
    managed_agents=[trading_agent],
)
