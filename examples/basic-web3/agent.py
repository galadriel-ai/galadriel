import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent, LiteLLMModel
from galadriel.clients import SimpleMessageClient
from galadriel.tools.web3.market_data import dexscreener
from galadriel.tools.web3.onchain.solana import raydium
from galadriel.wallets.solana_wallet import SolanaWallet


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

solana_wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))

# Add agent with GPT-4o model and access to market data
agent = CodeAgent(
    model=model,
    tools=[dexscreener.SearchTokenPairTool(), raydium.SwapTokenTool(solana_wallet)],
    additional_authorized_imports=["json"],
)

# Add basic client which sends two messages to the agent and prints agent's result
client = SimpleMessageClient("What is the price of DAIGE today? Buy 0.001 SOL of DAIGE if the price is below 0.5 USD")

# Set up the runtime
runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())
