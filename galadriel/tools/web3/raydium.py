import base64
from dataclasses import dataclass
import json
import os
import struct
import time
from typing import Optional
import logging
from solana.rpc.api import Client
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # pylint: disable=E0401
from solders.message import MessageV0  # pylint: disable=E0401
from solders.keypair import Keypair  # pylint: disable=E0401
from solders.pubkey import Pubkey  # pylint: disable=E0401
from solders.signature import Signature  # pylint: disable=E0401
from solders.instruction import AccountMeta, Instruction  # pylint: disable=E0401
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)
from solders.transaction import VersionedTransaction  # pylint: disable=E0401
from spl.token.client import Token
from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)

from construct import (
    Bytes,
    Int64ul,
    Padding,
    BitsInteger,
    BitsSwapped,
    BitStruct,
    Const,
    Flag,
    BytesInteger,
)
from construct import Struct as cStruct

from galadriel.tools.web3.wallet_tool import WalletTool


logger = logging.getLogger(__name__)

UNIT_BUDGET = 150_000
UNIT_PRICE = 1_000_000

RAYDIUM_AMM_V4 = Pubkey.from_string("HWy1jotHpo6UqeQxx49dpYYdQB8wj9Qk9MdxwjLvDHB8")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ACCOUNT_LAYOUT_LEN = 165
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
SOL_DECIMAL = 1e9

client = Client("https://api.devnet.solana.com")  # type: ignore

LIQUIDITY_STATE_LAYOUT_V4 = cStruct(
    "status" / Int64ul,
    "nonce" / Int64ul,
    "orderNum" / Int64ul,
    "depth" / Int64ul,
    "coinDecimals" / Int64ul,
    "pcDecimals" / Int64ul,
    "state" / Int64ul,
    "resetFlag" / Int64ul,
    "minSize" / Int64ul,
    "volMaxCutRatio" / Int64ul,
    "amountWaveRatio" / Int64ul,
    "coinLotSize" / Int64ul,
    "pcLotSize" / Int64ul,
    "minPriceMultiplier" / Int64ul,
    "maxPriceMultiplier" / Int64ul,
    "systemDecimalsValue" / Int64ul,
    "minSeparateNumerator" / Int64ul,
    "minSeparateDenominator" / Int64ul,
    "tradeFeeNumerator" / Int64ul,
    "tradeFeeDenominator" / Int64ul,
    "pnlNumerator" / Int64ul,
    "pnlDenominator" / Int64ul,
    "swapFeeNumerator" / Int64ul,
    "swapFeeDenominator" / Int64ul,
    "needTakePnlCoin" / Int64ul,
    "needTakePnlPc" / Int64ul,
    "totalPnlPc" / Int64ul,
    "totalPnlCoin" / Int64ul,
    "poolOpenTime" / Int64ul,
    "punishPcAmount" / Int64ul,
    "punishCoinAmount" / Int64ul,
    "orderbookToInitTime" / Int64ul,
    "swapCoinInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPcOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoin2PcFee" / Int64ul,
    "swapPcInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoinOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPc2CoinFee" / Int64ul,
    "poolCoinTokenAccount" / Bytes(32),
    "poolPcTokenAccount" / Bytes(32),
    "coinMintAddress" / Bytes(32),
    "pcMintAddress" / Bytes(32),
    "lpMintAddress" / Bytes(32),
    "ammOpenOrders" / Bytes(32),
    "serumMarket" / Bytes(32),
    "serumProgramId" / Bytes(32),
    "ammTargetOrders" / Bytes(32),
    "poolWithdrawQueue" / Bytes(32),
    "poolTempLpTokenAccount" / Bytes(32),
    "ammOwner" / Bytes(32),
    "pnlOwner" / Bytes(32),
)

