import json
import requests
from galadriel.core_agent import tool


def get_token_list() -> list:
    """
    Returns a JSON string containing the list of tokens with their addresses.

    Returns:
        A JSON string with token names and addresses.
    """
    token_list = []
    response = requests.get("https://api.dexscreener.com/token-boosts/top/v1", timeout=30)

    if response.status_code == 200:
        _data = response.json()
        for token in _data:
            token_list.append({"address": token["tokenAddress"]})
    # return the first 5 tokens
    return token_list[:4]


@tool
def fetch_market_data(dummy: dict) -> str:  # pylint: disable=W0613
    """
    Fetches market data.

    Args:
        dummy: A dummy argument to match the required function signature.

    Returns:
        A JSON string containing market data.
    """
    token_list = get_token_list()
    market_data = []
    for token in token_list:
        response = requests.get(f"https://api.dexscreener.com/tokens/v1/solana/{token['address']}", timeout=30)
        if response.status_code == 200:
            _data = response.json()
            # Remove unrelated data to fit the context limit
            if "info" in _data[0]:
                del _data[0]["info"]
            if "url" in _data[0]:
                del _data[0]["url"]
            market_data.append(_data[0])
    return json.dumps(market_data)


@tool
def get_token_profile(task: str) -> str:  # pylint: disable=W0613
    """
    Get the latest token profiles. Returns the results as a big chunk of text with
    the chain, token address and the description of the Token.
    Args:
         task: empty
    """

    response = requests.get(
        "https://api.dexscreener.com/token-profiles/latest/v1",
        headers={},
        timeout=30,
    )
    _data = response.json()
    result = ""
    for token in _data:
        try:
            d = "Chain: " + token["chainId"]
            d += ", tokenAddress: " + token["tokenAddress"]
            d += ", description: " + token["description"]
            for link in token["links"]:
                d += f', {link["type"]}: {link["url"]}'
            result += d + "\n"
        except Exception:
            pass
    return result


@tool
def fetch_market_data_devnet(dummy: dict) -> str:
    """
    Fetches market data for the Solana Devnet.

    Args:
        dummy: A dummy argument to match the required function signature.

    Returns:
        A JSON string containing market data for the Solana Devnet.
    """
    mock_market_data = """[{"chainId": "solana", "dexId": "raydium", "pairAddress": "ftNSdLt7wuF9kKz6BxiUVWYWeRYGyt1RgL5sSjCVnJ2", "baseToken": {"address": "ELJKW7qz3DA93K919agEk398kgeY1eGvs2u3GAfV3FLn", "name": "DAIGE DEVNET", "symbol": "DAIGE"}, "quoteToken": {"address": "So11111111111111111111111111111111111111112", "name": "Wrapped SOL", "symbol": "SOL"}, "priceNative": "0.00000007161", "priceUsd": "0.00001362", "txns": {"m5": {"buys": 0, "sells": 1}, "h1": {"buys": 13, "sells": 25}, "h6": {"buys": 64, "sells": 126}, "h24": {"buys": 11057, "sells": 4767}}, "volume": {"h24": 946578.57, "h6": 8416.05, "h1": 2250.36, "m5": 0}, "priceChange": {"m5": -0.1, "h1": -30.85, "h6": -29.27, "h24": -87.54}, "liquidity": {"usd": 13537.61, "base": 496103405, "quote": 35.6157}, "fdv": 13627, "marketCap": 13627, "pairCreatedAt": 1739310341000, "boosts": {"active": 5000}}]"""
    return mock_market_data


if __name__ == "__main__":
    data = fetch_market_data(dummy={})
    print(data)
