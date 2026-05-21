from typing import TypedDict


class TransactionState(TypedDict):
    raw_message: str
    telegram_user_id: str
    extracted_data: dict
    needs_clarification: bool
    clarification_message: str
