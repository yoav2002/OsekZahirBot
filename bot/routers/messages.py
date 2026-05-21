import logging

from aiogram import Router
from aiogram.types import Message

from agent.graph import transaction_graph
from agent.state import TransactionState

logger = logging.getLogger(__name__)
router = Router(name="messages")


def _format_confirmation(data: dict) -> str:
    tx_type = "הכנסה" if data["transaction_type"] == "income" else "הוצאה"
    preposition = "מ" if data["transaction_type"] == "income" else "ל"
    amount = data["amount"]
    currency = data.get("currency", "NIS")
    counterparty = data["counterparty"]
    description = data["description"]
    return (
        f"✅ {tx_type} על סך {amount:g} {currency} "
        f"{preposition}{counterparty} ({description}) נשמרה בהצלחה!"
    )


@router.message()
async def handle_any_message(message: Message) -> None:
    sender_id = message.from_user.id if message.from_user else "unknown"

    if message.text:
        logger.info("Text from %s: %s", sender_id, message.text)

        initial_state: TransactionState = {
            "raw_message": message.text,
            "telegram_user_id": str(sender_id),
            "extracted_data": {},
            "needs_clarification": False,
            "clarification_message": "",
        }
        result = await transaction_graph.ainvoke(initial_state)

        if result["needs_clarification"]:
            await message.reply(result["clarification_message"])
        else:
            await message.reply(_format_confirmation(result["extracted_data"]))

    elif message.photo:
        logger.info("Photo from %s: file_id=%s", sender_id, message.photo[-1].file_id)
        await message.reply("קיבלתי את התמונה. עיבוד קבצים יוטמע בקרוב!")

    elif message.document:
        logger.info(
            "Document from %s: name=%s file_id=%s",
            sender_id,
            message.document.file_name,
            message.document.file_id,
        )
        await message.reply("קיבלתי את המסמך. עיבוד קבצים יוטמע בקרוב!")

    else:
        logger.info("Message type=%s from %s", message.content_type, sender_id)
        await message.reply("סוג הודעה זה אינו נתמך עדיין.")
