import asyncio
import json
from typing import Dict, Optional

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # pylint: disable=E0401

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.core_agent import tool

LAMPORTS_PER_SOL = 1_000_000_000

Portfolio = Dict[str, float]

# Dictionary to store user balances
user_portfolios: Dict[str, Portfolio] = {}


@tool
def update_user_balance(user_address: str, token: str) -> str:
    """
    Updates the user's token balance storage from the blockchain.

    Args:
        user_address: The address of the user.
        token: The token address in solana.

    Returns:
        A message indicating success or failure.
    """
    if user_address not in user_portfolios:
        user_portfolios[user_address] = {}  # Initialize portfolio if user is new

    if token not in user_portfolios[user_address]:
        user_portfolios[user_address][token] = 0.0  # Initialize token balance if needed

    balance = asyncio.run(get_user_token_balance(user_address, token))
    user_portfolios[user_address][token] = balance  # type: ignore
    return "User balance updated successfully."


@tool
def get_all_users() -> str:  # Return type is now str
    """
    Returns a JSON string containing a list of user addresses
    who have deposited funds.

    Returns:
        A JSON string with user addresses.
    """
    users = list(user_portfolios.keys())
    return json.dumps(users)


@tool
def get_all_portfolios(dummy: dict) -> str:  # pylint: disable=W0613
    """
    Returns a JSON string containing the portfolios of all users.

    Args:
        dummy: A dummy argument to match the required function signature.

    Returns:
        A JSON string with all user's portfolio.
    """
    return json.dumps(user_portfolios)


@tool
async def get_user_balance(user_address: str, token: str) -> float:
    """
    Retrieves the user's balance for a specific token from the local portfolio storage.

    Args:
        user_address: The address of the user.
        token: The token address in solana.

    Returns:
        The user's balance for the specified token.
    """
    if user_address in user_portfolios:
        return user_portfolios[user_address].get(token, 0.0)  # Return 0 if token not found
    return 0.0


async def get_user_token_balance(self, user_address: str, token_address: Optional[str] = None) -> Optional[float]:
    """
    Get the token balance for a given wallet.

    Args:
        user_address (str): The user wallet address.
        token_address (Option[str]): The mint address of the token,
            if it is set to None, the balance of SOL is returned.

    Returns:
        float: The token balance.
    """
    try:
        user_pubkey = Pubkey.from_string(user_address)
        if not token_address:
            response = await self.async_client.get_balance(user_pubkey, commitment=Confirmed)
            return response.value / LAMPORTS_PER_SOL
        token_address = Pubkey.from_string(token_address)  # type: ignore
        spl_client = AsyncToken(self.async_client, token_address, TOKEN_PROGRAM_ID, user_pubkey)  # type: ignore

        mint = await spl_client.get_mint_info()
        if not mint.is_initialized:
            raise ValueError("Token mint is not initialized.")

        wallet_ata = get_associated_token_address(user_pubkey, token_address)  # type: ignore
        response = await self.async_client.get_token_account_balance(wallet_ata)
        if response.value is None:
            return None
        response = response.value.ui_amount
        print(f"Balance response: {response}")

        return float(response)

    except Exception as error:
        raise Exception(f"Failed to get balance: {str(error)}") from error  # pylint: disable=W0719
