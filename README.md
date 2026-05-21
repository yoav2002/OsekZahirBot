# OsekZahirBot

A Telegram bot backend for Israeli small business owners (Osek Za'ir) to log income and expenses via messaging apps.

## Current Phase

Phase 1 — Telegram integration only. The bot receives messages (text, photos, documents) and replies with a placeholder confirmation while the parsing and storage layers are built out.

## Project Structure

```
.
├── main.py              # Entry point — starts async polling
├── config.py            # Loads environment variables
├── requirements.txt
├── .env.example
└── bot/
    ├── instance.py      # Bot and Dispatcher singletons
    └── routers/
        └── messages.py  # Handles all incoming message types
```

## Setup

### 1. Create a bot via BotFather

Open Telegram, start a chat with [@BotFather](https://t.me/BotFather), and run `/newbot`. Copy the token it gives you.

### 2. Clone and install dependencies

```bash
git clone <repo-url>
cd OsekZahirBot

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your token:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 4. Run the bot

```bash
python main.py
```

The bot will start polling. Open a chat with your bot in Telegram and send any message — you should see the console log and receive:

> קיבלתי את ההודעה, המערכת בשלבי פיתוח!

## Message Types Handled

| Type | Logged info |
|------|-------------|
| Text | Sender ID + message text |
| Photo | Sender ID + highest-resolution `file_id` |
| Document | Sender ID + filename + `file_id` |
| Other | Sender ID + `content_type` |

## Roadmap

- [ ] LangGraph pipeline to parse Hebrew income/expense messages
- [ ] Structured storage layer (PostgreSQL / Supabase)
- [ ] Web dashboard for reviewing logged transactions
- [ ] Webhook mode for production deployment
