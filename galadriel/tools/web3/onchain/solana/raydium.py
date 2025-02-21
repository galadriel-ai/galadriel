
"""
Raydium AMM V4 Integration Module

This module provides tools for interacting with Raydium's Automated Market Maker (AMM) V4
on the Solana blockchain. It enables token swaps using SOL as the base currency.

Key Features:
- Buy tokens with SOL
- Sell tokens for SOL
- AMM pool interaction
- Price calculation with slippage protection
"""

# pylint: disable=R0801
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
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore # pylint: disable=E0401
from solders.message import MessageV0  # type: ignore # pylint: disable=E0401
from solders.keypair import Keypair  # type: ignore # pylint: disable=E0401
from solders.pubkey import Pubkey  # type: ignore # pylint: disable=E0401
from solders.signature import Signature  # type: ignore # pylint: disable=E0401
from solders.instruction import AccountMeta, Instruction  # type: ignore # pylint: disable=E0401
from solders.transaction import VersionedTransaction  # type: ignore # pylint: disable=E0401
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)
from spl.token.client import Token
from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)

from galadriel.tools.web3.onchain.solana.base_tool import SolanaBaseTool
from galadriel.wallets.solana_wallet import SolanaWallet
from galadriel.logging_utils import get_agent_logger, init_logging
from galadriel.utils.raydium.openbook import buy as openbook_buy, sell as openbook_sell
from galadriel.utils.raydium.cpmm import buy as cpmm_buy, sell as cpmm_sell
from galadriel.utils.raydium.constants import WSOL


logger = get_agent_logger()


class TokenSwapTool(SolanaBaseTool):
    """Tool for swapping tokens using Raydium."""

    name = "swap_token"
    description = "Swap tokens using Raydium"
    inputs = {
        "pair_address": {"type": "string", "description": "The Raydium OpenBook pair address"},
        "token_in": {"type": "string", "description": "The input token address"},
        "token_out": {"type": "string", "description": "The output token address"},
        "input_amount": {
            "type": "number",
            "description": "Amount of input token to swap",
        },
        "slippage": {
            "type": "number",
            "description": "Slippage tolerance percentage",
            "default": 5,
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, wallet: SolanaWallet):
        super().__init__(wallet)

    def forward(self, pair_address: str, token_in: str, token_out: str, input_amount: float, slippage: int = 5) -> Optional[str]:
        """Buy tokens with SOL.

        Args:
            pair_address (str): The Raydium OpenBook pair address
            network (str): The network to use (mainnet or devnet)
            sol_in (float, optional): Amount of SOL to swap. Defaults to 0.1
            slippage (int, optional): Slippage tolerance percentage. Defaults to 1

        Returns:
            Optional[str]: Transaction signature if successful, None otherwise
        """
        keypair = self.wallet.get_wallet()
        if token_in == WSOL:
            # Buy token with SOL using OpenBook 
            logger.info(f"Buying {token_out} with SOL using OpenBook")
            res = openbook_buy(
                client=self.client,
                network=self.network,
                payer_keypair=keypair,
                pair_address=pair_address,
                sol_in=input_amount,
                slippage=slippage,
            )
            if res:
                return res
            else:
                # If the OpenBook buy fails, try CPMM 
                logger.info("Buy with openbook failed. Trying CPMM.")
                res = cpmm_buy(
                    client=self.client,
                    network=self.network,
                    payer_keypair=keypair,
                    pair_address=pair_address,
                    sol_in=input_amount,
                    slippage=slippage,
                )

                if res:
                    logger.info(f"Successfully bought {token_out} with SOL using CPMM")
                    return res
                else:
                    logger.error(f"Failed to buy {token_out} with SOL using CPMM")
                    return None



        elif token_out == WSOL:
            res = openbook_sell(
                client=self.client,
                network=self.network,
                payer_keypair=keypair,
                pair_address=pair_address,
                amount_in=input_amount,
                slippage=slippage,
            )
            if res:
                return res
            else:
                logger.error(f"Failed to sell {token_in} for SOL using OpenBook, trying CPMM.")
                res = cpmm_sell(
                    client=self.client,
                    network=self.network,
                    payer_keypair=keypair,
                    pair_address=pair_address,
                    amount_in=input_amount,
                    slippage=slippage,
                )

                if res:
                    logger.info(f"Successfully sold {token_in} for SOL using CPMM")
                    return res
                else:
                    logger.error(f"Failed to sell {token_in} for SOL using CPMM")
                    return None

        else:
            logger.error(f"Unsupported token pair: {token_in} -> {token_out}. Only WSOL pairs are supported.")
            return None


if __name__ == "__main__":
    init_logging(False)
    wallet = SolanaWallet(key_path=os.getenv("SOLANA_KEY_PATH"))
    swap_tool = TokenSwapTool(wallet)
    res = swap_tool.forward("J3b6dvheS2Y1cbMtVz5TCWXNegSjJDbUKxdUVDPoqmS7", "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump", WSOL, 0.0001, 10)


