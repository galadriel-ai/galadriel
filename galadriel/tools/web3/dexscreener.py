import json
import requests
from galadriel.core_agent import tool


def get_token_list() -> list:
    """Fetch a list of top tokens from DexScreener.

    Retrieves a list of top tokens from DexScreener's token-boosts endpoint
    and extracts their addresses.

    Returns:
        list: A list of dictionaries containing token addresses
              Limited to the first 4 tokens for performance

    Note:
        The endpoint used is DexScreener's token-boosts/top/v1
        Each dictionary in the returned list has the format:
        {"address": "token_address"}
    """
    token_list = []
    response = requests.get("https://api.dexscreener.com/token-boosts/top/v1", timeout=30)

    if response.status_code == 200:
        _data = response.json()
        for token in _data:
            token_list.append({"address": token["tokenAddress"]})
    # return the first 4 tokens
    return token_list[:4]


@tool
def fetch_market_data(dummy: dict) -> str:  # pylint: disable=W0613
    """Fetch detailed market data for top tokens on Solana.

    Retrieves market data for the top tokens from DexScreener and formats
    it as a JSON string. Removes unnecessary data to fit context limits.

    Args:
        dummy (dict): Unused parameter required by tool decorator

    Returns:
        str: JSON string containing market data for top tokens

    Note:
        - Uses get_token_list() to determine which tokens to fetch
        - Removes 'info' and 'url' fields from the response to reduce size
        - Data is fetched from DexScreener's tokens/v1/solana endpoint
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
    """Fetch the latest token profiles from DexScreener.

    Retrieves detailed profile information for tokens, including chain,
    address, description, and associated links.

    Args:
        task (str): Unused parameter required by tool decorator

    Returns:
        str: A formatted string containing token profile information

    Note:
        - Data is fetched from DexScreener's token-profiles/latest/v1 endpoint
        - Each token profile includes:
            * Chain ID
            * Token address
            * Description
            * Associated links (with type and URL)
        - Invalid or incomplete profiles are skipped
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
