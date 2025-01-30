import base64
import json
from typing import Optional
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TxOpts

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID

from solders import message
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore


from jupiter_python_sdk.jupiter import Jupiter

SOLANA_API_URL = "https://api.mainnet-beta.solana.com"
JUPITER_QUOTE_API_URL = "https://quote-api.jup.ag/v6/quote?"
JUPITER_SWAP_API_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_OPEN_ORDER_API_URL = "https://jup.ag/api/limit/v1/createOrder"
JUPITER_CANCEL_ORDERS_API_URL = "https://jup.ag/api/limit/v1/cancelOrders"
JUPITER_QUERY_OPEN_ORDERS_API_URL = "https://jup.ag/api/limit/v1/openOrders?wallet="
JUPITER_QUERY_ORDER_HISTORY_API_URL = "https://jup.ag/api/limit/v1/orderHistory"
JUPITER_QUERY_TRADE_HISTORY_API_URL = "https://jup.ag/api/limit/v1/tradeHistory"

LAMPORTS_PER_SOL = 1_000_000_000


class SolanaRepository:
    def __init__(self):
        self.async_client = AsyncClient(SOLANA_API_URL)
        # TODO: Replace with actual wallet
        self.wallet = Keypair()
        self.jupiter = Jupiter(
            async_client=self.async_client,
            keypair=self.wallet,
            quote_api_url=JUPITER_QUOTE_API_URL,
            swap_api_url=JUPITER_SWAP_API_URL,
            open_order_api_url=JUPITER_OPEN_ORDER_API_URL,
            cancel_orders_api_url=JUPITER_CANCEL_ORDERS_API_URL,
            query_open_orders_api_url=JUPITER_QUERY_OPEN_ORDERS_API_URL,
            query_order_history_api_url=JUPITER_QUERY_ORDER_HISTORY_API_URL,
            query_trade_history_api_url=JUPITER_QUERY_TRADE_HISTORY_API_URL,
        )

    def get_wallet_address(self) -> str:
        """
        Get the wallet address.

        Returns:
            str: The wallet address.
        """
        return str(self.wallet.pubkey())

    async def swap(
        self,
        wallet: Keypair,
        output_mint: str,
        input_mint: str,
        input_amount: float,
        slippage_bps: int = 300,
    ) -> str:
        """
        Swap tokens using Jupiter Exchange.

        Args:
            output_mint (Pubkey): Target token mint address.
            input_mint (Pubkey): Source token mint address (default: USDC).
            input_amount (float): Amount to swap (in number of tokens).
            slippage_bps (int): Slippage tolerance in basis points (default: 300 = 3%).

        Returns:
            str: Transaction signature.

        Raises:
            Exception: If the swap fails.
        """
        input_mint = str(input_mint)
        output_mint = str(output_mint)
        spl_client = AsyncToken(
            self.async_client, Pubkey.from_string(input_mint), TOKEN_PROGRAM_ID, wallet
        )
        mint = await spl_client.get_mint_info()
        decimals = mint.decimals
        input_amount = int(input_amount * 10**decimals)

        try:
            transaction_data = await self.jupiter.swap(
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
            signed_txn = VersionedTransaction.populate(
                raw_transaction.message, [signature]
            )
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.async_client.send_raw_transaction(
                txn=bytes(signed_txn), opts=opts
            )
            print(f"Transaction sent: {json.loads(result.to_json())}")
            transaction_id = json.loads(result.to_json())["result"]
            print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")
            await self.async_client.confirm_transaction(signature, commitment=Confirmed)
            print(
                f"Transaction confirmed: https://explorer.solana.com/tx/{transaction_id}"
            )
            return str(signature)

        except Exception as e:
            raise Exception(f"Swap failed: {str(e)}")

    async def get_user_token_balance(
        self, user_address: str, token_address: Optional[str] = None
    ) -> float:
        """
        Get the token balance for a given wallet.

        Args:
            user_address (str): The user wallet address.
            token_address (Option[str]): The mint address of the token, if it is set to None, the balance of SOL is returned.

        Returns:
            float: The token balance.
        """
        try:
            user_pubkey = Pubkey.from_string(user_address)
            if not token_address:
                response = await self.async_client.get_balance(
                    user_pubkey, commitment=Confirmed
                )
                return response.value / LAMPORTS_PER_SOL
            token_address = Pubkey.from_string(token_address)
            spl_client = AsyncToken(
                self.async_client, token_address, TOKEN_PROGRAM_ID, user_pubkey
            )

            mint = await spl_client.get_mint_info()
            if not mint.is_initialized:
                raise ValueError("Token mint is not initialized.")

            wallet_ata = get_associated_token_address(user_pubkey, token_address)
            response = await self.async_client.get_token_account_balance(wallet_ata)
            if response.value is None:
                return None
            response = response.value.ui_amount
            print(f"Balance response: {response}")

            return float(response)

        except Exception as error:
            raise Exception(f"Failed to get balance: {str(error)}") from error
