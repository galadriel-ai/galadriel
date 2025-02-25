import json
import os
from typing import Optional

from solders.keypair import Keypair  # type: ignore

from galadriel.cli import DEFAULT_SOLANA_KEY_PATH
from galadriel.wallets.wallet_base import WalletBase  # type: ignore # pylint: disable=E0401


class SolanaWallet(WalletBase):
    def __init__(self, key_path: Optional[str]):
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


def _get_private_key(key_path: Optional[str]) -> Optional[Keypair]:
    if key_path == "":
        raise ValueError("Key path cannot be an empty string")

    if key_path is None:
        default_path = os.path.expanduser(DEFAULT_SOLANA_KEY_PATH)
        if not os.path.exists(default_path):
            raise ValueError(f"No key path provided and default key missing at: {default_path}")
        key_path = default_path
    else:
        key_path = os.path.expanduser(key_path)

    if not os.path.exists(key_path):
        raise ValueError(f"Key file not found at: {key_path}")

    if os.path.getsize(key_path) == 0:
        raise ValueError(f"Key file is empty: {key_path}")

    try:
        with open(key_path, "r", encoding="utf-8") as file:
            try:
                seed = json.load(file)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format in key file: {key_path}")

            try:
                return Keypair.from_bytes(seed)
            except Exception as e:
                raise ValueError(f"Invalid key format in file: {key_path}. Error: {str(e)}")
    except IOError as e:
        raise ValueError(f"Error reading key file {key_path}: {str(e)}")
