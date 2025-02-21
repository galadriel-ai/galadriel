"""Constants used in Raydium protocol interactions."""

from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401

# Budget and pricing constants
UNIT_BUDGET = 150_000
UNIT_PRICE = 1_000_000
LAMPORTS_PER_SOL = 1_000_000_000

ACCOUNT_LAYOUT_LEN = 165
SOL_DECIMAL = 1e9

# Program IDs and authority addresses
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Raydium program addresses
# https://docs.raydium.io/raydium/protocol/developers/addresses
# https://github.com/raydium-io/raydium-sdk-V2/blob/master/src/common/programId.ts
RAYDIUM_MAINNET_CREATE_CPMM_POOL_PROGRAM = Pubkey.from_string("CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C")
RAYDIUM_MAINNET_POOL_AUTHORITY = Pubkey.from_string("GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL")

RAYDIUM_DEVNET_CREATE_CPMM_POOL_PROGRAM = Pubkey.from_string("CPMDWBwJDtYax9qW7AyRuVC19Cc4L4Vcy4n2BHAbHkCW")
RAYDIUM_DEVNET_POOL_AUTHORITY = Pubkey.from_string("7rQ1QFNosMkUCuh7Z7fPbTHvh73b68sQYdirycEzJVuw")

# Add AMM V4 program ID
RAYDIUM_AMM_V4_PROGRAM = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
# Devnet constants
RAYDIUM_DEVNET_AMM_V4 = Pubkey.from_string("HWy1jotHpo6UqeQxx49dpYYdQB8wj9Qk9MdxwjLvDHB8")
OPENBOOK_DEVNET_MARKET = Pubkey.from_string("EoTcMgcDRTJVZDMZWBoU6rhYHZfkNTVEAfz3uUJRcYGj")
RAYDIUM_DEVNET_AUTHORITY = Pubkey.from_string("DbQqP6ehDYmeYjcBaMRuA8tAJY1EjDUz9DpwSLjaQqfC")
FEE_DESTINATION_DEVNET_ID = Pubkey.from_string("3XMrhbv989VxAMi3DErLV9eJht1pHppW5LbKxe9fkEFR")

# Mainnet constants
RAYDIUM_MAINNET_AMM_V4 = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
OPENBOOK_MAINNET_MARKET = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")
RAYDIUM_MAINNET_AUTHORITY = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
FEE_DESTINATION_MAINNET_ID = Pubkey.from_string("7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eqaYcHQqtj2G5")
