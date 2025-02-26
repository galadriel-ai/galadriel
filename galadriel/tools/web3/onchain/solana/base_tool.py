"""Base class for Solana tools."""

from abc import ABC
from enum import Enum
import os

from solana.rpc.api import Client
from galadriel.tools import Tool
from galadriel.wallets.solana_wallet import SolanaWallet


class Network(Enum):
    """Enumeration of the supported Solana networks."""

    MAINNET = "mainnet"
    DEVNET = "devnet"


class SolanaBaseTool(Tool, ABC):
    """Base class for Solana tools that require wallet access and onchain operation.

    This class provides common wallet functionality for tools that need
    to interact with the Solana blockchain using a wallet. It handles
    wallet initialization and provides access to the wallet manager.

    Attributes:
        wallet_manager (WalletManager): Manager for handling wallet operations
        network (Network): The Solana network being used (mainnet or devnet)
        client (Client): The Solana RPC client for network interactions

    Example:
        class MySolanaTool(SolanaBaseTool):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Additional initialization here

            def forward(self, ...):
                wallet = self.wallet_manager.get_wallet()
                # Use wallet for transactions
    """

    def __init__(self, wallet: SolanaWallet, *args, **kwargs):
        """Initialize the Solana tool.

        Args:
            wallet_manager (WalletManager): The wallet manager instance for handling wallet operations
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class
        """
        self.wallet = wallet

        # Set the network and client based on the environment variable, default to mainnet
        if os.getenv("SOLANA_NETWORK") == "devnet":
            self.network = Network.DEVNET
            self.client = Client("https://api.devnet.solana.com")
        else:
            self.network = Network.MAINNET
            self.client = Client("https://api.mainnet-beta.solana.com")

        # Initialize parent Tool class
        super().__init__(*args, **kwargs)
