from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from agent.graph import extract_transaction
from agent.schema import FinancialTransaction
from agent.state import TransactionState

_BASE_STATE: TransactionState = {
    "raw_message": "",
    "telegram_user_id": "12345",
    "extracted_data": {},
    "needs_clarification": False,
    "clarification_message": "",
}


async def test_extract_transaction_success():
    mock_result = FinancialTransaction(
        transaction_type="income",
        amount=500.0,
        counterparty="יוסי",
        description="ייעוץ עסקי",
    )
    state = {**_BASE_STATE, "raw_message": "קיבלתי 500 שח מיוסי על ייעוץ"}

    with patch("agent.graph.ChatAnthropic") as MockModel:
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_result)
        MockModel.return_value.with_structured_output.return_value = mock_chain

        result = await extract_transaction(state)

    assert result["needs_clarification"] is False
    assert result["extracted_data"]["amount"] == 500.0
    assert result["extracted_data"]["transaction_type"] == "income"
    assert result["extracted_data"]["counterparty"] == "יוסי"
    assert result["clarification_message"] == ""


async def test_extract_transaction_validation_error_sets_clarification():
    # Build a real ValidationError by omitting all required fields.
    # Pydantic will emit "missing" errors for amount, counterparty, description.
    try:
        FinancialTransaction(transaction_type="bad_type")  # type: ignore[call-arg]
    except ValidationError as exc:
        fake_exc = exc

    state = {**_BASE_STATE, "raw_message": "שלום"}

    with patch("agent.graph.ChatAnthropic") as MockModel:
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=fake_exc)
        MockModel.return_value.with_structured_output.return_value = mock_chain

        result = await extract_transaction(state)

    assert result["needs_clarification"] is True
    assert result["clarification_message"] != ""
    assert result["extracted_data"] == {}


async def test_extract_transaction_unexpected_error_sets_clarification():
    state = {**_BASE_STATE, "raw_message": "..."}

    with patch("agent.graph.ChatAnthropic") as MockModel:
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("API down"))
        MockModel.return_value.with_structured_output.return_value = mock_chain

        result = await extract_transaction(state)

    assert result["needs_clarification"] is True
    assert "שגיאה" in result["clarification_message"]
