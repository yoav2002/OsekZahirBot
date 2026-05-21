from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FinancialTransaction(BaseModel):
    transaction_type: Literal["income", "expense"]
    amount: float
    currency: str = Field(default="NIS")
    counterparty: str
    description: str

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"amount must be positive, got {v}")
        return v
