import json
import os
from typing import Optional

from solders import message
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore


class WalletRepository:
    def __init__(self, key_path: str):
        keypair = _get_private_key(key_path=key_path)
        if keypair is None:
            raise Exception("No admin key found")
        self.wallet = keypair

    def get_wallet_address(self) -> str:
        """
        Get the wallet address.

        Returns:
            str: The wallet address.
        """
        return str(self.wallet.pubkey())

    def get_wallet(self) -> Keypair:
        """
        Get the wallet keypair.

        Returns:
            Keypair: The wallet keypair.
        """
        return self.wallet


def _get_private_key(key_path: str) -> Optional[Keypair]:
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as file:
            seed = json.load(file)
            return Keypair.from_bytes(seed)
    return None
