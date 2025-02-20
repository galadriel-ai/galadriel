from unittest.mock import AsyncMock

import pytest

from galadriel.domain import validate_solana_payment
from galadriel.domain.validate_solana_payment import (
    PaymentValidationError,
    TaskAndPaymentSignature,
    _extract_transaction_signature,
)
from galadriel.domain.validate_solana_payment import TaskAndPaymentSignatureResponse
from galadriel.entities import Message
from galadriel.entities import Pricing


@pytest.fixture
def pricing():
    return Pricing(cost=0.1, wallet_address="HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH")


test_signature = "52rdAHYLiTw2vVJmkyWi2sQesn3dLaPnKrDc9UjySmnBK7qi39DyzTXrdPAPNEeh9b1JvHRB1RLg8RQZVXywDMGE"


async def test_successful_payment_validation(monkeypatch, pricing):
    """Test successful payment validation with valid signature."""
    monkeypatch.setattr(
        validate_solana_payment,
        "_get_sol_amount_transferred",
        AsyncMock(return_value=pricing.cost * 10**9),
    )

    spent_payments = set()
    message = Message(content=f"My task https://solscan.io/tx/{test_signature}")

    result = await validate_solana_payment.execute(pricing, spent_payments, message)

    assert isinstance(result, TaskAndPaymentSignatureResponse)
    assert result.task == "My task"
    assert result.signature == test_signature
    assert test_signature in spent_payments


async def test_reused_signature(pricing):
    """Test validation fails when signature was already used."""
    spent_payments = {test_signature}
    message = Message(content=f"My task https://solscan.io/tx/{test_signature}")

    with pytest.raises(PaymentValidationError) as exc_info:
        await validate_solana_payment.execute(pricing, spent_payments, message)

    assert "already been used" in str(exc_info.value)


async def test_missing_signature(pricing):
    """Test validation fails when no signature is provided."""
    spent_payments = set()
    message = Message(content="My task without signature")

    with pytest.raises(PaymentValidationError) as exc_info:
        await validate_solana_payment.execute(pricing, spent_payments, message)

    assert "No transaction signature found" in str(exc_info.value)


async def test_invalid_payment(monkeypatch, pricing):
    """Test validation fails when payment amount is incorrect."""
    monkeypatch.setattr(
        validate_solana_payment,
        "_get_sol_amount_transferred",
        AsyncMock(return_value=pricing.cost * 10**9 - 1),
    )

    spent_payments = set()
    message = Message(content=f"My task https://solscan.io/tx/{test_signature}")

    with pytest.raises(PaymentValidationError) as exc_info:
        await validate_solana_payment.execute(pricing, spent_payments, message)

    assert "Payment validation failed" in str(exc_info.value)
    assert test_signature not in spent_payments


async def test_signature_extraction_formats(monkeypatch, pricing):
    """Test different signature format extractions."""
    test_cases = [
        f"My task https://solscan.io/tx/{test_signature}",
        f"My task {test_signature}",
        f"My task\n{test_signature}\nmore text",
    ]
    monkeypatch.setattr(
        validate_solana_payment,
        "_get_sol_amount_transferred",
        AsyncMock(return_value=pricing.cost * 10**9),
    )
    for test_case in test_cases:
        spent_payments = set()
        message = Message(content=test_case)

        result = await validate_solana_payment.execute(pricing, spent_payments, message)
        assert isinstance(result, TaskAndPaymentSignatureResponse)
        assert result.signature == test_signature


def test_extract_transaction_signature():
    test_cases = [
        # With solscan URL
        (f"https://solscan.io/tx/{test_signature} - hello", "- hello"),
        (f"hello https://solscan.io/tx/{test_signature}", "hello"),
        (f"hello https://solscan.io/tx/{test_signature} ", "hello"),
        # Raw signature
        (f"{test_signature} - hello", "- hello"),
        (f"hello {test_signature}", "hello"),
        (f"hello {test_signature} ", "hello"),
        # With trailing slash
        (f"https://solscan.io/tx/{test_signature}/ - hello", "- hello"),
        (f"hello https://solscan.io/tx/{test_signature}/", "hello"),
        (f"hello https://solscan.io/tx/{test_signature}/ ", "hello"),
    ]

    for message, expected_task in test_cases:
        result = _extract_transaction_signature(message)
        assert isinstance(result, TaskAndPaymentSignature)
        assert result.signature == test_signature
        assert result.task == expected_task


def test_extract_transaction_signature_invalid_cases():
    invalid_cases = [
        "",  # Empty string
        "Hello world",  # No signature
        "https://solscan.io/tx/",  # Incomplete URL
        "https://solscan.io/tx/invalid_signature",  # Invalid signature
    ]

    for message in invalid_cases:
        result = _extract_transaction_signature(message)
        assert result is None


def test_extract_transaction_signature_preserves_task():
    message = f"How long should I hold my ETH portfolio before selling?\nhttps://solscan.io/tx/{test_signature}"

    result = _extract_transaction_signature(message)
    assert isinstance(result, TaskAndPaymentSignature)
    assert result.signature == test_signature
    assert result.task == "How long should I hold my ETH portfolio before selling?"
