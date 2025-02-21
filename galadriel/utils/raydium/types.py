"""Type definitions for Raydium protocol data structures."""

from dataclasses import dataclass
from enum import Enum
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401


class DIRECTION(Enum):
    """Enum for swap direction in CPMM pools.

    Values:
        BUY: Swap SOL for tokens
        SELL: Swap tokens for SOL
    """

    BUY = 0
    SELL = 1


@dataclass
class CpmmPoolKeys:
    """Data structure for Raydium CPMM pool configuration.

    Contains all necessary public keys and parameters for interacting
    with a Raydium CPMM pool.

    Attributes:
        pool_state (Pubkey): Pool state account address
        raydium_vault_auth_2 (Pubkey): Raydium vault authority
        amm_config (Pubkey): AMM configuration account
        pool_creator (Pubkey): Pool creator's address
        token_0_vault (Pubkey): Token 0 vault address
        token_1_vault (Pubkey): Token 1 vault address
        lp_mint (Pubkey): LP token mint address
        token_0_mint (Pubkey): Token 0 mint address
        token_1_mint (Pubkey): Token 1 mint address
        token_0_program (Pubkey): Token 0 program ID
        token_1_program (Pubkey): Token 1 program ID
        observation_key (Pubkey): Price observation account
        auth_bump (int): Authority bump seed
        status (int): Pool status
        lp_mint_decimals (int): LP token decimals
        mint_0_decimals (int): Token 0 decimals
        mint_1_decimals (int): Token 1 decimals
        lp_supply (int): Total LP token supply
        protocol_fees_token_0 (int): Protocol fees in token 0
        protocol_fees_token_1 (int): Protocol fees in token 1
        fund_fees_token_0 (int): Fund fees in token 0
        fund_fees_token_1 (int): Fund fees in token 1
        open_time (int): Pool opening timestamp
    """

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


@dataclass
class AmmV4PoolKeys:
    """Data structure for Raydium AMM V4 pool configuration.

    Contains all necessary public keys and parameters for interacting
    with a Raydium AMM V4 pool.

    Attributes:
        amm_id (Pubkey): The AMM pool's public key
        base_mint (Pubkey): Base token mint address
        quote_mint (Pubkey): Quote token mint address
        base_decimals (int): Base token decimal places
        quote_decimals (int): Quote token decimal places
        open_orders (Pubkey): OpenBook open orders account
        target_orders (Pubkey): Target orders account
        base_vault (Pubkey): Base token vault
        quote_vault (Pubkey): Quote token vault
        market_id (Pubkey): OpenBook market ID
        market_authority (Pubkey): Market authority account
        market_base_vault (Pubkey): Market base token vault
        market_quote_vault (Pubkey): Market quote token vault
        bids (Pubkey): Market bids account
        asks (Pubkey): Market asks account
        event_queue (Pubkey): Market event queue
        ray_authority_v4 (Pubkey): Raydium authority account
        open_book_program (Pubkey): OpenBook program ID
        token_program_id (Pubkey): Token program ID
    """

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