ACCOUNT_FLAGS_LAYOUT = BitsSwapped(
    BitStruct(
        "initialized" / Flag,
        "market" / Flag,
        "open_orders" / Flag,
        "request_queue" / Flag,
        "event_queue" / Flag,
        "bids" / Flag,
        "asks" / Flag,
        Const(0, BitsInteger(57)),
    )
)

MARKET_STATE_LAYOUT_V3 = cStruct(
    Padding(5),
    "account_flags" / ACCOUNT_FLAGS_LAYOUT,
    "own_address" / Bytes(32),
    "vault_signer_nonce" / Int64ul,
    "base_mint" / Bytes(32),
    "quote_mint" / Bytes(32),
    "base_vault" / Bytes(32),
    "base_deposits_total" / Int64ul,
    "base_fees_accrued" / Int64ul,
    "quote_vault" / Bytes(32),
    "quote_deposits_total" / Int64ul,
    "quote_fees_accrued" / Int64ul,
    "quote_dust_threshold" / Int64ul,
    "request_queue" / Bytes(32),
    "event_queue" / Bytes(32),
    "bids" / Bytes(32),
    "asks" / Bytes(32),
    "base_lot_size" / Int64ul,
    "quote_lot_size" / Int64ul,
    "fee_rate_bps" / Int64ul,
    "referrer_rebate_accrued" / Int64ul,
    Padding(7),
)


@dataclass
class AmmV4PoolKeys:
    amm_id: Pubkey
    base_mint: Pubkey
    quote_mint: Pubkey
    base_decimals: int
    quote_decimals: int
    open_orders: Pubkey
    target_orders: Pubkey
    base_vault: Pubkey
    quote_vault: Pubkey
    market_id: Pubkey
    market_authority: Pubkey
    market_base_vault: Pubkey
    market_quote_vault: Pubkey
    bids: Pubkey
    asks: Pubkey
    event_queue: Pubkey
    ray_authority_v4: Pubkey
    open_book_program: Pubkey
    token_program_id: Pubkey


class BuyTokenWithSolTool(WalletTool):
    name = "buy_token_with_sol"
    description = "Buy a token with SOL using the Raydium AMM V4."
    inputs = {
        "pair_address": {
            "type": "string",
            "description": "The address of the AMM V4 pair",
        },
        "sol_in": {
            "type": "number",
            "description": "The amount of SOL to swap",
            "default": 0.01,
        },
        "slippage": {
            "type": "integer",
            "description": "The slippage tolerance percentage",
            "default": 5,
        },
    }
    output_type = "string"

    def forward(self, pair_address: str, sol_in: float = 0.01, slippage: int = 5) -> str:  # pylint: disable=W0221
        payer_keypair = self.wallet_repository.get_wallet()
        result = buy(payer_keypair, pair_address, sol_in, slippage)
        return result


class SellTokenForSolTool(WalletTool):
    name = "sell_token_for_sol"
    description = "Sell a token for SOL using the Raydium AMM V4."
    inputs = {
        "pair_address": {
            "type": "string",
            "description": "The address of the AMM V4 pair",
        },
        "percentage": {
            "type": "integer",
            "description": "The percentage of token to sell",
            "default": 100,
        },
        "slippage": {
            "type": "integer",
            "description": "The slippage tolerance percentage",
            "default": 5,
        },
    }
    output_type = "string"

    def forward(self, pair_address: str, percentage: int = 100, slippage: int = 5) -> str:  # pylint: disable=W0221
        payer_keypair = self.wallet_repository.get_wallet()
        result = sell(payer_keypair, pair_address, percentage, slippage)
        return result


