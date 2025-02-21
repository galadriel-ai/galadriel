"""Raydium OpenBook swap implementation."""

import base64
import logging
import os
from typing import Optional
import struct

from solana.rpc.api import Client
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.instruction import AccountMeta, Instruction  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed  # type: ignore
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

from galadriel.tools.web3.onchain.solana.base_tool import Network

from .constants import (
    ACCOUNT_LAYOUT_LEN,
    LAMPORTS_PER_SOL,
    TOKEN_PROGRAM_ID,
    UNIT_BUDGET,
    UNIT_PRICE,
    WSOL,
    RAYDIUM_MAINNET_AMM_V4,
    RAYDIUM_DEVNET_AMM_V4,
    RAYDIUM_MAINNET_AUTHORITY,
    RAYDIUM_DEVNET_AUTHORITY,
    OPENBOOK_MAINNET_MARKET,
    OPENBOOK_DEVNET_MARKET,
)
from .layouts import LIQUIDITY_STATE_LAYOUT_V4, MARKET_STATE_LAYOUT_V3
from .types import AmmV4PoolKeys
from .utils import confirm_txn, get_token_balance, sol_for_tokens, tokens_for_sol

logger = logging.getLogger(__name__)


def fetch_amm_v4_pool_keys(client: Client, network: Network, pair_address: str) -> Optional[AmmV4PoolKeys]:
    """Fetch pool configuration for a Raydium AMM V4 pair.

    Retrieves and parses pool configuration data from the Solana blockchain.

    Args:
        client (Client): The Solana RPC client
        pair_address (str): The Raydium AMM V4 pair address

    Returns:
        Optional[AmmV4PoolKeys]: Pool configuration if successful, None otherwise

    Note:
        Includes market data from OpenBook integration
    """

    def bytes_of(value):
        if not 0 <= value < 2**64:
            raise ValueError("Value must be in the range of a u64 (0 to 2^64 - 1).")
        return struct.pack("<Q", value)

    openbook_market = OPENBOOK_MAINNET_MARKET if network == Network.MAINNET else OPENBOOK_DEVNET_MARKET
    openbook_authority = RAYDIUM_MAINNET_AUTHORITY if network == Network.MAINNET else RAYDIUM_DEVNET_AUTHORITY

    try:
        amm_id = Pubkey.from_string(pair_address)
        amm_data = client.get_account_info_json_parsed(amm_id, commitment=Processed).value.data  # type: ignore
        amm_data_decoded = LIQUIDITY_STATE_LAYOUT_V4.parse(amm_data)  # type: ignore
        market_id = Pubkey.from_bytes(amm_data_decoded.serumMarket)
        market_info = client.get_account_info_json_parsed(market_id, commitment=Processed).value.data  # type: ignore
        market_decoded = MARKET_STATE_LAYOUT_V3.parse(market_info)  # type: ignore
        vault_signer_nonce = market_decoded.vault_signer_nonce

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
            market_id=market_id,
            market_authority=Pubkey.create_program_address(
                seeds=[bytes(market_id), bytes_of(vault_signer_nonce)],
                program_id=openbook_market,
            ),
            market_base_vault=Pubkey.from_bytes(market_decoded.base_vault),
            market_quote_vault=Pubkey.from_bytes(market_decoded.quote_vault),
            bids=Pubkey.from_bytes(market_decoded.bids),
            asks=Pubkey.from_bytes(market_decoded.asks),
            event_queue=Pubkey.from_bytes(market_decoded.event_queue),
            ray_authority_v4=openbook_authority,
            open_book_program=openbook_market,
            token_program_id=TOKEN_PROGRAM_ID,
        )

        return pool_keys
    except Exception as e:
        logger.error(f"Error fetching pool keys: {e}")
        return None


