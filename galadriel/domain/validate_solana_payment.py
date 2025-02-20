from dataclasses import dataclass
import re
import time
from typing import List, Optional, Set

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey  # pylint: disable=E0401
from solders.signature import Signature  # pylint: disable=E0401

from galadriel.entities import Message
from galadriel.entities import Pricing
from galadriel.errors import PaymentValidationError


@dataclass
class TaskAndPaymentSignature:
    task: str
    signature: str


@dataclass
class TaskAndPaymentSignatureResponse(TaskAndPaymentSignature):
    amount_transferred_lamport: int


class SolanaPaymentValidator:
    def __init__(self, pricing: Pricing):
        self.pricing = pricing
        self.existing_payments: Set[str] = set()
        self.http_client = AsyncClient("https://api.mainnet-beta.solana.com")

    async def execute(self, request: Message) -> TaskAndPaymentSignatureResponse:
        """Validate the payment for the request.
            Args:
            pricing: Pricing configuration, containing the wallet address and payment amount required
            existing_payments: Already validated payments to avoid duplications
            request: The message containing the transaction signature
        Returns:
            The task to be executed
        Raises:
            PaymentValidationError: If the payment validation fails
        """
        task_and_payment = _extract_transaction_signature(request.content)
        if not task_and_payment:
            raise PaymentValidationError(
                "No transaction signature found in the message. Please include your payment transaction signature."
            )
        if task_and_payment.signature in self.existing_payments:
            raise PaymentValidationError(
                f"Transaction {task_and_payment.signature} has already been used. Please submit a new payment."
            )
        sol_transferred_lamport = await self._get_sol_amount_transferred(task_and_payment.signature)
        if sol_transferred_lamport < self.pricing.cost * 10**9:
            raise PaymentValidationError(
                f"Payment validation failed for transaction {task_and_payment.signature}. "
                f"Please ensure you've sent {self.pricing.cost} SOL to {self.pricing.wallet_address}"
            )
        self.existing_payments.add(task_and_payment.signature)
        return TaskAndPaymentSignatureResponse(
            task=task_and_payment.task,
            signature=task_and_payment.signature,
            amount_transferred_lamport=sol_transferred_lamport,
        )

    async def _get_sol_amount_transferred(self, tx_signature: str) -> int:
        """
        Get the amount of SOL transferred in lamports for the given transaction signature.
        This function includes a retry mechanism with exponential backoff to handle RPC rate limits.
        """
        tx_sig = Signature.from_string(tx_signature)
        max_retries = 3
        delay = 1.0  # initial delay in seconds

        for attempt in range(max_retries):
            try:
                tx_info = await self.http_client.get_transaction(tx_sig=tx_sig, max_supported_transaction_version=10)
                break  # Successful call, exit the retry loop.
            except Exception as e:
                # If we've not reached the final attempt, wait and retry.
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff.
                else:
                    raise PaymentValidationError(
                        f"RPC error on transaction validation: {str(e)}. "
                        f"Consider switching to an RPC endpoint with higher rate limits."
                    )
        # If the transaction data is not available, return 0.
        if not tx_info.value:
            return 0

        transaction = tx_info.value.transaction.transaction  # The actual transaction
        account_keys = transaction.message.account_keys  # type: ignore
        index = _get_key_index(account_keys, self.pricing.wallet_address)  # type: ignore
        if index < 0:
            return 0

        meta = tx_info.value.transaction.meta
        if meta.err is not None:  # type: ignore
            return 0

        pre_balance = meta.pre_balances[index]  # type: ignore
        post_balance = meta.post_balances[index]  # type: ignore
        amount_sent = post_balance - pre_balance
        return amount_sent


def _get_key_index(account_keys: List[Pubkey], wallet_address: str) -> int:
    """
    Returns the index of the wallet address
    :param account_keys:
    :param wallet_address:
    :return: non-zero number if present, -1 otherwise
    """
    wallet_key = Pubkey.from_string(wallet_address)
    for i, key in enumerate(account_keys):
        if wallet_key == key:
            return i
    return -1


def _extract_transaction_signature(message: str) -> Optional[TaskAndPaymentSignature]:
    """
    Given a string, parses it to extract the task text and the Solana transaction signature.

    For example:
      "How long should I hold my ETH portfolio before selling?
       https://solscan.io/tx/5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"

    :param message: Input string containing the task and the transaction signature.
    :return: TaskAndPaymentSignature if a valid signature is found, otherwise None.
    """
    if not message:
        return None

    # Regex pattern to capture a valid Solana transaction signature,
    # with an optional URL prefix and trailing slash.
    pattern = re.compile(
        r"(?:https?://solscan\.io/tx/)?"  # Optional URL prefix
        r"([1-9A-HJ-NP-Za-km-z]{87,88})"  # Capture group for the signature (base58, typical length 87-88)
        r"(?:/)?"  # Optional trailing slash
    )

    try:
        match = pattern.search(message)
        if match:
            signature = match.group(1)
            # Validate and normalize the signature using solana's Signature class.
            valid_signature = str(Signature.from_string(signature))
            task = message.replace(match.group(0), "").strip()
            return TaskAndPaymentSignature(task=task, signature=valid_signature)
    except Exception:
        pass
    return None
