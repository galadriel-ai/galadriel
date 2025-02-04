import json
import os
from typing import Callable, Dict, List

from galadriel_agent.core_agent import CodeAgent
from galadriel_agent.core_agent import Tool

from galadriel_agent.entities import Message

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
        5. Execute the trade: Use the 'swap_token' tool to perform the recommended action (Buy or Sell) for each token.
        """


class TradingAgent(CodeAgent):
    def __init__(
        self,
        tools: List[Tool],
        model: Callable[[List[Dict[str, str]]], str],
        add_base_tools: bool = False,
        additional_authorized_imports: List[str] = None,
    ):

        super().__init__(
            model=model,
            tools=tools,
            add_base_tools=add_base_tools,
            additional_authorized_imports=additional_authorized_imports,
        )

    async def execute(self, _request: Message) -> Message:
        response = self.run(TRADING_PROMPT)
        response_str = json.dumps(response)
        result = Message(content=response_str, additional_kwargs={})
        return result
