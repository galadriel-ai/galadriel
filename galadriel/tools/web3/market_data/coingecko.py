import json
import os
from abc import ABC

from typing import List

import requests

from galadriel.tools import Tool


class CoingeckoTool(Tool, ABC):
    """Base class for Coingecko API tools.

    This class provides common functionality for accessing the Coingecko API,
    including API key management and authentication.

    Required Environment Variables:
        COINGECKO_API_KEY: Your Coingecko API key for authentication

    For more information about Coingecko API, see:
    https://www.coingecko.com/api/documentation
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Coingecko tool.

        Args:
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class

        Raises:
            ValueError: If COINGECKO_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("COINGECKO_API_KEY")
        if not self.api_key:
            raise ValueError("COINGECKO_API_KEY environment variable is not set")
        super().__init__(*args, **kwargs)


class GetCoinPriceTool(CoingeckoTool):
    """Tool for retrieving current cryptocurrency price and market data.

    Fetches current price, market cap, 24hr volume, and 24hr price change
    for a specified cryptocurrency.
    """

    name = "coingecko_get_coin_price"
    description = "Get current prices and market data for cryptocurrencies using their Coingecko API IDs. Returns price, market cap, 24h volume and 24h price change percentage."  # pylint: disable=C0301
    inputs = {
        "token_names": {
            "type": "array",
            "description": "The list of token names. Names must be full, for example 'solana' not 'sol'",
            "items": {"type": "string"},
        },
        "currencies": {
            "type": "array",
            "description": "The list of currencies to convert the price to. Default is USD",
            "items": {"type": "string"},
        },
    }
    output_type = "string"

    def forward(self, token_names: List[str], currencies: List[str]) -> str:  # pylint: disable=W0221
        """Fetch current price and market data for a cryptocurrency.

        Args:
            token_names (List[str]): The list of full name of the cryptocurrency (e.g., 'bitcoin')
            currencies (List[str]): The list of currencies to convert the price to. The list of supported currencies is [here](https://docs.coingecko.com/v3.0.1/reference/simple-supported-currencies

        Returns:
            str: JSON string containing price and market data

        Note:
            Returns data including:
            - Current price in USD
            - Market capitalization
            - 24-hour trading volume
            - 24-hour price change percentage
            - Last updated timestamp
        """
        base_url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "vs_currencies": ",".join(currencies),
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
            "precision": "2",
            "ids": ",".join(token_names),
        }

        url = f"{base_url}?" + "&".join(f"{k}={v}" for k, v in params.items())
        response = call_coingecko_api(
            api_key=self.api_key,
            request=url,
        )
        return response.json()


class GetCoinMarketDataTool(CoingeckoTool):
    """Tool for retrieving current cryptocurrency market data.

    Fetches current market data for a specified cryptocurrency, including
    price, market cap, 24hr volume, and 24hr price change percentage.
    """

    name = "coingecko_get_coin_market_data"
    description = "Get comprehensive coin data from CoinGecko including name, price, market data and exchange tickers based on coin ID"
    inputs = {
        "coin_id": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        }
    }
    output_type = "string"

    def forward(self, coin_id: str) -> str:  # pylint: disable=W0221
        """Fetch current market data for a cryptocurrency.

        Args:
            coin_id (str): The coingecko id of the cryptocurrency (e.g., 'bitcoin')

        Returns:
            str: JSON string containing market data

        Note:
            Returns data including:
            - Current price in USD
            - Market capitalization
            - 24-hour trading volume
            - 24-hour price change percentage
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/coins/" + coin_id,
        )
        data = response.json()
        return data


class GetCoinHistoricalDataTool(CoingeckoTool):
    """Tool for retrieving historical cryptocurrency price data.

    Fetches historical price data for a specified cryptocurrency over
    a given time period.
    """

    name = "coingecko_get_coin_historical_data"
    description = "Get historical market data for a cryptocurrency by its CoinGecko ID, including price, market cap, and 24h volume over time. Returns time series data with UNIX timestamps and values in USD."
    inputs = {
        "token": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        },
        "days": {
            "type": "string",
            "description": "Data up to number of days ago, you may use any integer for number of days",
        },
    }
    output_type = "string"

    def forward(self, token: str, days: str) -> str:  # pylint: disable=W0221
        """Fetch historical price data for a cryptocurrency.

        Args:
            token (str): The full name of the cryptocurrency (e.g., 'bitcoin')
            days (str): Number of days of historical data to retrieve

        Returns:
            str: JSON string containing historical price data

        Note:
            Returns time series data including prices, market caps, and volumes
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/coins/" + token + "/market_chart?vs_currency=usd&days=" + days,
        )
        data = response.json()
        return data


class GetMarketDataPerCategoriesTool(CoingeckoTool):
    """Tool for retrieving market data for cryptocurrencies in specific categories.

    Fetches market data for cryptocurrencies in specific categories from CoinGecko.
    """

    name = "coingecko_get_market_data_per_categories"
    description = "Get market data for cryptocurrencies in specific categories from CoinGecko. Returns market data for the specified categories."
    inputs = {
        "categories": {
            "type": "array",
            "description": "The categories of the cryptocurrencies to get data for",
        }
    }
    output_type = "string"

    def forward(self, categories: list) -> str:  # pylint: disable=W0221
        """Fetch market data for cryptocurrencies in specific categories.

        Args:
            categories: The categories of the cryptocurrencies to fetch data for

        Returns:
            JSON string containing market data for the specified categories
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/coins/categories?order=market_cap_change_24h_asc",
        )
        data = response.json()

        filtered_data = [category_data for category_data in data if category_data["id"] in categories]
        return json.dumps(filtered_data)


class FetchTrendingCoinsTool(CoingeckoTool):
    """Tool for retrieving currently trending cryptocurrencies.

    Fetches a list of cryptocurrencies that are currently trending
    on CoinGecko.
    """

    name = "coingecko_fetch_trending_coins"
    description = "Get currently trending cryptocurrencies from CoinGecko. Returns a list of trending coins with their market data."
    inputs = {
        "dummy": {
            "type": "string",
            "description": "Dummy argument to make the tool work",
        }
    }
    output_type = "string"

    def forward(self, dummy: str) -> str:  # pylint: disable=W0221, W0613
        """Fetch currently trending cryptocurrencies.

        Args:
            dummy (str): Unused parameter required by tool interface

        Returns:
            str: JSON string containing trending cryptocurrency data
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/search/trending",
        )
        data = response.json()
        return data


def call_coingecko_api(api_key: str, request: str) -> requests.Response:
    """Make an authenticated request to the Coingecko API.

    Args:
        api_key (str): Coingecko API key for authentication
        request (str): Complete API request URL

    Returns:
        requests.Response: Response from the Coingecko API

    Note:
        Includes a 30-second timeout for API requests
    """
    headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
    return requests.get(
        request,
        headers=headers,
        timeout=30,
    )


if __name__ == "__main__":
    fetch_market_data = GetMarketDataPerCategoriesTool()
    print(fetch_market_data.forward("pump-fun"))
