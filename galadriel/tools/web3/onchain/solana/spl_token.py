"""
Solana SPL Token Tools Module

This module provides tools for interacting with SPL tokens on the Solana blockchain.

Key Features:
- Token balance tracking
- Multi-user support
- SPL token account management
"""

import logging
import os
from typing import Optional

from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from galadriel.tools.web3.onchain.solana.base_tool import SolanaBaseTool
from galadriel.wallets.solana_wallet import SolanaWallet

logger = logging.getLogger(__name__)


class GetTokenBalanceTool(SolanaBaseTool):
    """Tool for retrieving user SPL token balances.

    Fetches token balances from Associated Token Accounts (ATAs).
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

    def __init__(self, wallet: SolanaWallet, *args, **kwargs):
        super().__init__(wallet, *args, **kwargs)

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


class TransferTokenTool(SolanaBaseTool):
    """Tool for transferring SPL tokens between user"""

    name = "transfer_token"
    description = "Transfers SPL tokens between users."
    inputs = {
        "recipient_address": {
            "type": "string",
            "description": "The address of the recipient.",
        },
        "token_address": {
            "type": "string",
            "description": "The SPL token mint address.",
        },
        "amount": {
            "type": "number",
            "description": "Token transfer amount, expressed in whole token units (accounting for token decimals).",
        },
    }
    output_type = "string"

    def __init__(self, wallet: SolanaWallet, *args, **kwargs):
        super().__init__(wallet, *args, **kwargs)

    def forward(self, recipient_address: str, token_address: str, amount: float) -> str:
        """Transfer SPL tokens between user addresses.

        Args:
            recipient_address (str): The recipient's Solana wallet address
            token_address (str): The token's mint address
            amount (float): Token transfer amount, expressed in whole token units (accounting for token decimals)

        Returns:
            str: The transaction signature if successful, error message if failed
        """
        try:
            keypair = self.wallet.get_wallet()
            sender_pubkey = Pubkey.from_string(self.wallet.get_address())
            recipient_pubkey = Pubkey.from_string(recipient_address)
            token_pubkey = Pubkey.from_string(token_address)

            # Initialize SPL token client
            spl_client = Token(conn=self.client, pubkey=token_pubkey, program_id=TOKEN_PROGRAM_ID, payer=keypair)

            # Verify token mint is initialized
            mint = spl_client.get_mint_info()
            if not mint.is_initialized:
                raise ValueError("Token mint is not initialized.")

            # Get sender's Associated Token Account
            sender_ata = get_associated_token_address(sender_pubkey, token_pubkey)

            sender_token_balance = self.client.get_token_account_balance(sender_ata)

            # Verify sender has sufficient balance
            sender_ui_amount = sender_token_balance.value.ui_amount
            if sender_ui_amount is not None and sender_ui_amount < amount:
                raise ValueError("Insufficient balance to transfer tokens.")

            # Calculate amount in UI format
            decimals = mint.decimals
            amount = int(amount * 10**decimals)  # Convert to UI format based on token decimals

            # Transfer tokens
            response = spl_client.transfer(sender_ata, recipient_pubkey, sender_pubkey, amount)

            logger.info(f"Token transfer response: {response}")

            if response is None:
                return "Transaction failed. No response received."

            logger.info(f"Token transfer response: {response}")
            return f"Transaction succeeded with signature: {response}"

        except Exception as error:
            logger.error(f"Failed to transfer tokens: {str(error)}")
            return f"Transaction failed with error: {str(error)}"


if __name__ == "__main__":
    wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))
    get_balance_tool = GetTokenBalanceTool(wallet)  # type: ignore
    data = get_balance_tool.forward(
        "4kbGbZtfkfkRVGunkbKX4M7dGPm9MghJZodjbnRZbmug",
        "J1Wpmugrooj1yMyQKrdZ2vwRXG5rhfx3vTnYE39gpump",
    )
    print(data)

    transfer_tool = TransferTokenTool(wallet)  # type: ignore
    transfer_res = transfer_tool.forward(
        "J7DYsxt2mGt3XGpk8rAwcc5qfjPP14FgmiAsEeAsMEMY",
        "J1Wpmugrooj1yMyQKrdZ2vwRXG5rhfx3vTnYE39gpump",
        0.1,
    )
    print(transfer_res)
