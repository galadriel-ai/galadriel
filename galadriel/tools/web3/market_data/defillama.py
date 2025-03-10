import json

import requests

from galadriel.tools import Tool


class GetProtocolTVLTool(Tool):
    """Tool for retrieving Total Value Locked (TVL) data for DeFi protocols.

    Fetches current TVL data for a specified protocol using the DeFi Llama API.
    """

    name = "defillama_get_protocol_tvl"
    description = "Get Total Value Locked (TVL) for a given DeFi protocol using DeFi Llama API"
    inputs = {
        "protocol_name": {
            "type": "string",
            "description": "The name of the protocol to get TVL for (e.g., 'uniswap', 'aave')",
        }
    }
    output_type = "string"

    def forward(self, protocol_name: str) -> str:  # pylint: disable=W0221
        """Fetch current TVL data for a DeFi protocol.

        Args:
            protocol_name (str): The name of the protocol (e.g., 'uniswap')

        Returns:
            str: JSON string containing TVL data. Returns "Protocol not found" if the token doesn't exist

        Note:
            Returns data including:
            - Current TVL in USD
            - Timestamp of the data
        """
        response = requests.get(f"https://api.llama.fi/tvl/{protocol_name}")
        return json.dumps(response.json())