# pylint: disable=R0914
def buy(payer_keypair: Keypair, pair_address: str, sol_in: float = 0.01, slippage: int = 5) -> str:
    try:
        pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(pair_address)
        if pool_keys is None:
            return "Failed to fetch pool keys."

        mint = pool_keys.base_mint if pool_keys.base_mint != WSOL else pool_keys.quote_mint
        amount_in = int(sol_in * SOL_DECIMAL)

        base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(pool_keys)
        amount_out = sol_for_tokens(sol_in, base_reserve, quote_reserve)

        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        minimum_amount_out = int(amount_out_with_slippage * 10**token_decimal)

        token_account_check = client.get_token_accounts_by_owner(
            payer_keypair.pubkey(), TokenAccountOpts(mint), Processed
        )
        if token_account_check.value:
            token_account = token_account_check.value[0].pubkey
            create_token_account_instruction = None
        else:
            token_account = get_associated_token_address(payer_keypair.pubkey(), mint)
            create_token_account_instruction = create_associated_token_account(
                payer_keypair.pubkey(), payer_keypair.pubkey(), mint
            )

        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        wsol_token_account = Pubkey.create_with_seed(payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID)
        balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

        create_wsol_account_instruction = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=wsol_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=int(balance_needed + amount_in),
                space=ACCOUNT_LAYOUT_LEN,
                owner=TOKEN_PROGRAM_ID,
            )
        )

        init_wsol_account_instruction = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                mint=WSOL,
                owner=payer_keypair.pubkey(),
            )
        )

        swap_instruction = make_amm_v4_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=wsol_token_account,
            token_account_out=token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
        )

        close_wsol_account_instruction = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE),
            create_wsol_account_instruction,
            init_wsol_account_instruction,
        ]

        if create_token_account_instruction:
            instructions.append(create_token_account_instruction)

        instructions.append(swap_instruction)  # type: ignore
        instructions.append(close_wsol_account_instruction)

        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value

        confirmed = confirm_txn(txn_sig)

        if confirmed:
            return f"Transaction successful. Signature: {txn_sig}"
        return "Transaction failed. Confirmation timeout."

    except Exception as e:
        return f"Error occurred during transaction: {e}"


def sell(payer_keypair: Keypair, pair_address: str, percentage: int = 100, slippage: int = 5) -> str:
    try:
        if not 1 <= percentage <= 100:
            return "Percentage must be between 1 and 100."

        pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(pair_address)
        if pool_keys is None:
            return "Failed to fetch pool keys."

        mint = pool_keys.base_mint if pool_keys.base_mint != WSOL else pool_keys.quote_mint
        token_balance = get_token_balance(payer_keypair.pubkey(), str(mint))

        if token_balance == 0 or token_balance is None:
            return "No token balance available to sell."

        token_balance = token_balance * (percentage / 100)
        base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(pool_keys)
        amount_out = tokens_for_sol(token_balance, base_reserve, quote_reserve)

        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        minimum_amount_out = int(amount_out_with_slippage * SOL_DECIMAL)

        amount_in = int(token_balance * 10**token_decimal)
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint)

        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        wsol_token_account = Pubkey.create_with_seed(payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID)
        balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

        create_wsol_account_instruction = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=wsol_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=int(balance_needed),
                space=ACCOUNT_LAYOUT_LEN,
                owner=TOKEN_PROGRAM_ID,
            )
        )

        init_wsol_account_instruction = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                mint=WSOL,
                owner=payer_keypair.pubkey(),
            )
        )

        swap_instructions = make_amm_v4_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=token_account,
            token_account_out=wsol_token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
        )

        close_wsol_account_instruction = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE),
            create_wsol_account_instruction,
            init_wsol_account_instruction,
            swap_instructions,
            close_wsol_account_instruction,
        ]

        if percentage == 100:
            close_token_account_instruction = close_account(
                CloseAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=token_account,
                    dest=payer_keypair.pubkey(),
                    owner=payer_keypair.pubkey(),
                )
            )
            instructions.append(close_token_account_instruction)

        # Filter out any None instructions
        valid_instructions = [instr for instr in instructions if instr is not None]
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            valid_instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value

        confirmed = confirm_txn(txn_sig)

        if confirmed:
            return f"Transaction successful. Signature: {txn_sig}"
        return "Transaction failed. Confirmation timeout."

    except Exception as e:
        return f"Error occurred during transaction: {e}"


