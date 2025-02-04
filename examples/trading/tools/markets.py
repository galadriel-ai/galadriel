import requests
import json
from galadriel.core_agent import tool

# Predefined list of tokens with their addresses
# TOKENS = [
#    {"name": "DAIGE", "address": "HsNx7RirehVMy54xnFtcgCBPDMrwNnJKykageqdWpump"},
#    {"name": "TRUMP", "address": "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN"},
# ]


def get_token_list() -> list:
    """
    Returns a JSON string containing the list of tokens with their addresses.

    Returns:
        A JSON string with token names and addresses.
    """
    token_list = []
    response = requests.get("https://api.dexscreener.com/token-boosts/top/v1")

    if response.status_code == 200:
        data = response.json()
        for token in data:
            token_list.append({"address": token["tokenAddress"]})
    # return the first 5 tokens
    return token_list[:4]


@tool
def fetch_market_data(dummy: dict) -> str:
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
        response = requests.get(
            f"https://api.dexscreener.com/tokens/v1/solana/{token['address']}"
        )
        if response.status_code == 200:
            data = response.json()
            if "info" in data[0]:
                del data[0]["info"]
            if "url" in data[0]:
                del data[0]["url"]
            market_data.append(data[0])
    return json.dumps(market_data)


@tool
def format_output(user: str, operation: str, token: str, amount: float) -> str:
    """
    Formats the output in a JSON string.

    Args:
        user: The user's name.
        operation: The operation (Buy, Sell or Hold) to perform.
        token: The token symbol.
        amount: The amount to trade.

    Returns:
        A JSON string with the formatted output.
    """
    if operation not in ["Buy", "Sell", "Hold"]:
        return json.dumps({"error": "Invalid operation."})
    return json.dumps(
        {"user": user, "operation": operation, "token": token, "amount": amount}
    )


if __name__ == "__main__":
    data = fetch_market_data()
    print(data)
