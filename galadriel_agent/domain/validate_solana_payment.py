from typing import List
from typing import Optional

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.signature import Signature

from galadriel_agent.entities import Pricing


def execute(pricing: Pricing, tx_signature: str) -> bool:
    http_client = Client("https://api.mainnet-beta.solana.com")
    tx_sig = Signature.from_string(tx_signature)
    tx_info = http_client.get_transaction(
        tx_sig=tx_sig, max_supported_transaction_version=10
    )
    if not tx_info.value:
        return False
    transaction = tx_info.value.transaction.transaction  # The actual transaction
    account_keys = transaction.message.account_keys
    index = _get_key_index(account_keys, pricing.wallet_address)
    if index < 0:
        return False

    meta = tx_info.value.transaction.meta
    if meta.err is not None:
        return False

    pre_balance = meta.pre_balances[index]
    post_balance = meta.post_balances[index]
    amount_sent = post_balance - pre_balance
    if amount_sent >= pricing.cost * 10**9:
        return True
    return False


def _get_key_index(account_keys: List[Pubkey], wallet_address: str) -> int:
    """
    Returns the index of the wallet address
    :param account_keys:
    :param wallet_address:
    :return: non-zero number if present, -1 otherwise
    """
    wallet_key = Pubkey.from_string(wallet_address)
    for i, key in enumerate(account_keys):
        if wallet_key == key:
            return i
    return -1
