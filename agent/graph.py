import logging

from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from config import ANTHROPIC_API_KEY
from agent.schema import FinancialTransaction
from agent.state import TransactionState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a financial transaction parser for Israeli small business owners (עוסקים זעירים).
Extract structured data from Hebrew, English, or mixed-language messages describing income or expenses.

## Field guide

**transaction_type**
- "income"  → money received:  קיבלתי / שולם לי / הכנסה / חשבונית יצאה / received
- "expense" → money paid out:  שילמתי / הוצאה / רכשתי / קניתי / paid / bought

**amount** (positive float)
- Strip thousands separators: "1,500" → 1500.0
- Translate written Hebrew numbers: "אלף" → 1000, "מאה" → 100, "חמישים" → 50, "חצי" → 0.5
- If the amount is completely absent from the message, use 0.0

**currency** (default "NIS" when not stated)
- ש"ח / שח / שקל / shekel / NIS → "NIS"
- $ / דולר / dollar / USD       → "USD"
- € / יורו / euro / EUR         → "EUR"

**counterparty** — the person or business the money moved to or from
- income:  the client or person who paid you
- expense: the vendor or person you paid to

**description** — 2-5 words naming the service or product

## Few-shot examples

"קיבלתי 500 שח מיוסי על ייעוץ"
→ income | 500.0 NIS | counterparty: יוסי | description: ייעוץ

"שילמתי 120 ש״ח לבזק על חשבון אינטרנט"
→ expense | 120.0 NIS | counterparty: בזק | description: חשבון אינטרנט

"received 1,500 NIS from Acme Ltd for website design"
→ income | 1500.0 NIS | counterparty: Acme Ltd | description: website design

"קניתי ציוד משרדי ב-200 שח בסטימצקי"
→ expense | 200.0 NIS | counterparty: סטימצקי | description: ציוד משרדי

"חשבונית לדוד כהן 3,200 שקל — פרויקט פיתוח אפליקציה"
→ income | 3200.0 NIS | counterparty: דוד כהן | description: פרויקט פיתוח אפליקציה

"paid Amazon $45 for office supplies"
→ expense | 45.0 USD | counterparty: Amazon | description: office supplies

"העברה של אלף וחמש מאות שקל לרואה חשבון על דוחות שנתיים"
→ expense | 1500.0 NIS | counterparty: רואה חשבון | description: דוחות שנתיים

## Rules
- Amount is always positive; transaction_type encodes the direction.
- Extract counterparty even if only a first name is given.
- If the message contains no financial transaction at all, set amount to 0.0.
- Never fabricate fields — use only what the message contains."""

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