def get_amm_v4_reserves(client: Client, pool_keys: AmmV4PoolKeys) -> tuple:
    """Get current token reserves from AMM pool.

    Fetches current balances of both tokens in the pool.

    Args:
        client (Client): The Solana RPC client
        pool_keys (AmmV4PoolKeys): Pool configuration data

    Returns:
        tuple: (base_reserve, quote_reserve, token_decimal) or (None, None, None) if error

    Note:
        Handles WSOL wrapping/unwrapping automatically
    """
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


def make_amm_v4_swap_instruction(
    amount_in: int,
    minimum_amount_out: int,
    token_account_in: Pubkey,
    token_account_out: Pubkey,
    accounts: AmmV4PoolKeys,
    owner: Pubkey,
    network: Network,
) -> Instruction:
    """Create swap instruction for Raydium AMM V4.

    Constructs the instruction for executing a token swap.

    Args:
        amount_in (int): Input token amount in raw units
        minimum_amount_out (int): Minimum acceptable output amount
        token_account_in (Pubkey): Source token account
        token_account_out (Pubkey): Destination token account
        accounts (AmmV4PoolKeys): Pool configuration
        owner (Pubkey): Transaction signer's public key

    Returns:
        Optional[Instruction]: Swap instruction if successful, None otherwise

    Note:
        Includes all necessary account metas for the swap
    """
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
        raydium_amm_v4 = RAYDIUM_MAINNET_AMM_V4 if network == Network.MAINNET else RAYDIUM_DEVNET_AMM_V4
        swap_instruction = Instruction(raydium_amm_v4, bytes(data), keys)

        return swap_instruction
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise e


def buy(
    client: Client,
    network: Network,
    payer_keypair: Keypair,
    pair_address: str,
    sol_in: float,
    slippage: int = 5,
) -> Optional[str]:
    """Buy tokens with SOL using Raydium AMM V4."""
    logger.info(f"Starting buy transaction for pair address: {pair_address}")

    try:
        # Set compute budget
        compute_budget_instruction = set_compute_unit_limit(UNIT_BUDGET)
        compute_price_instruction = set_compute_unit_price(UNIT_PRICE)

        # Fetch pool configuration
        logger.info("Fetching pool keys...")
        pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(client, network, pair_address)
        if pool_keys is None:
            logger.error("No pool keys found...")
            return None

        # Determine token mint based on pool configuration
        if pool_keys.base_mint == WSOL:
            mint = pool_keys.quote_mint
        else:
            mint = pool_keys.base_mint

        # Calculate swap amounts
        logger.info("Calculating transaction amounts...")
        amount_in = int(sol_in * LAMPORTS_PER_SOL)

        base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(client, pool_keys)
        amount_out = sol_for_tokens(sol_in, base_reserve, quote_reserve)
        logger.info(f"Estimated Amount Out: {amount_out}")

        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        minimum_amount_out = int(amount_out_with_slippage * 10**token_decimal)
        logger.info(f"Amount In: {amount_in} | Minimum Amount Out: {minimum_amount_out}")

        # Check for existing token account
        logger.info("Checking for existing token account...")
        token_account_check = client.get_token_accounts_by_owner(
            payer_keypair.pubkey(), TokenAccountOpts(mint), Processed
        )

        if token_account_check.value:
            token_account = token_account_check.value[0].pubkey
            token_account_instruction = None
        else:
            token_account = get_associated_token_address(payer_keypair.pubkey(), mint)
            token_account_instruction = create_associated_token_account(
                payer_keypair.pubkey(), payer_keypair.pubkey(), mint
            )

        # Create temporary WSOL account
        logger.info("Creating temporary WSOL account...")
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        wsol_token_account = Pubkey.create_with_seed(payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID)
        balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

        create_wsol_account_instruction = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=wsol_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=balance_needed + amount_in,
                space=ACCOUNT_LAYOUT_LEN,
                owner=TOKEN_PROGRAM_ID,
            )
        )

        initialize_wsol_account_instruction = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                mint=WSOL,
                owner=payer_keypair.pubkey(),
            )
        )

        close_wsol_account_instruction = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        # Create swap instruction
        logger.info("Creating swap instruction...")
        swap_instruction = make_amm_v4_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=wsol_token_account,
            token_account_out=token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
            network=network,
        )

        # Compile instructions
        instructions = [compute_budget_instruction, compute_price_instruction]
        instructions.extend([create_wsol_account_instruction, initialize_wsol_account_instruction])

        if token_account_instruction:
            instructions.append(token_account_instruction)

        instructions.append(swap_instruction)
        instructions.append(close_wsol_account_instruction)

        # Send transaction
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
            opts=TxOpts(skip_preflight=False),
        ).value
        logger.info(f"Transaction Signature: {txn_sig}")

        # Confirm transaction
        logger.info("Confirming transaction...")
        confirmed = confirm_txn(client, txn_sig)
        if not confirmed:
            logger.error("Transaction failed.")
            return None

        logger.info(f"Transaction confirmed: {txn_sig}")
        return str(txn_sig)

    except Exception as e:
        logger.error(f"Error occurred during transaction: {e}")
        return None


