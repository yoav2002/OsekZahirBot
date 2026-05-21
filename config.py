import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
# Optional: defaults to a local Postgres DB so tests can omit this var
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://localhost/osekzahir"
)
