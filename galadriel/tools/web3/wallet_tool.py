import os
from galadriel.core_agent import Tool
from galadriel.repository.wallet_repository import WalletRepository


class WalletTool(Tool):
    """
    Base class for web3 tools that require wallet access.
    """

    def __init__(self, *args, **kwargs):
        key_path = os.getenv("SOLANA_KEY_PATH")
        if not key_path:
            raise ValueError("SOLANA_KEY_PATH environment variable is not set")
        self.wallet_repository = WalletRepository(key_path)
        super().__init__(*args, **kwargs)
