import os
import requests

from galadriel.core_agent import Tool


class CoingeckoTool(Tool):
    """
    Base class for Coingecko tools that require wallet access.
    """

    def __init__(self, *args, **kwargs):
        self.api_key = os.getenv("COINGECKO_API_KEY")
        if not self.api_key:
            raise ValueError("COINGECKO_API_KEY environment variable is not set")
        super().__init__(*args, **kwargs)


class GetCoinPriceTool(CoingeckoTool):
    name = "get_coin_price"
    description = "This is a tool that returns the price of given crypto token together with market cap, 24hr vol and 24hr change."  # pylint: disable=C0301
    inputs = {
        "task": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        }
    }
    output_type = "string"

    def forward(self, task: str) -> str:  # pylint: disable=W0221
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/simple/price"
            "?vs_currencies=usd"
            "&include_market_cap=true"
            "&include_24hr_vol=true"
            "&include_24hr_change=true"
            "&include_last_updated_at=true"
            "&precision=2"
            "&ids=" + task,
        )
        data = response.json()
        return data


class GetCoinHistoricalDataTool(CoingeckoTool):
    name = "get_coin_historical_data"
    description = "This is a tool that returns the historical data of given crypto token."
    inputs = {
        "task": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        },
        "days": {
            "type": "string",
            "description": "Data up to number of days ago, you may use any integer for number of days",
        },
    }
    output_type = "string"

    def forward(self, task: str, days: str) -> str:  # pylint: disable=W0221
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/coins/" + task + "/market_chart?vs_currency=usd&days=" + days,
        )
        data = response.json()
        return data


class FetchTrendingCoinsTool(CoingeckoTool):
    name = "fetch_trending_coins"
    description = "This is a tool that returns the trending coins on coingecko."
    inputs = {
        "dummy": {
            "type": "string",
            "description": "Dummy argument to make the tool work",
        }
    }
    output_type = "string"

    def forward(self, dummy: str) -> str:  # pylint: disable=W0221, W0613
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/search/trending",
        )
        data = response.json()
        return data


def call_coingecko_api(api_key: str, request: str) -> requests.Response:
    headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
    return requests.get(
        request,
        headers=headers,
        timeout=30,
    )


if __name__ == "__main__":
    get_coin_price = GetCoinPriceTool()
    print(get_coin_price.forward("ethereum"))
