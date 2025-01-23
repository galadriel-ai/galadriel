import os

from smolagents import tool


@tool
def coin_price_api(task: str) -> str:
    """
    This is a tool that returns the price of given crypto token together with market cap,
    24hr vol and 24hr change.
    The output is a string.
    Args:
        task: The full name of the token. For example 'solana' not 'sol'
    """
    import requests

    api_key = os.getenv("COINGECKO_API_KEY")
    headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price"
        "?vs_currencies=usd"
        "&include_market_cap=true"
        "&include_24hr_vol=true"
        "&include_24hr_change=true"
        "&include_last_updated_at=true"
        "&precision=2"
        "&ids=" + task,
        headers=headers,
    )
    data = response.json()
    return data


if __name__ == "__main__":
    print(coin_price_api("ethereum"))
