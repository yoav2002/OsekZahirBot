import pytest
from pydantic import ValidationError

from agent.schema import FinancialTransaction


def test_valid_income_defaults_currency_to_nis():
    t = FinancialTransaction(
        transaction_type="income",
        amount=500.0,
        counterparty="יוסי כהן",
        description="ייעוץ עסקי",
    )
    assert t.currency == "NIS"
    assert t.transaction_type == "income"


def test_valid_expense_with_explicit_currency():
    t = FinancialTransaction(
        transaction_type="expense",
        amount=120.0,
        currency="USD",
        counterparty="Amazon",
        description="תוכנה",
    )
    assert t.currency == "USD"


def test_negative_amount_raises():
    with pytest.raises(ValidationError, match="amount must be positive"):
        FinancialTransaction(
            transaction_type="income",
            amount=-100.0,
            counterparty="יוסי",
            description="ייעוץ",
        )


def test_zero_amount_raises():
    with pytest.raises(ValidationError):
        FinancialTransaction(
            transaction_type="expense",
            amount=0.0,
            counterparty="בזק",
            description="אינטרנט",
        )


def test_invalid_transaction_type_raises():
    with pytest.raises(ValidationError):
        FinancialTransaction(
            transaction_type="transfer",  # not in Literal["income","expense"]
            amount=200.0,
            counterparty="מישהו",
            description="משהו",
        )


def test_missing_amount_raises():
    with pytest.raises(ValidationError):
        FinancialTransaction(
            transaction_type="income",
            counterparty="יוסי",
            description="ייעוץ",
        )


def test_missing_counterparty_raises():
    with pytest.raises(ValidationError):
        FinancialTransaction(
            transaction_type="income",
            amount=300.0,
            description="ייעוץ",
        )
