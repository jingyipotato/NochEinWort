# NochEinWort

## Overview

A telegram bot that delivers translated German news article, gathers user feedback, and generates personalized article recommendations.

---

## Architecture 🔧

- A scheduled CI Pipeline (GitHub Actions) periodically runs the content pipeline
- During each run, the system:
  - Scrapes the latest German news article from [Tagesschau](https://www.tagesschau.de)
  - Translates article into English using an LLM
  - Generates concise English summary
  - Classifies article by topic, sentiment, and urgency
- All processed content and metadata are persisted in Supabase
- The Telegram bot notifies users of new article and supports:
  - Feedback collection
  - On-demand article recommendations
- User feedback is later used to curate content in a reading dashboard

---

## Getting Started

### Prerequisites ⚙️

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- [Supabase project](https://supabase.com)
- [Anthropic API Key](https://console.anthropic.com/settings/keys)
- Telegram Bot Token

### Setup 📥

```bash
# Clone the repo
git clone <repo-url>
cd deutsch

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync
```

### Run the API (Telegram Webhook)

1. FastAPI required for Telegram interactions.

```bash
uv run uvicorn app:app
```

2. For local testing with Telegram:

```bash
ngrok http 8000
```

3. Register the webhook:

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<ngrok-url>/telegram/webhook
```

### Run Pipeline Scripts Locally

You can run run each step independently:

```bash
# Discover and store new articles
uv run scrape.py

# Translate, classify and notify Telegram
uv run translate.py
```

### Environment Variables

```bash
# API Key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Supabase Credentials
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Telegram Credentials
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

---

## Project structure 📁

```
deutsch/
├── app.py              # FastAPI application entrypoint
├── scrape.py           # Article discovery from Tagesschau
├── translate.py        # Translation & classification logic / script
├── recommend.py        # Recommendation logic
├── prompts.py          # LLM prompts
├── database/
│   └── client.py       # Supabase client initialization
├── telegram_bot/
│   ├── callback.py     # Telegram callback handler
│   ├── sender.py       # Telegram notification handling
│   └── feedback.py     # Telegram feedback handling
└── utils/
    └── logging.py      # Logging script

```

## Tech stack

| Layer                | Technology                    |
| -------------------- | ----------------------------- |
| Messaging            | Telegram Bot API              |
| Backend API          | FastAPI (Webhook handling)    |
| Backend Jobs         | Github Actions CI/CD          |
| Web Scraping         | Playwright (Chromium)         |
| LLM Processing       | PydanticAI + LLM              |
| Database             | Supabase (PostgreSQL)         |
| Frontend (Upcoming!) | React + Next.js               |
| Infrastructure       | ngrok (Local webhook testing) |

---
