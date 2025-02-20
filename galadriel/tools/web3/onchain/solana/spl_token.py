"""
Solana SPL Token Tools Module

This module provides tools for interacting with SPL tokens on the Solana blockchain.

Key Features:
- Token balance tracking
- Multi-user support
- SPL token account management
"""

import logging
from typing import Optional

from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.tools.web3.onchain.solana.base_tool import SolanaBaseTool

logger = logging.getLogger(__name__)


class GetTokenBalanceTool(SolanaBaseTool):
    """Tool for retrieving user SPL token balances.

    Fetches token balances from Associated Token Accounts (ATAs).

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "get_user_token_balance"
    description = "Retrieves the user's SPL token balance from the blockchain."
    inputs = {
        "user_address": {
            "type": "string",
            "description": "The address of the user.",
        },
        "token_address": {
            "type": "string",
            "description": "The SPL token mint address.",
        },
    }
    output_type = "number"

    def __init__(self, *args, **kwargs):
        super().__init__(wallet_manager=None, is_async_client=False, *args, **kwargs)

    def forward(self, user_address: str, token_address: str) -> Optional[float]:
        """Get SPL token balance for a wallet address.

        Args:
            user_address (str): The user's Solana wallet address
            token_address (str): The token's mint address

        Returns:
            Optional[float]: The token balance if successful, None if error
        """
        try:
            user_pubkey = Pubkey.from_string(user_address)
            token_pubkey = Pubkey.from_string(token_address)

            # Initialize SPL token client
            spl_client = Token(self.client, token_pubkey, TOKEN_PROGRAM_ID, user_pubkey)  # type: ignore

            # Verify token mint is initialized
            mint = spl_client.get_mint_info()
            if not mint.is_initialized:
                raise ValueError("Token mint is not initialized.")

            # Get balance from Associated Token Account
            wallet_ata = get_associated_token_address(user_pubkey, token_pubkey)
            response = self.client.get_token_account_balance(wallet_ata)
            if response.value is None:
                return None

            response_amount = response.value.ui_amount
            logger.info(f"Balance response: {response_amount}")
            return response_amount

        except Exception as error:
            logger.error(f"Failed to get token balance: {str(error)}")
            return None


if __name__ == "__main__":
    get_balance_tool = GetTokenBalanceTool()
    data = get_balance_tool.forward(
        "4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug",
        "J1Wpmugrooj1yMyQKrdZ2vwRXG5rhfx3vTnYE39gpump",
    )
    print(data)
