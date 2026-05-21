# Set dummy env vars BEFORE any project module is imported.
# pytest loads conftest.py before collecting/importing test files, so this
# guarantees config.py never hits a KeyError during the test run.
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:AAFakeTokenForTesting")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-api03-fake-key-for-testing")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

import db.database as db_module

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """In-memory SQLite DB wired into db.database for the duration of one test."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    original = db_module.async_session_maker
    db_module.async_session_maker = factory
    try:
        yield engine, factory
    finally:
        db_module.async_session_maker = original
        await engine.dispose()
