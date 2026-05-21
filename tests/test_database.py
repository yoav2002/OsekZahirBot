import pytest
from sqlalchemy import select

from agent.graph import save_to_database
from agent.state import TransactionState
from db.models import Transaction


async def test_save_to_database_inserts_row(test_db):
    _, factory = test_db

    state: TransactionState = {
        "raw_message": "קיבלתי 500 שח מיוסי",
        "telegram_user_id": "42",
        "extracted_data": {
            "transaction_type": "income",
            "amount": 500.0,
            "currency": "NIS",
            "counterparty": "יוסי",
            "description": "ייעוץ",
        },
        "needs_clarification": False,
        "clarification_message": "",
    }

    await save_to_database(state)

    async with factory() as session:
        result = await session.execute(select(Transaction))
        rows = result.scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.telegram_user_id == "42"
    assert row.amount == 500.0
    assert row.transaction_type == "income"
    assert row.counterparty == "יוסי"
    assert row.currency == "NIS"
    assert row.receipt_url is None


async def test_save_to_database_sets_id_and_created_at(test_db):
    _, factory = test_db

    state: TransactionState = {
        "raw_message": "שילמתי 120 שח לבזק",
        "telegram_user_id": "99",
        "extracted_data": {
            "transaction_type": "expense",
            "amount": 120.0,
            "currency": "NIS",
            "counterparty": "בזק",
            "description": "אינטרנט",
        },
        "needs_clarification": False,
        "clarification_message": "",
    }

    await save_to_database(state)

    async with factory() as session:
        result = await session.execute(select(Transaction))
        rows = result.scalars().all()

    assert rows[0].id is not None
    assert rows[0].created_at is not None


async def test_save_skips_when_session_maker_is_none():
    """save_to_database must not crash when the DB has not been initialised."""
    import db.database as _db

    original = _db.async_session_maker
    _db.async_session_maker = None
    try:
        state: TransactionState = {
            "raw_message": "test",
            "telegram_user_id": "1",
            "extracted_data": {
                "transaction_type": "income",
                "amount": 1.0,
                "currency": "NIS",
                "counterparty": "x",
                "description": "y",
            },
            "needs_clarification": False,
            "clarification_message": "",
        }
        result = await save_to_database(state)  # should return {} without raising
        assert result == {}
    finally:
        _db.async_session_maker = original
