import pytest
from unittest.mock import MagicMock

from galadriel.domain import validate_solana_payment
from galadriel.domain.validate_solana_payment import (
    TaskAndPaymentSignature,
    PaymentValidationError,
)
from galadriel.entities import Message, Pricing


@pytest.fixture
def pricing():
    return Pricing(
        cost=0.1, wallet_address="HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
    )


def test_successful_payment_validation(monkeypatch, pricing):
    """Test successful payment validation with valid signature."""
    monkeypatch.setattr(
        validate_solana_payment,
        "_validate_solana_payment",
        MagicMock(return_value=True),
    )

    spent_payments = set()
    message = Message(content="My task https://solscan.io/tx/valid_signature123")

    result = validate_solana_payment.execute(pricing, spent_payments, message)

    assert isinstance(result, TaskAndPaymentSignature)
    assert result.task == "My task"
    assert result.signature == "valid_signature123"
    assert "valid_signature123" in spent_payments


def test_reused_signature(pricing):
    """Test validation fails when signature was already used."""
    spent_payments = {"used_signature123"}
    message = Message(content="My task https://solscan.io/tx/used_signature123")

    with pytest.raises(PaymentValidationError) as exc_info:
        validate_solana_payment.execute(pricing, spent_payments, message)

    assert "already been used" in str(exc_info.value)


def test_missing_signature(pricing):
    """Test validation fails when no signature is provided."""
    spent_payments = set()
    message = Message(content="My task without signature")

    with pytest.raises(PaymentValidationError) as exc_info:
        validate_solana_payment.execute(pricing, spent_payments, message)

    assert "No transaction signature found" in str(exc_info.value)


def test_invalid_payment(monkeypatch, pricing):
    """Test validation fails when payment amount is incorrect."""
    monkeypatch.setattr(
        validate_solana_payment,
        "_validate_solana_payment",
        MagicMock(return_value=False),
    )

    spent_payments = set()
    message = Message(content="My task https://solscan.io/tx/invalid_payment123")

    with pytest.raises(PaymentValidationError) as exc_info:
        validate_solana_payment.execute(pricing, spent_payments, message)

    assert "Payment validation failed" in str(exc_info.value)
    assert "invalid_payment123" not in spent_payments


def test_signature_extraction_formats(monkeypatch, pricing):
    """Test different signature format extractions."""
    test_cases = [
        "My task https://solscan.io/tx/2pcaEXQGhg9fRcMxQ3bj1La31em3fNynnTF5y1WodE56zxcvcqK3SnBjok8eYHajCJ6DxsjfrpEqtCdrEk2cxQ1Z",
        "My task 2pcaEXQGhg9fRcMxQ3bj1La31em3fNynnTF5y1WodE56zxcvcqK3SnBjok8eYHajCJ6DxsjfrpEqtCdrEk2cxQ1Z",
        "2pcaEXQGhg9fRcMxQ3bj1La31em3fNynnTF5y1WodE56zxcvcqK3SnBjok8eYHajCJ6DxsjfrpEqtCdrEk2cxQ1Z My task",
        "My task\n2pcaEXQGhg9fRcMxQ3bj1La31em3fNynnTF5y1WodE56zxcvcqK3SnBjok8eYHajCJ6DxsjfrpEqtCdrEk2cxQ1Z\nmore text",
    ]
    monkeypatch.setattr(
        validate_solana_payment,
        "_validate_solana_payment",
        MagicMock(return_value=True),
    )
    for test_case in test_cases:
        spent_payments = set()
        message = Message(content=test_case)

        result = validate_solana_payment.execute(pricing, spent_payments, message)
        assert isinstance(result, TaskAndPaymentSignature)
        assert (
            "2pcaEXQGhg9fRcMxQ3bj1La31em3fNynnTF5y1WodE56zxcvcqK3SnBjok8eYHajCJ6DxsjfrpEqtCdrEk2cxQ1Z"
            in result.signature
        )
