import asyncio
import base64
import json
import os
from typing import Dict

from galadriel.core_agent import tool
from galadriel.repository.wallet_repository import WalletRepository

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TxOpts
from solders import message
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID

from jupiter_python_sdk.jupiter import Jupiter

from galadriel.tools.web3.wallet_tool import WalletTool


SOLANA_API_URL = "https://api.mainnet-beta.solana.com"

JUPITER_QUOTE_API_URL = "https://quote-api.jup.ag/v6/quote?"
JUPITER_SWAP_API_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_OPEN_ORDER_API_URL = "https://jup.ag/api/limit/v1/createOrder"
JUPITER_CANCEL_ORDERS_API_URL = "https://jup.ag/api/limit/v1/cancelOrders"
JUPITER_QUERY_OPEN_ORDERS_API_URL = "https://jup.ag/api/limit/v1/openOrders?wallet="
JUPITER_QUERY_ORDER_HISTORY_API_URL = "https://jup.ag/api/limit/v1/orderHistory"
JUPITER_QUERY_TRADE_HISTORY_API_URL = "https://jup.ag/api/limit/v1/tradeHistory"


class SwapTokenTool(WalletTool):
    name = "swap_token"
    description = "Swaps one token for another in the user's portfolio."
    inputs = {
        "user_address": {
            "type": "string",
            "description": "The solana address of the user",
        },
        "token1": {"type": "string", "description": "The address of the token to sell"},
        "token2": {"type": "string", "description": "The address of the token to buy"},
        "amount": {"type": "number", "description": "The amount of token1 to swap"},
    }
    output_type = "string"

    def forward(
        self, user_address: str, token1: str, token2: str, amount: float
    ) -> str:
        wallet = self.wallet_repository.get_wallet()

        result = asyncio.run(swap(wallet, user_address, token1, token2, amount))

        return f"Successfully swapped {amount} {token1} for {token2}, tx sig: {result}."


async def swap(
    wallet: Keypair,
    output_mint: str,
    input_mint: str,
    input_amount: float,
    slippage_bps: int = 300,
) -> str:
    """
    Swap tokens using Jupiter Exchange.

    Args:
        wallet(Keypair): The signer wallet.
        output_mint (Pubkey): Target token mint address.
        input_mint (Pubkey): Source token mint address (default: USDC).
        input_amount (float): Amount to swap (in number of tokens).
        slippage_bps (int): Slippage tolerance in basis points (default: 300 = 3%).

    Returns:
        str: Transaction signature.

    Raises:
        Exception: If the swap fails.
    """
    async_client = AsyncClient(SOLANA_API_URL)
    jupiter = Jupiter(
        async_client=async_client,
        keypair=wallet,
        quote_api_url=JUPITER_QUOTE_API_URL,
        swap_api_url=JUPITER_SWAP_API_URL,
        open_order_api_url=JUPITER_OPEN_ORDER_API_URL,
        cancel_orders_api_url=JUPITER_CANCEL_ORDERS_API_URL,
        query_open_orders_api_url=JUPITER_QUERY_OPEN_ORDERS_API_URL,
        query_order_history_api_url=JUPITER_QUERY_ORDER_HISTORY_API_URL,
        query_trade_history_api_url=JUPITER_QUERY_TRADE_HISTORY_API_URL,
    )
    input_mint = str(input_mint)
    output_mint = str(output_mint)
    spl_client = AsyncToken(
        async_client, Pubkey.from_string(input_mint), TOKEN_PROGRAM_ID, wallet
    )
    mint = await spl_client.get_mint_info()
    decimals = mint.decimals
    input_amount = int(input_amount * 10**decimals)

    try:
        transaction_data = await jupiter.swap(
            input_mint,
            output_mint,
            input_amount,
            only_direct_routes=False,
            slippage_bps=slippage_bps,
        )
        raw_transaction = VersionedTransaction.from_bytes(
            base64.b64decode(transaction_data)
        )
        signature = wallet.sign_message(
            message.to_bytes_versioned(raw_transaction.message)
        )
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await async_client.send_raw_transaction(
            txn=bytes(signed_txn), opts=opts
        )
        print(f"Transaction sent: {json.loads(result.to_json())}")
        transaction_id = json.loads(result.to_json())["result"]
        print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")
        await async_client.confirm_transaction(signature, commitment=Confirmed)
        print(f"Transaction confirmed: https://explorer.solana.com/tx/{transaction_id}")
        return str(signature)

    except Exception as e:
        raise Exception(f"Swap failed: {str(e)}")
