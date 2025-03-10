import json
import requests
from typing import Dict, Any

from galadriel.tools import Tool

DEXSCREENER_API_URL = "https://api.dexscreener.com"


class GetTokenDataTool(Tool):
    """Tool for fetching detailed token data from DexScreener.

    Retrieves and formats token data from DexScreener API, removing unnecessary
    information to fit context limits.
    """

    name = "dexscreener_get_token_data"
    description = "Get detailed token pair data from DexScreener by token address. Returns array of pairs with chain ID, DEX info, base/quote tokens, price, volume, liquidity and other market data."
    inputs = {
        "ecosystem": {
            "type": "string",
            "description": "The ecosystem of the token (e.g., 'solana', 'ethereum')",
        },
        "token_address": {
            "type": "string",
            "description": "The address of the token to fetch data for",
        },
    }
    output_type = "object"

    def forward(self, ecosystem: str, token_address: str) -> Dict[str, Any]:
        """Fetch token data from DexScreener API.

        Args:
            ecosystem (str): The ecosystem of the token (e.g., 'solana', 'ethereum')
            token_address (str): The address of the token to fetch data for

        Returns:
            Dict[str, Any]: Token data as a dictionary, or empty dict if request fails
        """
        try:
            response = requests.get(f"{DEXSCREENER_API_URL}/tokens/v1/{ecosystem}/{token_address}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Remove unrelated data to fit the context limit
                if data and len(data) > 0:
                    if "info" in data[0]:
                        del data[0]["info"]
                    return data[0]
            return {}
        except Exception as e:
            print(f"Error fetching token data: {str(e)}")
            return {}


class SearchTokenPairTool(Tool):
    """Tool for searching for token pairs on DexScreener.

    Retrieves and formats token pair data from DexScreener API, removing unnecessary
    information to fit context limits.
    """

    name = "dexscreener_search_token_pair"
    description = "Search for token pairs on DexScreener by token symbol. Returns pairs with price, volume, liquidity and other market data."
    inputs = {
        "token_symbol": {
            "type": "string",
            "description": "The symbol of the token to search for",
        },
    }
    output_type = "string"

    def forward(self, token_symbol: str) -> str:
        """Search for token pairs on DexScreener.

        Args:
            token_symbol (str): The symbol of the token to search for

        Returns:
            str: Token pair data as a string, or empty string if request fails
        """
        try:
            response = requests.get(f"{DEXSCREENER_API_URL}/latest/dex/search/?q={token_symbol}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                raise Exception(f"Request failed with status code {response.status_code}")
        except Exception as e:
            return f"Error searching for token pairs: {str(e)}"


# Example usage
if __name__ == "__main__":
    token_tool = GetTokenDataTool()
    data = token_tool.forward("solana", "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump")
    print(json.dumps(data, indent=2))
