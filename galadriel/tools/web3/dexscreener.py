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


if __name__ == "__main__":
    data = fetch_market_data(dummy={})
    print(data)
