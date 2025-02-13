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
import json
from typing import Dict, Optional

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # pylint: disable=E0401

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.core_agent import tool

# Constants
LAMPORTS_PER_SOL = 1_000_000_000  # Number of lamports in 1 SOL

# Type Aliases
Portfolio = Dict[str, float]  # Maps token addresses to balances

# Global state
user_portfolios: Dict[str, Portfolio] = {}  # Maps user addresses to their portfolios


@tool
def update_user_balance(user_address: str, token: str) -> str:
    """Update a user's token balance in the local storage.

    Fetches the current balance from the blockchain and updates the local
    portfolio storage for the specified user and token.

    Args:
        user_address (str): The Solana address of the user
        token (str): The token's mint address

    Returns:
        str: Success message

    Note:
        - Creates new portfolio entry if user doesn't exist
        - Initializes token balance to 0 if not present
        - Uses asyncio to handle blockchain queries
    """
    if user_address not in user_portfolios:
        user_portfolios[user_address] = {}  # Initialize portfolio if user is new

    if token not in user_portfolios[user_address]:
        user_portfolios[user_address][token] = 0.0  # Initialize token balance if needed

    balance = asyncio.run(get_user_token_balance(user_address, token))
    user_portfolios[user_address][token] = balance  # type: ignore
    return "User balance updated successfully."


@tool
def get_all_users() -> str:
    """Retrieve a list of all users with portfolios.

    Returns a JSON string containing addresses of all users who have
    deposited funds or had their balances tracked.

    Returns:
        str: JSON string containing list of user addresses

    Note:
        Returns an empty list if no users are tracked
    """
    users = list(user_portfolios.keys())
    return json.dumps(users)


@tool
def get_all_portfolios(dummy: dict) -> str:  # pylint: disable=W0613
    """Retrieve all user portfolios.

    Returns a JSON string containing the complete portfolio data
    for all tracked users.

    Args:
        dummy (dict): Unused parameter required by tool decorator

    Returns:
        str: JSON string containing all user portfolios

    Note:
        Format: {user_address: {token_address: balance}}
    """
    return json.dumps(user_portfolios)


@tool
async def get_user_balance(user_address: str, token: str) -> float:
    """Get a user's token balance from local storage.

    Retrieves the stored balance for a specific token from the user's
    portfolio, without querying the blockchain.

    Args:
        user_address (str): The Solana address of the user
        token (str): The token's mint address

    Returns:
        float: The stored token balance, or 0.0 if not found

    Note:
        Returns 0.0 if either the user or token is not found
    """
    if user_address in user_portfolios:
        return user_portfolios[user_address].get(token, 0.0)  # Return 0 if token not found
    return 0.0


async def get_user_token_balance(self, user_address: str, token_address: Optional[str] = None) -> Optional[float]:
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
            response = await self.async_client.get_balance(user_pubkey, commitment=Confirmed)
            return response.value / LAMPORTS_PER_SOL

        # Handle SPL token balance query
        token_address = Pubkey.from_string(token_address)  # type: ignore
        spl_client = AsyncToken(self.async_client, token_address, TOKEN_PROGRAM_ID, user_pubkey)  # type: ignore

        # Verify token mint is initialized
        mint = await spl_client.get_mint_info()
        if not mint.is_initialized:
            raise ValueError("Token mint is not initialized.")

        # Get balance from Associated Token Account
        wallet_ata = get_associated_token_address(user_pubkey, token_address)  # type: ignore
        response = await self.async_client.get_token_account_balance(wallet_ata)
        if response.value is None:
            return None

        response = response.value.ui_amount
        print(f"Balance response: {response}")

        return float(response)

    except Exception as error:
        raise Exception(f"Failed to get balance: {str(error)}") from error  # pylint: disable=W0719
