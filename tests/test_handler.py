from unittest.mock import AsyncMock, MagicMock, patch

from bot.routers.messages import handle_any_message


async def test_text_message_invokes_graph_and_replies_with_confirmation():
    mock_message = MagicMock()
    mock_message.text = "קיבלתי 500 שח מיוסי על ייעוץ"
    mock_message.photo = None
    mock_message.document = None
    mock_message.from_user.id = 99999
    mock_message.reply = AsyncMock()

    graph_result = {
        "raw_message": "קיבלתי 500 שח מיוסי על ייעוץ",
        "telegram_user_id": "99999",
        "extracted_data": {
            "transaction_type": "income",
            "amount": 500.0,
            "currency": "NIS",
            "counterparty": "יוסי",
            "description": "ייעוץ",
        },
        "needs_clarification": False,
        "clarification_message": "",
    }

    with patch("bot.routers.messages.transaction_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=graph_result)
        await handle_any_message(mock_message)

    mock_graph.ainvoke.assert_called_once()
    invoked_state = mock_graph.ainvoke.call_args[0][0]
    assert invoked_state["raw_message"] == "קיבלתי 500 שח מיוסי על ייעוץ"
    assert invoked_state["telegram_user_id"] == "99999"

    mock_message.reply.assert_called_once()
    reply_text = mock_message.reply.call_args[0][0]
    assert "✅" in reply_text
    assert "נשמרה בהצלחה" in reply_text
    assert "הכנסה" in reply_text
    assert "500" in reply_text
    assert "יוסי" in reply_text


async def test_text_message_replies_with_clarification():
    mock_message = MagicMock()
    mock_message.text = "שלום"
    mock_message.photo = None
    mock_message.document = None
    mock_message.from_user.id = 77777
    mock_message.reply = AsyncMock()

    clarification = "לא הצלחתי להבין את פרטי העסקה. נסה שוב."

    graph_result = {
        "raw_message": "שלום",
        "telegram_user_id": "77777",
        "extracted_data": {},
        "needs_clarification": True,
        "clarification_message": clarification,
    }

    with patch("bot.routers.messages.transaction_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=graph_result)
        await handle_any_message(mock_message)

    mock_message.reply.assert_called_once_with(clarification)


async def test_photo_message_skips_graph_and_sends_placeholder():
    mock_message = MagicMock()
    mock_message.text = None
    mock_message.photo = [MagicMock(file_id="abc123")]
    mock_message.document = None
    mock_message.from_user.id = 55555
    mock_message.reply = AsyncMock()

    with patch("bot.routers.messages.transaction_graph") as mock_graph:
        await handle_any_message(mock_message)

    mock_graph.ainvoke.assert_not_called()
    mock_message.reply.assert_called_once()
    assert "תמונה" in mock_message.reply.call_args[0][0]
