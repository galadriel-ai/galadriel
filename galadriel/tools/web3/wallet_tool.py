import os
from galadriel.core_agent import Tool
from galadriel.repository.wallet_repository import WalletRepository


class WalletTool(Tool):
    """
    Base class for web3 tools that require wallet access.
    """

    def __init__(self, *args, **kwargs):
        self.wallet_repository = WalletRepository(os.getenv("SOLANA_KEY_PATH"))
        super().__init__(*args, **kwargs)
