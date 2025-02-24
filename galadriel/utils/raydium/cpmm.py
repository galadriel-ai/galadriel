"""Raydium CPMM swap implementation."""

import base64
import logging
import os
import struct
from typing import Optional

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
    RAYDIUM_DEVNET_CREATE_CPMM_POOL_PROGRAM,
    RAYDIUM_MAINNET_CREATE_CPMM_POOL_PROGRAM,
    RAYDIUM_MAINNET_POOL_AUTHORITY,
    RAYDIUM_DEVNET_POOL_AUTHORITY,
    TOKEN_PROGRAM_ID,
    UNIT_BUDGET,
    UNIT_PRICE,
    WSOL,
)
from .layouts import CPMM_POOL_STATE_LAYOUT
from .types import DIRECTION, CpmmPoolKeys
from .utils import confirm_txn, get_token_balance, sol_for_tokens, tokens_for_sol

logger = logging.getLogger(__name__)


def fetch_cpmm_pool_keys(client: Client, network: Network, pair_address: str) -> Optional[CpmmPoolKeys]:
    """Fetch pool configuration for a Raydium CPMM pair."""
    try:
        # Get network-specific constants
        pool_authority = RAYDIUM_MAINNET_POOL_AUTHORITY if network == Network.MAINNET else RAYDIUM_DEVNET_POOL_AUTHORITY

        pool_state = Pubkey.from_string(pair_address)
        pool_state_account = client.get_account_info_json_parsed(pool_state, commitment=Processed).value
        if not pool_state_account:
            logger.error("Pool state account not found.")
            return None

        pool_state_data = pool_state_account.data
        parsed_data = CPMM_POOL_STATE_LAYOUT.parse(bytes(pool_state_data))

        pool_keys = CpmmPoolKeys(
            pool_state=pool_state,
            raydium_vault_auth_2=pool_authority,
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


def get_cpmm_reserves(client: Client, pool_keys: CpmmPoolKeys) -> tuple:
    """Get current token reserves from CPMM pool.

    Args:
        client (Client): The Solana RPC client
        pool_keys (CpmmPoolKeys): Pool configuration data

    Returns:
        tuple: (base_reserve, quote_reserve, token_decimal) or (None, None, None) if error
    """
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
        base_reserve = quote_account_balance - (protocol_fees_token_0 + fund_fees_token_0)
        quote_reserve = base_account_balance - (protocol_fees_token_1 + fund_fees_token_1)
        token_decimal = quote_decimal
    else:
        base_reserve = base_account_balance - (protocol_fees_token_1 + fund_fees_token_1)
        quote_reserve = quote_account_balance - (protocol_fees_token_0 + fund_fees_token_0)
        token_decimal = base_decimal

    logger.info(f"Base Mint: {base_mint} | Quote Mint: {quote_mint}")
    logger.info(f"Base Reserve: {base_reserve} | Quote Reserve: {quote_reserve} | Token Decimal: {token_decimal}")
    return base_reserve, quote_reserve, token_decimal


def make_cpmm_swap_instruction(
    amount_in: int,
    minimum_amount_out: int,
    token_account_in: Pubkey,
    token_account_out: Pubkey,
    accounts: CpmmPoolKeys,
    owner: Pubkey,
    action: DIRECTION,
    network: Network,
) -> Instruction:
    """Create a swap instruction for a Raydium CPMM pool.

    Args:
        amount_in (int): Amount of tokens to swap in
        minimum_amount_out (int): Minimum amount of tokens to receive
        token_account_in (Pubkey): Token account address for input
        token_account_out (Pubkey): Token account address for output
        accounts (CpmmPoolKeys): Pool configuration data
        owner (Pubkey): Transaction signer's public key
        action (DIRECTION): Swap direction (BUY or SELL)
        network (Network): Network to use (mainnet or devnet)

    Returns:
        Instruction: The compiled swap instruction
    """
    try:
        # Get network-specific program ID
        pool_program = (
            RAYDIUM_MAINNET_CREATE_CPMM_POOL_PROGRAM
            if network == Network.MAINNET
            else RAYDIUM_DEVNET_CREATE_CPMM_POOL_PROGRAM
        )

        # Initialize variables with default values
        input_vault = None
        output_vault = None
        input_token_program = None
        output_token_program = None
        input_token_mint = None
        output_token_mint = None

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
        else:
            raise ValueError("Invalid action")

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
        data.extend(bytes.fromhex("8fbe5adac41e33de"))  # CPMM swap instruction discriminator
        data.extend(struct.pack("<Q", amount_in))
        data.extend(struct.pack("<Q", minimum_amount_out))
        swap_instruction = Instruction(pool_program, bytes(data), keys)

        return swap_instruction

    except Exception as e:
        logger.error(f"Error creating swap instruction: {e}")
        raise


def buy(
    client: Client,
    network: Network,
    payer_keypair: Keypair,
    pair_address: str,
    sol_in: float = 0.1,
    slippage: int = 5,
) -> Optional[str]:
    """Buy tokens with SOL using Raydium CPMM."""
    logger.info(f"Starting buy transaction for pair address: {pair_address}")

    try:
        # Set compute budget
        compute_budget_instruction = set_compute_unit_limit(UNIT_BUDGET)
        compute_price_instruction = set_compute_unit_price(UNIT_PRICE)

        # Fetch pool configuration
        logger.info("Fetching pool keys...")
        pool_keys: Optional[CpmmPoolKeys] = fetch_cpmm_pool_keys(client, network, pair_address)
        if pool_keys is None:
            logger.error("No pool keys found...")
            return None

        # Determine token mint based on pool configuration
        if pool_keys.token_0_mint == WSOL:
            mint = pool_keys.token_1_mint
        else:
            mint = pool_keys.token_0_mint

        # Calculate swap amounts
        logger.info("Calculating transaction amounts...")
        amount_in = int(sol_in * LAMPORTS_PER_SOL)

        base_reserve, quote_reserve, token_decimal = get_cpmm_reserves(client, pool_keys)
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
        swap_instruction = make_cpmm_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=wsol_token_account,
            token_account_out=token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
            action=DIRECTION.BUY,
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
    """Sell tokens for SOL using Raydium CPMM.

    Args:
        client (Client): The Solana RPC client
        payer_keypair (Keypair): The transaction signer's keypair
        pair_address (str): The Raydium CPMM pair address
        percentage (int, optional): Percentage of token balance to sell. Defaults to 100
        slippage (int, optional): Slippage tolerance percentage. Defaults to 5

    Returns:
        Optional[str]: Transaction signature if successful, None otherwise
    """
    try:
        # Set compute budget
        compute_budget_instruction = set_compute_unit_limit(UNIT_BUDGET)
        compute_price_instruction = set_compute_unit_price(UNIT_PRICE)

        # Fetch pool configuration
        logger.info("Fetching pool keys...")
        pool_keys: Optional[CpmmPoolKeys] = fetch_cpmm_pool_keys(client, network, pair_address)
        if pool_keys is None:
            logger.error("No pool keys found...")
            return None

        # Determine token mint based on pool configuration
        if pool_keys.token_0_mint == WSOL:
            mint = pool_keys.token_1_mint
        else:
            mint = pool_keys.token_0_mint

        # Get token balance
        logger.info("Retrieving token balance...")
        token_balance = get_token_balance(client, payer_keypair.pubkey(), str(mint))
        if token_balance == 0 or token_balance is None:
            logger.error("No token balance available to sell.")
            return None

        if amount_in > token_balance:
            logger.error("Insufficient token balance to sell.")
            return None

        # Calculate swap amounts
        logger.info("Calculating transaction amounts...")
        base_reserve, quote_reserve, token_decimal = get_cpmm_reserves(client, pool_keys)
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
        swap_instruction = make_cpmm_swap_instruction(
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            token_account_in=token_account,
            token_account_out=wsol_token_account,
            accounts=pool_keys,
            owner=payer_keypair.pubkey(),
            action=DIRECTION.SELL,
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
