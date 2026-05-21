from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Both set by init_engine(); None until then so tests can inject a different engine.
async_engine: Optional[AsyncEngine] = None
async_session_maker: Optional[sessionmaker] = None


def init_engine(url: str) -> None:
    global async_engine, async_session_maker
    async_engine = create_async_engine(url, echo=False)
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )


async def create_db_and_tables() -> None:
    if async_engine is None:
        raise RuntimeError("Call init_engine() before create_db_and_tables()")
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
