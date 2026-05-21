import asyncio
import logging

from bot.instance import bot, dp
from bot.routers import messages
from config import DATABASE_URL
from db.database import create_db_and_tables, init_engine
import db.models  # noqa: F401 — registers Transaction with SQLModel.metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main() -> None:
    init_engine(DATABASE_URL)
    await create_db_and_tables()
    dp.include_router(messages.router)
    logging.info("OsekZahirBot starting — polling for updates...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
