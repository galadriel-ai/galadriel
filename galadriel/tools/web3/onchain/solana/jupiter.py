import base64
import json
import os

from solana.rpc.api import Client
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TxOpts
from solders import message
from solders.keypair import Keypair  # pylint: disable=E0401 # type: ignore
from solders.pubkey import Pubkey  # pylint: disable=E0401 # type: ignore
from solders.transaction import VersionedTransaction  # pylint: disable=E0401 # type: ignore

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID

from jupiter_python_sync_sdk.jupiter import Jupiter

from galadriel.tools.web3.onchain.solana.base_tool import Network, SolanaBaseTool
from galadriel.wallets.solana_wallet import SolanaWallet


# API endpoints for Jupiter Protocol
SOLANA_API_URL = "https://api.mainnet-beta.solana.com"
JUPITER_QUOTE_API_URL = "https://quote-api.jup.ag/v6/quote?"
JUPITER_SWAP_API_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_OPEN_ORDER_API_URL = "https://jup.ag/api/limit/v1/createOrder"
JUPITER_CANCEL_ORDERS_API_URL = "https://jup.ag/api/limit/v1/cancelOrders"
JUPITER_QUERY_OPEN_ORDERS_API_URL = "https://jup.ag/api/limit/v1/openOrders?wallet="
JUPITER_QUERY_ORDER_HISTORY_API_URL = "https://jup.ag/api/limit/v1/orderHistory"
JUPITER_QUERY_TRADE_HISTORY_API_URL = "https://jup.ag/api/limit/v1/tradeHistory"


class SwapTokenTool(SolanaBaseTool):
    """Tool for performing token swaps using Jupiter Protocol on Solana.

    This tool enables token swaps between any two SPL tokens using Jupiter's
    aggregator for optimal routing and pricing.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "jupiter_swap_token"
    description = "Swaps one token for another on Jupiter Swap. It also supports Meteora, Fluxbeam, 1Intro, Pump.Fun, Raydium and Whirlpools."
    inputs = {
        "token1": {"type": "string", "description": "The address of the token to sell"},
        "token2": {"type": "string", "description": "The address of the token to buy"},
        "amount": {"type": "number", "description": "The amount of token1 to swap"},
        "slippage_bps": {
            "type": "number",
            "description": "Slippage tolerance in basis points. Defaults to 300 (3%)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, wallet: SolanaWallet, *args, **kwargs):
        super().__init__(wallet=wallet, is_async_client=False, *args, **kwargs)  # type: ignore
        if self.network is not Network.MAINNET:
            raise NotImplementedError("Jupiter tool is not available on devnet")

    def forward(self, token1: str, token2: str, amount: float, slippage_bps: int = 300) -> str:
        """Execute a token swap transaction.

        Args:
            token1 (str): The address of the token to sell
            token2 (str): The address of the token to buy
            amount (float): The amount of token1 to swap
            slippage_bps (int): Slippage tolerance in basis points. Defaults to 300 (3%)

        Returns:
            str: A success message containing the transaction signature
        """
        wallet = self.wallet.get_wallet()

        result = swap(
            client=self.client,
            wallet=wallet,
            input_mint=token1,
            output_mint=token2,
            input_amount=amount,
            slippage_bps=slippage_bps,
        )

        return f"Successfully swapped {amount} {token1} for {token2}, tx sig: {result}."


# pylint: disable=R0914
def swap(
    client: Client,
    wallet: Keypair,
    input_mint: str,
    output_mint: str,
    input_amount: float,
    slippage_bps: int = 300,
) -> str:
    """Execute a token swap using Jupiter Protocol.

    Performs a swap between two tokens using Jupiter's aggregator for optimal
    routing and pricing. Handles transaction construction, signing, and confirmation.

    Args:
        client (Client): The Solana RPC client
        wallet (Keypair): The signer wallet for the transaction
        input_mint (str): Source token mint address
        output_mint (str): Target token mint address
        input_amount (float): Amount of input token to swap
        slippage_bps (int, optional): Slippage tolerance in basis points. Defaults to 300 (3%)

    Returns:
        str: The transaction signature

    Raises:
        Exception: If the swap fails for any reason

    Note:
        - Connects to Solana mainnet via RPC
        - Uses Jupiter's quote API for price discovery
        - Handles token decimal conversion
        - Confirms transaction completion
        - Prints transaction URLs for monitoring
    """
    jupiter = Jupiter(
        client=client,
        keypair=wallet,
        quote_api_url=JUPITER_QUOTE_API_URL,
        swap_api_url=JUPITER_SWAP_API_URL,
        open_order_api_url=JUPITER_OPEN_ORDER_API_URL,
        cancel_orders_api_url=JUPITER_CANCEL_ORDERS_API_URL,
        query_open_orders_api_url=JUPITER_QUERY_OPEN_ORDERS_API_URL,
        query_order_history_api_url=JUPITER_QUERY_ORDER_HISTORY_API_URL,
        query_trade_history_api_url=JUPITER_QUERY_TRADE_HISTORY_API_URL,
    )

    # Convert addresses to strings
    input_mint = str(input_mint)
    output_mint = str(output_mint)

    # Get token decimals and adjust amount
    spl_client = Token(client, Pubkey.from_string(input_mint), TOKEN_PROGRAM_ID, wallet)
    mint = spl_client.get_mint_info()
    decimals = mint.decimals
    input_amount = int(input_amount * 10**decimals)

    try:
        # Get swap transaction data
        transaction_data = jupiter.swap(
            input_mint,
            output_mint,
            input_amount,
            only_direct_routes=False,
            slippage_bps=slippage_bps,
        )

        # Construct and sign transaction
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = wallet.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])

        # Send and confirm transaction
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        print(f"Transaction sent: {json.loads(result.to_json())}")
        transaction_id = json.loads(result.to_json())["result"]
        print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")
        client.confirm_transaction(signature, commitment=Confirmed)
        print(f"Transaction confirmed: https://explorer.solana.com/tx/{transaction_id}")
        return str(signature)

    except Exception as e:
        raise Exception(f"Swap failed: {str(e)}")  # pylint: disable=W0719


if __name__ == "__main__":
    wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))  # type: ignore
    swap_tool = SwapTokenTool(wallet)
    print(
        swap_tool.forward(
            "So11111111111111111111111111111111111111112",
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            0.0001,
            300,
        )
    )
