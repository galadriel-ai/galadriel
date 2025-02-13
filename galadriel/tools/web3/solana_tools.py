import asyncio
import logging
from typing import Optional

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.core_agent import tool
from galadriel.tools.web3.wallet_tool import WalletTool

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000


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
    return asyncio.run(get_user_token_balance(user_address, token))


class GetAdminWalletAddressTool(WalletTool):
    name = "get_admin_wallet_address"
    description = "This tool returns the wallet address of the admin."
    inputs = {"dummy": {"type": "string", "description": "Dummy input"}}
    output_type = "string"

    # pylint:disable=W0221,W0613
    def forward(self, dummy: str) -> str:
        return self.wallet_repository.get_wallet_address()


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
        logger.info(f"Balance response: {response}")

        return float(response)

    except Exception as error:
        raise Exception(f"Failed to get balance: {str(error)}") from error  # pylint: disable=W0719
