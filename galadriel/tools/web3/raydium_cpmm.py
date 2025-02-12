import base64
from dataclasses import dataclass
import logging
import os
import struct
from typing import Optional
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.rpc.api import Client
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.instruction import AccountMeta, Instruction  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)
from solders.transaction import VersionedTransaction  # type: ignore
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
    Enum,
    Struct,
    Int64ul,
    Int8ul,
    Bytes,
    Array,
    Padding,
    Int8ul,
    Flag,
    Int16ul,
    GreedyRange,
    Adapter,
)


from galadriel.tools.web3.wallet_tool import WalletTool
from galadriel.tools.web3.raydium_openbook import confirm_txn, get_token_balance

logger = logging.getLogger(__name__)

UNIT_BUDGET = 150_000
UNIT_PRICE = 1_000_000

# Raydium AMM V4 devnet addresses
RAYDIUM_CREATE_CPMM_POOL_PROGRAM = Pubkey.from_string(
    "CPMDWBwJDtYax9qW7AyRuVC19Cc4L4Vcy4n2BHAbHkCW"
)
CREATE_CPMM_POOL_AUTHORITY = Pubkey.from_string("7rQ1QFNosMkUCuh7Z7fPbTHvh73b68sQYdirycEzJVuw")

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ACCOUNT_LAYOUT_LEN = 165
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
SOL_DECIMAL = 1e9

client = Client("https://api.devnet.solana.com")  # type: ignore


@dataclass
class CpmmPoolKeys:
    pool_state: Pubkey
    raydium_vault_auth_2: Pubkey
    amm_config: Pubkey
    pool_creator: Pubkey
    token_0_vault: Pubkey
    token_1_vault: Pubkey
    lp_mint: Pubkey
    token_0_mint: Pubkey
    token_1_mint: Pubkey
    token_0_program: Pubkey
    token_1_program: Pubkey
    observation_key: Pubkey
    auth_bump: int
    status: int
    lp_mint_decimals: int
    mint_0_decimals: int
    mint_1_decimals: int
    lp_supply: int
    protocol_fees_token_0: int
    protocol_fees_token_1: int
    fund_fees_token_0: int
    fund_fees_token_1: int
    open_time: int


class DIRECTION(Enum):
    BUY = 0
    SELL = 1


CPMM_POOL_STATE_LAYOUT = Struct(
    Padding(8),
    "amm_config" / Bytes(32),
    "pool_creator" / Bytes(32),
    "token_0_vault" / Bytes(32),
    "token_1_vault" / Bytes(32),
    "lp_mint" / Bytes(32),
    "token_0_mint" / Bytes(32),
    "token_1_mint" / Bytes(32),
    "token_0_program" / Bytes(32),
    "token_1_program" / Bytes(32),
    "observation_key" / Bytes(32),
    "auth_bump" / Int8ul,
    "status" / Int8ul,
    "lp_mint_decimals" / Int8ul,
    "mint_0_decimals" / Int8ul,
    "mint_1_decimals" / Int8ul,
    "lp_supply" / Int64ul,
    "protocol_fees_token_0" / Int64ul,
    "protocol_fees_token_1" / Int64ul,
    "fund_fees_token_0" / Int64ul,
    "fund_fees_token_1" / Int64ul,
    "open_time" / Int64ul,
    "padding" / Array(32, Int64ul),
)

AMM_CONFIG_LAYOUT = Struct(
    Padding(8),
    "bump" / Int8ul,
    "disable_create_pool" / Flag,
    "index" / Int16ul,
    "trade_fee_rate" / Int64ul,
    "protocol_fee_rate" / Int64ul,
    "fund_fee_rate" / Int64ul,
    "create_pool_fee" / Int64ul,
    "protocol_owner" / Bytes(32),
    "fund_owner" / Bytes(32),
    "padding" / Array(16, Int64ul),
)


class UInt128Adapter(Adapter):
    def _decode(self, obj, context, path):
        return (obj.high << 64) | obj.low

    def _encode(self, obj, context, path):
        high = (obj >> 64) & ((1 << 64) - 1)
        low = obj & ((1 << 64) - 1)
        return dict(high=high, low=low)


UInt128ul = UInt128Adapter(Struct("low" / Int64ul, "high" / Int64ul))

OBSERVATION = Struct(
    "block_timestamp" / Int64ul,
    "cumulative_token_0_price_x32" / UInt128ul,
    "cumulative_token_1_price_x32" / UInt128ul,
)

OBSERVATION_STATE = Struct(
    Padding(8),
    "initialized" / Flag,
    "observationIndex" / Int16ul,
    "poolId" / Bytes(32),
    "observations" / GreedyRange(OBSERVATION),
    "padding" / GreedyRange(Int64ul),
)


