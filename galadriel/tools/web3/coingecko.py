import os
import requests

from galadriel.core_agent import tool


@tool
def get_coin_price(task: str) -> str:
    """
    This is a tool that returns the price of given crypto token together with market cap,
    24hr vol and 24hr change.
    The output is a string.
    Args:
        task: The full name of the token. For example 'solana' not 'sol'
    """
    response = call_coingecko_api(
        "https://api.coingecko.com/api/v3/simple/price"
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


@tool
def get_coin_historical_data(task: str, days: str) -> str:
    """
    This is a tool that returns the historical data of given crypto token.
    The output is a string.
    Args:
        task: The full name of the token. For example 'solana' not 'sol'
        days: Data up to number of days ago, you may use any integer for number of days
    """
    response = call_coingecko_api(
        "https://api.coingecko.com/api/v3/coins/"
        + task
        + "/market_chart?vs_currency=usd&days="
        + days
    )
    data = response.json()
    return data


@tool
def fetch_trending_coins(dummy: str) -> str:
    """
    This is a tool that returns the trending coins on coingecko.
    The output is a string.
    Args:
        dummy: Dummy argument to make the tool work
    """
    response = call_coingecko_api("https://api.coingecko.com/api/v3/search/trending")
    data = response.json()
    return data


def call_coingecko_api(request: str) -> requests.Response:
    api_key = os.getenv("COINGECKO_API_KEY")
    headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
    return requests.get(
        request,
        headers=headers,
    )


if __name__ == "__main__":
    print(get_coin_price("ethereum"))
