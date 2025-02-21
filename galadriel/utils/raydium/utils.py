"""Common utility functions for Raydium protocol interactions."""

import json
import logging
import time
from typing import Optional

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401
from solders.signature import Signature  # type: ignore # pylint: disable=E0401
from spl.token.instructions import get_associated_token_address


logger = logging.getLogger(__name__)


def confirm_txn(client: Client, txn_sig: Signature, max_retries: int = 20, retry_interval: int = 3) -> bool:
    """Confirm a transaction."""
    retries = 0

    while retries < max_retries:
        try:
            txn_res = client.get_transaction(
                txn_sig,
                encoding="json",
                commitment=Confirmed,
                max_supported_transaction_version=0,
            )
            if txn_res.value and txn_res.value.transaction.meta:
                txn_json = json.loads(txn_res.value.transaction.meta.to_json())
            else:
                raise Exception("Transaction not found.")

            if txn_json["err"] is None:
                logger.info(f"Transaction confirmed... try count: {retries}")
                return True

            logger.error("Error: Transaction not confirmed. Retrying...")
            if txn_json["err"]:
                logger.error("Transaction failed.")
                return False
        except Exception:
            logger.info(f"Awaiting confirmation... try count: {retries}")
            retries += 1
            time.sleep(retry_interval)

    logger.error("Max retries reached. Transaction confirmation failed.")
    return False


def get_token_balance(client: Client, owner: Pubkey, token_mint: str) -> Optional[float]:
    """Get token balance for a wallet address."""
    try:
        token_pubkey = Pubkey.from_string(token_mint)
        token_account = get_associated_token_address(owner, token_pubkey)
        response = client.get_token_account_balance(token_account)

        if response.value is None:
            return None

        return response.value.ui_amount

    except Exception as e:
        logger.error(f"Error getting token balance: {e}")
        return None


def sol_for_tokens(
    sol_amount: float,
    base_vault_balance: float,
    quote_vault_balance: float,
    swap_fee: float = 0.25,
) -> float:
    """Calculate the amount of tokens received for a given amount of SOL."""
    effective_sol_used = sol_amount - (sol_amount * (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_base_vault_balance = constant_product / (quote_vault_balance + effective_sol_used)
    tokens_received = base_vault_balance - updated_base_vault_balance
    return round(tokens_received, 9)


def tokens_for_sol(
    token_amount: float,
    base_vault_balance: float,
    quote_vault_balance: float,
    swap_fee: float = 0.25,
) -> float:
    """Calculate the amount of SOL received for a given amount of tokens."""
    effective_tokens_sold = token_amount * (1 - (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_quote_vault_balance = constant_product / (base_vault_balance + effective_tokens_sold)
    sol_received = quote_vault_balance - updated_quote_vault_balance
    return round(sol_received, 9)
