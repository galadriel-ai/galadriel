import os

from galadriel import LiteLLMModel
from galadriel.agent import CodeAgent
from galadriel.tools.web3.market_data import coingecko, dexscreener


model = LiteLLMModel(
    model_id="openai/gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

MANAGED_AGENT_TASK_PROMPT = """
You're a helpful agent named '{{name}}'.
You have been submitted this task by your manager which is working closely with a human trader.
---
Task:
{{task}}
---

**Guidelines:**
- Present trade analysis and top 3 concrete investment options, always inclue a 4th option to not trade.
- Make each option short (couple of sentences max) and add data to support the option if possible.
- Confirm with the trader before executing any trade by checking the most recent chat history.
- If confirmation is being given in the current request, proceed with execution; otherwise, ask again.
- Maintain a chat-like conversation with the human trader, this is also important.
- VERY IMPORTANT: if you have the final answer, wrap it in the appropriate manner using a code block function. call the final_answer tool with a string as argument.

Provide your manager with your best answer to the task.

Put all these in your final_answer tool, everything that you do not pass as an argument to final_answer will be lost.
And even if your task resolution is not successful, please return as much context as possible, so that your manager can act upon this feedback.
"""

research_agent = CodeAgent(
    model=model,
    tools=[
        coingecko.GetMarketDataPerCategoriesTool(),
        coingecko.GetCoinMarketDataTool(),
        coingecko.GetCoinHistoricalDataTool(),
        dexscreener.GetTokenDataTool(),
    ],
    max_steps=6,
    verbosity_level=2,
    name="research_agent",
    description="""A team member that can help with any reasearch in the web3 and crypto space.""",
    provide_run_summary=True,
)
research_agent.prompt_templates["managed_agent"]["task"] = MANAGED_AGENT_TASK_PROMPT
