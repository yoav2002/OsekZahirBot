from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Transaction(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    telegram_user_id: str = Field(index=True)
    transaction_type: str  # "income" | "expense" — enforced by FinancialTransaction before insert
    amount: float
    currency: str = Field(default="NIS")
    counterparty: str
    description: str
    receipt_url: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
