import os
from galadriel.keystore.wallet_manager import KeyType, WalletManager

# Initialize wallet manager
key_path = os.getenv("SOLANA_KEY_PATH")
if not key_path:
    raise ValueError("SOLANA_KEY_PATH environment variable is not set")
wallet_manager = WalletManager(KeyType.SOLANA, key_path)

# Prepare a Web3 specific toolkit, relevant for the trading agent
tools = [
    market_data_devnet.fetch_market_data,
    raydium_cpmm.BuyTokenWithSolTool(wallet_manager=wallet_manager),
    solana_common.GetAdminWalletAddressTool(),
    solana_common.GetUserBalanceTool(),
]
