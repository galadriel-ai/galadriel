"""
Solana Tools Module

This module provides tools for interacting with the Solana blockchain,
specifically for managing user token balances and portfolios.

Key Features:
- User balance tracking
- Portfolio management
- Token balance queries
- Multi-user support
"""

import asyncio
import logging
import os
from typing import Optional

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.core_agent import tool
from galadriel.tools.web3.wallet_tool import WalletTool

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000

if os.getenv("SOLANA_NETWORK") == "devnet":
    client = Client("https://api.devnet.solana.com")
else:
    client = Client("https://api.mainnet-beta.solana.com")


@tool
def get_user_balance(user_address: str, token: str) -> Optional[float]:
    """
    Retrieves the user's balance for a specific token from the blockchain.

    Args:
        user_address: The address of the user.
        token: The token address in solana.

    Returns:
        The balance of the user for the specified token, or None if the balance is not available.
    """
    return get_user_token_balance(user_address, token)


class GetAdminWalletAddressTool(WalletTool):
    name = "get_admin_wallet_address"
    description = "This tool returns the wallet address of the admin."
    inputs = {"dummy": {"type": "string", "description": "Dummy input"}}
    output_type = "string"

    # pylint:disable=W0221,W0613
    def forward(self, dummy: str) -> str:
        return self.wallet_repository.get_wallet_address()


def get_user_token_balance(user_address: str, token_address: Optional[str] = None) -> Optional[float]:
    """Query a user's token balance from the Solana blockchain.

    Fetches the current balance of either SOL or an SPL token for
    a given wallet address directly from the blockchain.

    Args:
        user_address (str): The user's Solana wallet address
        token_address (Optional[str]): The token's mint address, or None for SOL

    Returns:
        Optional[float]: The token balance, or None if the query fails

    Raises:
        Exception: If the balance query fails

    Note:
        - For SOL balance, uses RPC getBalance
        - For SPL tokens, uses Associated Token Account (ATA)
        - Handles token decimal conversion
        - Returns None if token account doesn't exist
    """
    try:
        user_pubkey = Pubkey.from_string(user_address)

        # Handle SOL balance query
        if not token_address:
            response_sol = client.get_balance(user_pubkey, commitment=Confirmed)
            return response_sol.value / LAMPORTS_PER_SOL

        # Handle SPL token balance query
        token_address = Pubkey.from_string(token_address)  # type: ignore
        spl_client = Token(client, token_address, TOKEN_PROGRAM_ID, user_pubkey)  # type: ignore

        # Verify token mint is initialized
        mint = spl_client.get_mint_info()
        if not mint.is_initialized:
            raise ValueError("Token mint is not initialized.")

        # Get balance from Associated Token Account
        wallet_ata = get_associated_token_address(user_pubkey, token_address)  # type: ignore
        response = client.get_token_account_balance(wallet_ata)
        if response.value is None:
            return None

        response_amount = response.value.ui_amount
        logger.info(f"Balance response: {response_amount}")

        return response_amount

    except Exception as error:
        raise Exception(f"Failed to get balance: {str(error)}") from error  # pylint: disable=W0719


if __name__ == "__main__":
    os.environ["SOLANA_NETWORK"] = "devnet"
    data = get_user_token_balance(
        "4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug",
        "ELJKW7qz3DA93K919agEk398kgeY1eGvs2u3GAfV3FLn",
    )
    print(data)