def sell(
    client: Client,
    network: Network,
    payer_keypair: Keypair,
    pair_address: str,
    amount_in: float,
    slippage: int = 5,
) -> Optional[str]:
    """Sell tokens for SOL using Raydium AMM V4."""
    try:
        # Set compute budget
        compute_budget_instruction = set_compute_unit_limit(UNIT_BUDGET)
        compute_price_instruction = set_compute_unit_price(UNIT_PRICE)

        # Fetch pool configuration
        logger.info("Fetching pool keys...")
        pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(client, network, pair_address)
        if pool_keys is None:
            logger.error("No pool keys found...")
            return None

        mint = pool_keys.base_mint if pool_keys.base_mint != WSOL else pool_keys.quote_mint
        # Get token balance
        logger.info("Retrieving token balance...")
        token_balance = get_token_balance(client, payer_keypair.pubkey(), str(mint))
        if token_balance == 0 or token_balance is None:
            logger.error("No token balance available to sell.")
            return None

        if amount_in > token_balance:
            logger.error("Insufficient token balance.")
            return None

        # Calculate swap amounts
        logger.info("Calculating transaction amounts...")
        base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(client, pool_keys)
        amount_out = tokens_for_sol(amount_in, base_reserve, quote_reserve)
        logger.info(f"Estimated Amount Out: {amount_out}")

        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        minimum_amount_out = int(amount_out_with_slippage * LAMPORTS_PER_SOL)

        amount_in = int(amount_in * 10**token_decimal)
        logger.info(f"Amount In: {amount_in} | Minimum Amount Out: {minimum_amount_out}")

        # Get token account
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint)

        # Create temporary WSOL account
        logger.info("Creating temporary WSOL account...")
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        wsol_token_account = Pubkey.create_with_seed(payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID)
        balance_needed = Token.get_min_balance_rent_for_exempt_for_account(client)

        create_wsol_account_instruction = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=wsol_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=balance_needed,
                space=ACCOUNT_LAYOUT_LEN,
                owner=TOKEN_PROGRAM_ID,
            )
        )

        initialize_wsol_account_instruction = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                mint=WSOL,
                owner=payer_keypair.pubkey(),
            )
        )

        close_wsol_account_instruction = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        # Create swap instruction
        logger.info("Creating swap instruction...")
        swap_instruction = make_amm_v4_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=token_account,
            token_account_out=wsol_token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
            network=network,
        )

        # Compile instructions
        instructions = [compute_budget_instruction, compute_price_instruction]
        instructions.extend([create_wsol_account_instruction, initialize_wsol_account_instruction])
        instructions.append(swap_instruction)
        instructions.append(close_wsol_account_instruction)

        # Send transaction
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

        # Confirm transaction
        logger.info("Confirming transaction...")
        confirmed = confirm_txn(client, txn_sig)
        if not confirmed:
            logger.error("Transaction failed.")
            return None

        logger.info(f"Transaction confirmed: {txn_sig}")
        return str(txn_sig)

    except Exception as e:
        logger.error(f"Error occurred during transaction: {e}")
        return None
