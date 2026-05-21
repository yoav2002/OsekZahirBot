import logging

from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from config import ANTHROPIC_API_KEY
from agent.schema import FinancialTransaction
from agent.state import TransactionState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """אתה עוזר פיננסי לבעלי עסקים קטנים בישראל (עוסקים זעירים).
תפקידך לנתח הודעות בעברית או בשפה מעורבת ולחלץ מהן פרטי עסקה פיננסית.
חלץ: סוג עסקה (income/expense), סכום, מטבע (ברירת מחדל NIS), שם הצד השני, ותיאור.
אם המטבע לא צוין, השתמש ב-NIS."""

_MISSING_FIELD_LABELS = {
    "transaction_type": 'סוג העסקה (הכנסה או הוצאה)',
    "amount": 'הסכום בש"ח',
    "counterparty": "שם הצד השני (מי ששילם לך, או מי ששילמת לו)",
    "description": "תיאור השירות או המוצר",
}


async def extract_transaction(state: TransactionState) -> dict:
    model = ChatAnthropic(model="claude-sonnet-4-6", api_key=ANTHROPIC_API_KEY)
    structured = model.with_structured_output(FinancialTransaction)

    messages = [
        ("system", _SYSTEM_PROMPT),
        ("human", state["raw_message"]),
    ]

    try:
        result: FinancialTransaction = await structured.ainvoke(messages)
        logger.info("Parsed transaction: %s", result.model_dump())
        return {
            "extracted_data": result.model_dump(),
            "needs_clarification": False,
            "clarification_message": "",
        }
    except ValidationError as exc:
        missing = [
            _MISSING_FIELD_LABELS.get(str(err["loc"][0]), str(err["loc"][0]))
            for err in exc.errors()
            if err.get("type") in ("missing", "value_error", "none_required")
        ]
        if missing:
            msg = f"לא הצלחתי להבין את כל הפרטים. האם תוכל להוסיף: {', '.join(missing)}?"
        else:
            msg = (
                "לא הצלחתי לנתח את ההודעה. "
                'נסה לנסח כך: "קיבלתי 500 שח מיוסי על ייעוץ" '
                'או "שילמתי 120 שח לבזק על אינטרנט".'
            )
        logger.warning("ValidationError parsing transaction: %s", exc)
        return {"extracted_data": {}, "needs_clarification": True, "clarification_message": msg}
    except Exception as exc:
        logger.error("Unexpected error in extract_transaction: %s", exc, exc_info=True)
        return {
            "extracted_data": {},
            "needs_clarification": True,
            "clarification_message": "אירעה שגיאה בעיבוד ההודעה. אנא נסה שוב.",
        }


async def save_to_database(state: TransactionState) -> dict:
    # Late import so tests can patch db.database.async_session_maker freely.
    import db.database as _db
    from db.models import Transaction

    if _db.async_session_maker is None:
        logger.error("Database not initialised — skipping persist (call init_engine first)")
        return {}

    transaction = Transaction(
        telegram_user_id=state["telegram_user_id"],
        **state["extracted_data"],
    )
    try:
        async with _db.async_session_maker() as session:
            session.add(transaction)
            await session.commit()
            logger.info("Saved transaction id=%s", transaction.id)
    except Exception as exc:
        logger.error("DB insert failed: %s", exc, exc_info=True)

    return {}


def _route_after_extract(state: TransactionState) -> str:
    return END if state["needs_clarification"] else "save_to_database"


def _build_graph():
    builder = StateGraph(TransactionState)
    builder.add_node("extract_transaction", extract_transaction)
    builder.add_node("save_to_database", save_to_database)
    builder.set_entry_point("extract_transaction")
    builder.add_conditional_edges("extract_transaction", _route_after_extract)
    builder.add_edge("save_to_database", END)
    return builder.compile()


transaction_graph = _build_graph()