class BuyTokenWithSolTool(WalletTool):
    name = "buy_token_with_sol_cpmm"
    description = "Buy a token with SOL using the Raydium CPMM."
    inputs = {
        "pair_address": {
            "type": "string",
            "description": "The address of the CPMM pair",
        },
        "sol_in": {
            "type": "number",
            "description": "The amount of SOL to swap",
            "default": 0.01,
            "nullable": True,
        },
        "slippage": {
            "type": "integer",
            "description": "The slippage tolerance percentage",
            "default": 5,
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, pair_address: str, sol_in: float = 0.01, slippage: int = 5) -> str:
        payer_keypair = self.wallet_repository.get_wallet()
        result = buy(payer_keypair, pair_address, sol_in, slippage)
        return "Transaction successful" if result else "Transaction failed"


class SellTokenForSolTool(WalletTool):
    name = "sell_token_for_sol_cpmm"
    description = "Sell a token for SOL using the Raydium CPMM."
    inputs = {
        "pair_address": {
            "type": "string",
            "description": "The address of the CPMM pair",
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

    def forward(self, pair_address: str, percentage: int = 100, slippage: int = 5) -> str:
        payer_keypair = self.wallet_repository.get_wallet()
        result = sell(payer_keypair, pair_address, percentage, slippage)
        return "Transaction successful" if result else "Transaction failed"


def buy(payer_keypair: Keypair, pair_address: str, sol_in: float = 0.1, slippage: int = 1) -> bool:
    logger.info(f"Starting buy transaction for pair address: {pair_address}")

    logger.info("Fetching pool keys...")
    pool_keys: Optional[CpmmPoolKeys] = fetch_cpmm_pool_keys(pair_address)
    if pool_keys is None:
        logger.error("No pool keys found...")
        return False
    logger.info("Pool keys fetched successfully.")

    if pool_keys.token_0_mint == WSOL:
        mint = pool_keys.token_1_mint
        token_program = pool_keys.token_1_program
    else:
        mint = pool_keys.token_0_mint
        token_program = pool_keys.token_0_program

    logger.info("Calculating transaction amounts...")
    amount_in = int(sol_in * SOL_DECIMAL)

    base_reserve, quote_reserve, token_decimal = get_cpmm_reserves(pool_keys)
    amount_out = sol_for_tokens(sol_in, base_reserve, quote_reserve)
    logger.info(f"Estimated Amount Out: {amount_out}")

    slippage_adjustment = 1 - (slippage / 100)
    amount_out_with_slippage = amount_out * slippage_adjustment
    minimum_amount_out = int(amount_out_with_slippage * 10**token_decimal)
    logger.info(f"Amount In: {amount_in} | Minimum Amount Out: {minimum_amount_out}")

    logger.info("Checking for existing token account...")
    token_account_check = client.get_token_accounts_by_owner(
        payer_keypair.pubkey(), TokenAccountOpts(mint), Processed
    )
    if token_account_check.value:
        token_account = token_account_check.value[0].pubkey
        token_account_instruction = None
        logger.info("Token account found.")
    else:
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint)
        token_account_instruction = create_associated_token_account(
            payer_keypair.pubkey(), payer_keypair.pubkey(), mint, token_program
        )
        logger.info("No existing token account found; creating associated token account.")

    logger.info("Generating seed for WSOL account...")
    seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
    wsol_token_account = Pubkey.create_with_seed(payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID)
    balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

    logger.info("Creating and initializing WSOL account...")
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

    logger.info("Creating swap instructions...")
    swap_instruction = make_cpmm_swap_instruction(
        amount_in=amount_in,
        minimum_amount_out=minimum_amount_out,
        token_account_in=wsol_token_account,
        token_account_out=token_account,
        accounts=pool_keys,
        owner=payer_keypair.pubkey(),
        action=DIRECTION.BUY,
    )

    logger.info("Preparing to close WSOL account after swap...")
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

    if token_account_instruction:
        instructions.append(token_account_instruction)

    instructions.append(swap_instruction)
    instructions.append(close_wsol_account_instruction)

    logger.info("Compiling transaction message...")
    compiled_message = MessageV0.try_compile(
        payer_keypair.pubkey(),
        instructions,
        [],
        client.get_latest_blockhash().value.blockhash,
    )

    logger.info("Sending transaction...")
    txn_sig = client.send_transaction(
        txn=VersionedTransaction(compiled_message, [payer_keypair]),
        opts=TxOpts(skip_preflight=True),
    ).value
    logger.info(f"Transaction Signature: {txn_sig}")

    logger.info("Confirming transaction...")
    confirmed = confirm_txn(txn_sig)

    logger.info(f"Transaction confirmed: {confirmed}")
    return confirmed


def sell(
    payer_keypair: Keypair, pair_address: str, percentage: int = 100, slippage: int = 1
) -> bool:
    try:
        logger.info("Fetching pool keys...")
        pool_keys: Optional[CpmmPoolKeys] = fetch_cpmm_pool_keys(pair_address)
        if pool_keys is None:
            logger.error("No pool keys found...")
            return False
        logger.info("Pool keys fetched successfully.")

        if pool_keys.token_0_mint == WSOL:
            mint = pool_keys.token_1_mint
            token_program_id = pool_keys.token_1_program
        else:
            mint = pool_keys.token_0_mint
            token_program_id = pool_keys.token_0_program

        logger.info("Retrieving token balance...")
        token_balance = get_token_balance(str(mint))
        logger.info(f"Token Balance: {token_balance}")

        if token_balance == 0 or token_balance is None:
            logger.error("No token balance available to sell.")
            return False

        token_balance = token_balance * (percentage / 100)
        logger.info(
            f"Selling {percentage}% of the token balance, adjusted balance: {token_balance}"
        )

        logger.info("Calculating transaction amounts...")
        base_reserve, quote_reserve, token_decimal = get_cpmm_reserves(pool_keys)
        amount_out = tokens_for_sol(token_balance, base_reserve, quote_reserve)
        logger.info(f"Estimated Amount Out: {amount_out}")

        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        minimum_amount_out = int(amount_out_with_slippage * SOL_DECIMAL)

        amount_in = int(token_balance * 10**token_decimal)
        logger.info(f"Amount In: {amount_in} | Minimum Amount Out: {minimum_amount_out}")
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint, token_program_id)

        logger.info("Generating seed and creating WSOL account...")
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

        logger.info("Creating swap instructions...")
        swap_instructions = make_cpmm_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=token_account,
            token_account_out=wsol_token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
            action=DIRECTION.SELL,
        )

        logger.info("Preparing to close WSOL account after swap...")
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
            logger.info("Preparing to close token account after swap...")
            close_token_account_instruction = close_account(
                CloseAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=token_account,
                    dest=payer_keypair.pubkey(),
                    owner=payer_keypair.pubkey(),
                )
            )
            instructions.append(close_token_account_instruction)

        logger.info("Compiling transaction message...")
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        logger.info("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value
        logger.info(f"Transaction Signature: {txn_sig}")

        logger.info("Confirming transaction...")
        confirmed = confirm_txn(txn_sig)

        logger.info(f"Transaction confirmed: {confirmed}")
        return confirmed

    except Exception as e:
        logger.error(f"Error occurred during transaction: {e}")
        return False


def fetch_cpmm_pool_keys(pair_address: str) -> Optional[CpmmPoolKeys]:
    try:
        pool_state = Pubkey.from_string(pair_address)
        pool_state_data = client.get_account_info_json_parsed(
            pool_state, commitment=Processed
        ).value.data
        parsed_data = CPMM_POOL_STATE_LAYOUT.parse(pool_state_data)

        pool_keys = CpmmPoolKeys(
            pool_state=pool_state,
            raydium_vault_auth_2=CREATE_CPMM_POOL_AUTHORITY,
            amm_config=Pubkey.from_bytes(parsed_data.amm_config),
            pool_creator=Pubkey.from_bytes(parsed_data.pool_creator),
            token_0_vault=Pubkey.from_bytes(parsed_data.token_0_vault),
            token_1_vault=Pubkey.from_bytes(parsed_data.token_1_vault),
            lp_mint=Pubkey.from_bytes(parsed_data.lp_mint),
            token_0_mint=Pubkey.from_bytes(parsed_data.token_0_mint),
            token_1_mint=Pubkey.from_bytes(parsed_data.token_1_mint),
            token_0_program=Pubkey.from_bytes(parsed_data.token_0_program),
            token_1_program=Pubkey.from_bytes(parsed_data.token_1_program),
            observation_key=Pubkey.from_bytes(parsed_data.observation_key),
            auth_bump=parsed_data.auth_bump,
            status=parsed_data.status,
            lp_mint_decimals=parsed_data.lp_mint_decimals,
            mint_0_decimals=parsed_data.mint_0_decimals,
            mint_1_decimals=parsed_data.mint_1_decimals,
            lp_supply=parsed_data.lp_supply,
            protocol_fees_token_0=parsed_data.protocol_fees_token_0,
            protocol_fees_token_1=parsed_data.protocol_fees_token_1,
            fund_fees_token_0=parsed_data.fund_fees_token_0,
            fund_fees_token_1=parsed_data.fund_fees_token_1,
            open_time=parsed_data.open_time,
        )

        return pool_keys

    except Exception as e:
        logger.error(f"Error fetching pool keys: {e}")
        return None


def make_cpmm_swap_instruction(
    amount_in: int,
    minimum_amount_out: int,
    token_account_in: Pubkey,
    token_account_out: Pubkey,
    accounts: CpmmPoolKeys,
    owner: Pubkey,
    action: DIRECTION,
) -> Instruction:
    try:

        if action == DIRECTION.BUY:
            input_vault = accounts.token_0_vault
            output_vault = accounts.token_1_vault
            input_token_program = accounts.token_0_program
            output_token_program = accounts.token_1_program
            input_token_mint = accounts.token_0_mint
            output_token_mint = accounts.token_1_mint
        elif action == DIRECTION.SELL:
            input_vault = accounts.token_1_vault
            output_vault = accounts.token_0_vault
            input_token_program = accounts.token_1_program
            output_token_program = accounts.token_0_program
            input_token_mint = accounts.token_1_mint
            output_token_mint = accounts.token_0_mint

        keys = [
            AccountMeta(pubkey=owner, is_signer=True, is_writable=True),
            AccountMeta(pubkey=accounts.raydium_vault_auth_2, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.amm_config, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.pool_state, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
            AccountMeta(pubkey=input_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=output_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=input_token_program, is_signer=False, is_writable=False),
            AccountMeta(pubkey=output_token_program, is_signer=False, is_writable=False),
            AccountMeta(pubkey=input_token_mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=output_token_mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=accounts.observation_key, is_signer=False, is_writable=True),
        ]

        data = bytearray()
        data.extend(bytes.fromhex("8fbe5adac41e33de"))
        data.extend(struct.pack("<Q", amount_in))
        data.extend(struct.pack("<Q", minimum_amount_out))
        swap_instruction = Instruction(RAYDIUM_CREATE_CPMM_POOL_PROGRAM, bytes(data), keys)

        return swap_instruction
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return None


def get_cpmm_reserves(pool_keys: CpmmPoolKeys):
    quote_vault = pool_keys.token_0_vault
    quote_decimal = pool_keys.mint_0_decimals
    quote_mint = pool_keys.token_0_mint

    base_vault = pool_keys.token_1_vault
    base_decimal = pool_keys.mint_1_decimals
    base_mint = pool_keys.token_1_mint

    protocol_fees_token_0 = pool_keys.protocol_fees_token_0 / (10**quote_decimal)
    fund_fees_token_0 = pool_keys.fund_fees_token_0 / (10**quote_decimal)
    protocol_fees_token_1 = pool_keys.protocol_fees_token_1 / (10**base_decimal)
    fund_fees_token_1 = pool_keys.fund_fees_token_1 / (10**base_decimal)

    balances_response = client.get_multiple_accounts_json_parsed(
        [quote_vault, base_vault], Processed
    )
    balances = balances_response.value

    quote_account = balances[0]
    base_account = balances[1]
    quote_account_balance = quote_account.data.parsed["info"]["tokenAmount"]["uiAmount"]
    base_account_balance = base_account.data.parsed["info"]["tokenAmount"]["uiAmount"]

    if quote_account_balance is None or base_account_balance is None:
        logger.error("Error: One of the account balances is None.")
        return None, None, None

    if base_mint == WSOL:
        base_reserve = quote_account_balance - (protocol_fees_token_0 + fund_fees_token_0)
        quote_reserve = base_account_balance - (protocol_fees_token_1 + fund_fees_token_1)
        token_decimal = quote_decimal
    else:
        base_reserve = base_account_balance - (protocol_fees_token_1 + fund_fees_token_1)
        quote_reserve = quote_account_balance - (protocol_fees_token_0 + fund_fees_token_0)
        token_decimal = base_decimal

    logger.info(f"Base Mint: {base_mint} | Quote Mint: {quote_mint}")
    logger.info(
        f"Base Reserve: {base_reserve} | Quote Reserve: {quote_reserve} | Token Decimal: {token_decimal}"
    )
    return base_reserve, quote_reserve, token_decimal


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


# main function to run the code
if __name__ == "__main__":
    # Example usage
    buy_tool = BuyTokenWithSolTool()
    buy_tool.forward("ftNSdLt7wuF9kKz6BxiUVWYWeRYGyt1RgL5sSjCVnJ2", 0.05, 5)
