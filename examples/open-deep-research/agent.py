import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from galadriel.memory.memory_store import MemoryStore
from scripts.text_inspector_tool import TextInspectorTool
from scripts.text_web_browser import (
    ArchiveSearchTool,
    FinderTool,
    FindNextTool,
    PageDownTool,
    PageUpTool,
    SearchInformationTool,
    SimpleTextBrowser,
    VisitTool,
)
from scripts.visual_qa import visualizer

from galadriel import CodeAgent, AgentRuntime, ToolCallingAgent
from galadriel.clients import ChatUIClient
from galadriel import LiteLLMModel
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.tools.web3.market_data import coingecko, dexscreener
from galadriel.tools.web3.onchain.solana import (
    jupiter,
    raydium,
    native as solana_native,
    spl_token,
)

AUTHORIZED_IMPORTS = [
    "requests",
    "zipfile",
    "os",
    "pandas",
    "numpy",
    "sympy",
    "json",
    "bs4",
    "pubchempy",
    "xml",
    "yahoo_finance",
    "Bio",
    "sklearn",
    "scipy",
    "pydub",
    "io",
    "PIL",
    "chess",
    "PyPDF2",
    "pptx",
    "torch",
    "datetime",
    "fractions",
    "csv",
]


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"

load_dotenv(dotenv_path=Path(".") / ".env", override=True)

BROWSER_CONFIG = {
    "viewport_size": 1024 * 5,
    "downloads_folder": "downloads_folder",
    "request_kwargs": {
        "headers": {"User-Agent": user_agent},
        "timeout": 300,
    },
    "serpapi_key": os.getenv("SERPAPI_API_KEY"),
}

os.makedirs(f"./{BROWSER_CONFIG['downloads_folder']}", exist_ok=True)


text_limit = 150000

model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

document_inspection_tool = TextInspectorTool(model, text_limit)

browser = SimpleTextBrowser(**BROWSER_CONFIG)

WEB_TOOLS = [
    SearchInformationTool(browser),
    VisitTool(browser),
    PageUpTool(browser),
    PageDownTool(browser),
    FinderTool(browser),
    FindNextTool(browser),
    ArchiveSearchTool(browser),
    TextInspectorTool(model, text_limit),
]

text_webbrowser_agent = ToolCallingAgent(
    model=model,
    tools=WEB_TOOLS,
    max_steps=20,
    verbosity_level=2,
    planning_interval=4,
    name="search_agent",
    description="""Your job is to search the web deeply for topics related with web3 and crypto. assume your task is about those topics only. focus on those topics and provide only relevant answers
""",
    provide_run_summary=True,
)
text_webbrowser_agent.prompt_templates["managed_agent"]["task"] += """You can navigate to .txt online files.
If a non-html page is in another format, especially .pdf or a Youtube video, use tool 'inspect_file_as_text' to inspect it.
Additionally, if after some searching you find out that you need more information to answer the question, you can use `final_answer` with your request for clarification as argument to request for more information.
If you find the error "Error in code parsing: Your code snippet is invalid, because the regex pattern ```(?:py|python)?\n(.*?)\n``` was not found in it.", ignore it and call the final_answer tool"""

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

# WEB3_AGENT_PROMPT = """You are a highly knowledgeable crypto trading assistant with expertise in the Solana ecosystem. You have access to real-time market data and trading capabilities through various tools.
# Your goal is to help users understand market conditions and execute trades safely.
# When you get new question, see memory for previous answers. Here is the chat history: \n\n {{chat_history}} \n
# Answer this: {{request}}
# """

# Create a trading agent
trading_agent = CodeAgent(
    # prompt_template=WEB3_AGENT_PROMPT,  # Use the new comprehensive prompt
    model=model,
    tools=tools,
    add_base_tools=True,
    additional_authorized_imports=["json"],
    chat_memory=True,
    max_steps=6,
    name="web3_agent",
    description="""
    Agent which is able to handle any question related to cryptocurrency operations.
    A team member who is a highly knowledgeable crypto with expertise in the Solana ecosystem. It has access to real-time market data and trading capabilities through various tools. 
Call it when you want to:
- get cryptocurrency market data (eg token prices)
- get balance of some account
- swap tokens
    """,
    provide_run_summary=True,
)
# Make the trading agent more reliable by increasing the number of steps he can take to complete the task

MANAGER_PROMPT = """You are a helpful crypto analyst. Your goal is to provide users the insights about trading as well as answer quick questions about pricing and execute onchain operations like token swaps.
All questions about prices, tokens etc are related to crypto.
For quick questions, don't do a lot of planning, just provide the answers. For more complex questions eg about trading strategies, plan and execute a thorough research. {{request}}
History: {{chat_history}}
"""

manager_agent = CodeAgent(
    prompt_template=MANAGER_PROMPT,
    model=model,
    tools=[visualizer, document_inspection_tool],
    max_steps=12,
    verbosity_level=2,
    additional_authorized_imports=AUTHORIZED_IMPORTS,
    planning_interval=4,
    managed_agents=[text_webbrowser_agent],
)

client = ChatUIClient()

# Set up the runtime
runtime = AgentRuntime(
    inputs=[client],
    outputs=[client],
    agent=manager_agent,
    memory_store=MemoryStore(
        api_key=os.getenv("OPENAI_API_KEY"),
        embedding_model="text-embedding-3-large",
        agent_name="open_deep_research_agent",
        short_term_memory_limit=4,
    ),
)

# Run the agent
asyncio.run(runtime.run(stream=True))
