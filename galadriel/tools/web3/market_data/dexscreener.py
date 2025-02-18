import json
import requests
from galadriel.core_agent import tool


@tool
def get_token_data(ecosystem: str, token_address: str) -> str:
    """Fetch detailed data for a specific token on a given ecosystem.

    Retrieves detailed data for a specific token from DexScreener and formats
    it as a JSON string. Removes unnecessary data to fit context limits.

    Args:
        ecosystem: The ecosystem of the token (e.g., 'solana', 'ethereum')
        token_address: The address of the token to fetch data for

    Returns:
        A JSON string containing detailed data for the token
    """
    response = requests.get(
        f"https://api.dexscreener.com/tokens/v1/{ecosystem}/{token_address}", timeout=30
    )
    if response.status_code == 200:
        data = response.json()
        # Remove unrelated data to fit the context limit
        if "info" in data[0]:
            del data[0]["info"]
        return json.dumps(data[0])
    return json.dumps({})


if __name__ == "__main__":
    data = get_token_data("solana", "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump")
    print(data)
