import json
import os
from typing import Optional

from construct import Enum
from solders.keypair import Keypair  # type: ignore # pylint: disable=E0401


class KeyType(Enum):
    """
    Enumeration of the key types.
    """
    SOLANA = "solana"
    ETHEREUM = "ethereum"


class WalletManager:
    def __init__(self, key_type: KeyType, key_path: str):

        if key_type != KeyType.SOLANA:
            raise ValueError("Unsupported key type. Only Solana keys are supported currently.")

        keypair = _get_private_key(key_path=key_path)
        if keypair is None:
            raise ValueError("No admin key found")
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
