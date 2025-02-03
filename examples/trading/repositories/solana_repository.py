from typing import Dict

from borsh_construct import CStruct, String, U64
import base64
import json
import os
from typing import Optional

from jupiter_python_sdk.jupiter import Jupiter
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.commitment import Processed
from solana.rpc.types import TxOpts
from solders import message
from solders.instruction import AccountMeta
from solders.instruction import Instruction
from solders.keypair import Keypair  # type: ignore
from solders.message import Message
from solders.pubkey import Pubkey  # type: ignore
from solders.system_program import TransferParams
from solders.system_program import transfer
from solders.transaction import Transaction
from solders.transaction import VersionedTransaction  # type: ignore
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

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
    def __init__(
        self,
        private_key_path: Optional[str] = None,
    ):
        self.async_client = AsyncClient(
            os.getenv("SOLANA_API_URL", SOLANA_API_URL)
        )
        if private_key_path:
            self.wallet = self._load_keypair_from_file(private_key_path)
        else:
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

    def _load_keypair_from_file(self, file_path):
        with open(file_path, "r") as f:
            secret_key = json.load(f)
        return Keypair.from_bytes(bytes(secret_key))

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
        input_amount = int(input_amount * 10 ** decimals)

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

    async def transfer_sol(self, recipient_address: str, amount: float) -> str:
        """
        Transfer SOL to a recipient asynchronously.

        Args:
            recipient_address (str): The Solana wallet address to send SOL to.
            amount (float): The amount of SOL to transfer.

        Returns:
            str: Transaction signature.

        Raises:
            Exception: If the transfer fails.
        """
        try:
            recipient_pubkey = Pubkey.from_string(recipient_address)
            sender_pubkey = self.wallet.pubkey()
            lamports = int(amount * LAMPORTS_PER_SOL)
            transfer_tx = transfer(
                TransferParams(
                    from_pubkey=sender_pubkey,
                    to_pubkey=recipient_pubkey,
                    lamports=lamports,
                )
            )
            recent_blockhash_response = await self.async_client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_response.value.blockhash

            msg = Message.new_with_blockhash([transfer_tx], self.wallet.pubkey(), recent_blockhash)
            transaction = VersionedTransaction(
                message=msg,
                keypairs=[self.wallet]
            )

            result = await self.async_client.send_transaction(
                transaction,
                opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed),
            )
            txn_signature = result.value
            await self.async_client.confirm_transaction(txn_signature, commitment=Confirmed)
            print(f"Transaction confirmed: https://explorer.solana.com/tx/{txn_signature}")

            return txn_signature
        except Exception as e:
            raise Exception(f"Transfer failed: {str(e)}")

    # TODO: this does not make any sense tbh, need to know the data storage structure in contract
    #  to actually decode the data
    async def fetch_account_data(self, account_address: str) -> bytes:
        """
        Fetch raw account storage data.

        Args:
            account_address (str): The public key of the account.

        Returns:
            bytes: The raw data stored in the account.
        """
        try:
            account_pubkey = Pubkey.from_string(account_address)
            response = await self.async_client.get_account_info(account_pubkey)

            if response.value is None:
                raise Exception("Account data not found.")

            return response.value.data  # Raw binary data, may need to decode using Borsh

        except Exception as e:
            raise Exception(f"Failed to fetch account data: {str(e)}")

    async def call_instruction(
        self, program_id: str, function_name: str, args: Dict, accounts: list
    ):
        try:
            program_pubkey = Pubkey.from_string(program_id)

            recent_blockhash_resp = await self.async_client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_resp.value.blockhash

            instruction = Instruction(
                program_pubkey,
                self._encode_args(function_name, args),
                [
                    AccountMeta(
                        self.wallet.pubkey(),
                        is_signer=True,
                        is_writable=True
                    )
                ],
            )
            msg = Message([instruction])
            transaction = Transaction([self.wallet], msg, recent_blockhash)
            result = await self.async_client.send_transaction(
                transaction,
                opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed),
            )
            txn_signature = result.value
            await self.async_client.confirm_transaction(txn_signature, commitment=Confirmed)
            print(f"Transaction confirmed: https://explorer.solana.com/tx/{txn_signature}")

            return txn_signature
        except Exception as e:
            raise Exception(f"Failed to send transaction: {str(e)}")

    def _encode_args(self, function_name: str, args: dict) -> bytes:
        """
        Encodes arguments dynamically using Borsh.

        Args:
            function_name (str): The smart contract function being called.
            args (dict): The function arguments as key-value pairs.

        Returns:
            bytes: Serialized Borsh data.
        """
        try:
            # Define Borsh schema dynamically based on args
            arg_schema = CStruct(*(key / (String if isinstance(val, str) else U64) for key, val in args.items()))
            encoded_data = arg_schema.build(args)

            # Prefix function name for identification in contract
            function_selector = function_name.encode("utf-8")[:16]  # Max 16 bytes for function identifier
            return function_selector + encoded_data

        except Exception as e:
            raise Exception(f"Encoding failed: {str(e)}")
