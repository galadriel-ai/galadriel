from typing import List

from smolagents import tool
from solders.pubkey import Pubkey
from solders.signature import Signature

PRICE = 10**7


@tool
def solana_payment_tool(signature: str, wallet_address: str) -> bool:
    """
    This is a tool that returns if a certain payment has been made to a certain wallet
    The output is a boolean if payment has been made or not.
    Args:
        signature: The tx signature
        wallet_address: The wallet address of the receiver
    """
    from solana.rpc.api import Client

    http_client = Client("https://api.mainnet-beta.solana.com")
    tx_sig = Signature.from_string(signature)
    tx_info = http_client.get_transaction(
        tx_sig=tx_sig, max_supported_transaction_version=10
    )
    if not tx_info.value:
        return False
    transaction = tx_info.value.transaction.transaction  # The actual transaction
    account_keys = transaction.message.account_keys
    index = _get_key_index(account_keys, wallet_address)
    if index < 0:
        return False

    meta = tx_info.value.transaction.meta
    if meta.err is not None:
        return False

    pre_balance = meta.pre_balances[index]
    post_balance = meta.post_balances[index]
    amount_sent = post_balance - pre_balance
    if amount_sent >= PRICE:
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


if __name__ == "__main__":
    _signature = "5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"
    _wallet_address = "5RYHzQuknP2viQjYzP27wXVWKeaxonZgMBPQA86GV92t"
    print(solana_payment_tool(_signature, _wallet_address))
