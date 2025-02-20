"""
Solana Native SOL Tools Module

This module provides tools for interacting with native SOL on the Solana blockchain.

Key Features:
- SOL balance tracking
- Multi-user support
"""

import logging
from typing import Optional

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

from galadriel.tools.web3.onchain.solana.base_tool import SolanaBaseTool
from galadriel.wallets.solana_wallet import SolanaWallet

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000


class GetSOLBalanceTool(SolanaBaseTool):
    """Tool for retrieving user SOL balances.

    Fetches native SOL balance for any Solana wallet address.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "get_user_sol_balance"
    description = "Retrieves the user's SOL balance from the blockchain."
    inputs = {
        "user_address": {
            "type": "string",
            "description": "The address of the user.",
        },
    }
    output_type = "number"

    def __init__(self, wallet: SolanaWallet, *args, **kwargs):
        super().__init__(wallet, *args, **kwargs)

    def forward(self, user_address: str) -> Optional[float]:
        """Get SOL balance for a wallet address.

        Args:
            user_address (str): The user's Solana wallet address

        Returns:
            Optional[float]: The SOL balance if successful, None if error
        """
        try:
            user_pubkey = Pubkey.from_string(user_address)
            response = self.client.get_balance(user_pubkey, commitment=Confirmed)
            return response.value / LAMPORTS_PER_SOL
        except Exception as error:
            logger.error(f"Failed to get SOL balance: {str(error)}")
            return None


if __name__ == "__main__":
    wallet = SolanaWallet(key_path="/path/to/keypair.json")
    get_balance_tool = GetSOLBalanceTool(wallet)
    data = get_balance_tool.forward("4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug")
    print(data)
