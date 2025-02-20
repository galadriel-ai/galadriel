import json
import os
from typing import Optional

from solders.keypair import Keypair  # type: ignore

from galadriel.wallets.wallet_base import WalletBase  # type: ignore # pylint: disable=E0401


class SolanaWallet(WalletBase):
    def __init__(self, key_path: str):
        keypair = _get_private_key(key_path=key_path)
        if keypair is None:
            raise ValueError("No key found")
        self.keypair = keypair

    def get_address(self) -> str:
        """
        Get the wallet address.

        Returns:
            str: The wallet address.
        """
        return str(self.keypair.pubkey())

    def get_wallet(self) -> Keypair:
        """
        Get the wallet keypair.

        Returns:
            Keypair: The wallet keypair.
        """
        return self.keypair


def _get_private_key(key_path: str) -> Optional[Keypair]:
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as file:
            seed = json.load(file)
            return Keypair.from_bytes(seed)
    return None
