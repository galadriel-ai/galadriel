import os
from galadriel.core_agent import Tool
from galadriel.repository.wallet_repository import WalletRepository


class WalletTool(Tool):
    """Base class for web3 tools that require wallet access.

    This class provides common wallet functionality for tools that need
    to interact with the Solana blockchain using a wallet. It handles
    wallet initialization and provides access to the wallet repository.

    Attributes:
        wallet_repository (WalletRepository): Repository for managing wallet access

    Example:
        class MyWeb3Tool(WalletTool):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Additional initialization here

            def forward(self, ...):
                wallet = self.wallet_repository.get_wallet()
                # Use wallet for transactions
    """

    def __init__(self, *args, **kwargs):
        """Initialize the wallet tool.

        Sets up the wallet repository using the keypair file specified
        in environment variables.

        Args:
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class

        Raises:
            ValueError: If SOLANA_KEY_PATH environment variable is not set

        Note:
            The keypair file should be kept secure and never committed to
            version control.
        """
        key_path = os.getenv("SOLANA_KEY_PATH")
        if not key_path:
            raise ValueError("SOLANA_KEY_PATH environment variable is not set")

        # Initialize wallet repository with keypair file
        self.wallet_repository = WalletRepository(key_path)

        # Initialize parent Tool class
        super().__init__(*args, **kwargs)