def sol_for_tokens(sol_amount, base_vault_balance, quote_vault_balance, swap_fee=0.25):
    effective_sol_used = sol_amount - (sol_amount * (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_base_vault_balance = constant_product / (quote_vault_balance + effective_sol_used)
    tokens_received = base_vault_balance - updated_base_vault_balance
    return round(tokens_received, 9)


def tokens_for_sol(token_amount, base_vault_balance, quote_vault_balance, swap_fee=0.25):
    effective_tokens_sold = token_amount * (1 - (swap_fee / 100))
    constant_product = base_vault_balance * quote_vault_balance
    updated_quote_vault_balance = constant_product / (base_vault_balance + effective_tokens_sold)
    sol_received = quote_vault_balance - updated_quote_vault_balance
    return round(sol_received, 9)


def fetch_amm_v4_pool_keys(pair_address: str) -> Optional[AmmV4PoolKeys]:

    def bytes_of(value):
        if not 0 <= value < 2**64:
            raise ValueError("Value must be in the range of a u64 (0 to 2^64 - 1).")
        return struct.pack("<Q", value)

    try:
        amm_id = Pubkey.from_string(pair_address)
        amm_data = client.get_account_info_json_parsed(amm_id, commitment=Processed).value.data  # type: ignore
        amm_data_decoded = LIQUIDITY_STATE_LAYOUT_V4.parse(amm_data)  # type: ignore
        _market_id = Pubkey.from_bytes(amm_data_decoded.serumMarket)
        _market_info = client.get_account_info_json_parsed(_market_id, commitment=Processed).value.data  # type: ignore
        market_decoded = MARKET_STATE_LAYOUT_V3.parse(_market_info)  # type: ignore
        vault_signer_nonce = market_decoded.vault_signer_nonce

        ray_authority_v4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
        open_book_program = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

        pool_keys = AmmV4PoolKeys(
            amm_id=amm_id,
            base_mint=Pubkey.from_bytes(market_decoded.base_mint),
            quote_mint=Pubkey.from_bytes(market_decoded.quote_mint),
            base_decimals=amm_data_decoded.coinDecimals,
            quote_decimals=amm_data_decoded.pcDecimals,
            open_orders=Pubkey.from_bytes(amm_data_decoded.ammOpenOrders),
            target_orders=Pubkey.from_bytes(amm_data_decoded.ammTargetOrders),
            base_vault=Pubkey.from_bytes(amm_data_decoded.poolCoinTokenAccount),
            quote_vault=Pubkey.from_bytes(amm_data_decoded.poolPcTokenAccount),
            market_id=_market_id,
            market_authority=Pubkey.create_program_address(
                seeds=[bytes(_market_id), bytes_of(vault_signer_nonce)],
                program_id=open_book_program,
            ),
            market_base_vault=Pubkey.from_bytes(market_decoded.base_vault),
            market_quote_vault=Pubkey.from_bytes(market_decoded.quote_vault),
            bids=Pubkey.from_bytes(market_decoded.bids),
            asks=Pubkey.from_bytes(market_decoded.asks),
            event_queue=Pubkey.from_bytes(market_decoded.event_queue),
            ray_authority_v4=ray_authority_v4,
            open_book_program=open_book_program,
            token_program_id=TOKEN_PROGRAM_ID,
        )

        return pool_keys
    except Exception as e:
        logger.error(f"Error fetching pool keys: {e}")
        return None


def get_amm_v4_reserves(pool_keys: AmmV4PoolKeys) -> tuple:
    try:
        quote_vault = pool_keys.quote_vault
        quote_decimal = pool_keys.quote_decimals
        quote_mint = pool_keys.quote_mint

        base_vault = pool_keys.base_vault
        base_decimal = pool_keys.base_decimals
        base_mint = pool_keys.base_mint

        balances_response = client.get_multiple_accounts_json_parsed([quote_vault, base_vault], Processed)
        balances = balances_response.value

        quote_account = balances[0]
        base_account = balances[1]

        quote_account_balance = quote_account.data.parsed["info"]["tokenAmount"]["uiAmount"]  # type: ignore
        base_account_balance = base_account.data.parsed["info"]["tokenAmount"]["uiAmount"]  # type: ignore

        if quote_account_balance is None or base_account_balance is None:
            logger.error("Error: One of the account balances is None.")
            return None, None, None

        if base_mint == WSOL:
            base_reserve = quote_account_balance
            quote_reserve = base_account_balance
            token_decimal = quote_decimal
        else:
            base_reserve = base_account_balance
            quote_reserve = quote_account_balance
            token_decimal = base_decimal

        logger.info(f"Base Mint: {base_mint} | Quote Mint: {quote_mint}")
        logger.info(f"Base Reserve: {base_reserve} | Quote Reserve: {quote_reserve} | Token Decimal: {token_decimal}")
        return base_reserve, quote_reserve, token_decimal

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return None, None, None


# pylint: disable=R0917
def make_amm_v4_swap_instruction(
    amount_in: int,
    minimum_amount_out: int,
    token_account_in: Pubkey,
    token_account_out: Pubkey,
    accounts: AmmV4PoolKeys,
    owner: Pubkey,
) -> Optional[Instruction]:
    try:

        keys = [
            AccountMeta(pubkey=accounts.token_program_id, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.amm_id, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.ray_authority_v4, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.open_orders, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.target_orders, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.base_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.quote_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.open_book_program, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.market_id, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.bids, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.asks, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.event_queue, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_base_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_quote_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=accounts.market_authority, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False),
        ]

        data = bytearray()
        discriminator = 9
        data.extend(struct.pack("<B", discriminator))
        data.extend(struct.pack("<Q", amount_in))
        data.extend(struct.pack("<Q", minimum_amount_out))
        swap_instruction = Instruction(RAYDIUM_AMM_V4, bytes(data), keys)

        return swap_instruction
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return None


def get_token_balance(pubkey: Pubkey, mint_str: str) -> float | None:

    mint = Pubkey.from_string(mint_str)
    response = client.get_token_accounts_by_owner_json_parsed(pubkey, TokenAccountOpts(mint=mint), commitment=Processed)

    if response.value:
        accounts = response.value
        if accounts:
            try:
                token_amount = accounts[0].account.data.parsed["info"]["tokenAmount"]["uiAmount"]  # type: ignore
                if isinstance(token_amount, (int, float, str)):
                    return float(token_amount)
            except Exception as e:
                logger.error(f"Failed to parse token amount: {e}")
                return None
    return None


def confirm_txn(txn_sig: Signature, max_retries: int = 20, retry_interval: int = 3) -> bool:
    retries = 1

    while retries < max_retries:
        try:
            txn_res = client.get_transaction(
                txn_sig,
                encoding="json",
                commitment=Confirmed,
                max_supported_transaction_version=0,
            )
            if txn_res.value and txn_res.value.transaction.meta:
                txn_json = json.loads(txn_res.value.transaction.meta.to_json())
            else:
                return False

            if txn_json["err"] is None:
                logger.info("Transaction confirmed... try count:", retries)
                return True

            logger.error("Error: Transaction not confirmed. Retrying...")
            if txn_json["err"]:
                logger.error("Transaction failed.")
                return False
        except Exception:
            logger.info("Awaiting confirmation... try count:", retries)
            retries += 1
            time.sleep(retry_interval)

    logger.error("Max retries reached. Transaction confirmation failed.")
    return False


# main function to run the code
if __name__ == "__main__":
    # buy_token
    buy_token_with_sol_tool = BuyTokenWithSolTool()
    buy_token_with_sol_tool.forward("HWy1jotHpo6UqeQxx49dpYYdQB8wj9Qk9MdxwjLvDHB8", 0.01, 5)
