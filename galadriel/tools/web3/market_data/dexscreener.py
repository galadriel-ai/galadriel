import json
import requests
from typing import Dict, Any

from galadriel.core_agent import Tool


class GetTokenDataTool(Tool):
    """Tool for fetching detailed token data from DexScreener.

    Retrieves and formats token data from DexScreener API, removing unnecessary
    information to fit context limits.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "get_token_data"
    description = "Fetch detailed data for a specific token from DexScreener"
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
            response = requests.get(f"https://api.dexscreener.com/tokens/v1/{ecosystem}/{token_address}", timeout=30)
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


# Example usage
if __name__ == "__main__":
    token_tool = GetTokenDataTool()
    data = token_tool.forward("solana", "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump")
    print(json.dumps(data, indent=2))
