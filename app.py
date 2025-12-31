"""FastAPI application factory."""

import os
import json
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler
from dotenv import load_dotenv

from utils.logging import get_logger
from telegram_bot.callback import handle_callback
from database.client import get_supabase_client

logger = get_logger(__name__)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = "/telegram/webhook"

app = FastAPI()

# Create python tele bot application
news_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Initialize supabase client
supabase = get_supabase_client()

news_app.bot_data["supabase"] = supabase

# Register handlers
news_app.add_handler(CallbackQueryHandler(handle_callback))


@app.on_event("startup")
async def startup_event():
    # Initialize and start the telegram Application so it can process updates from the queue
    await news_app.initialize()
    await news_app.bot.initialize()
    await news_app.start()

    logger.info("Telegram Application started and ready to process updates")


@app.on_event("shutdown")
async def shutdown_event():
    # Stop and shutdown the telegram Application gracefully
    await news_app.stop()
    await news_app.shutdown()

    logger.info("Telegram Application stopped")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get(WEBHOOK_PATH)
async def webhook_get():
    # Quick manual check to ensure the public endpoint is reachable
    return {"ok": True}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):

    body_bytes = await req.body()
    client_ip = req.client.host if req.client else "unknown"
    logger.info("Incoming webhook request from %s headers=%s body=%s", client_ip, dict(req.headers), body_bytes.decode("utf-8", errors="replace"))

    if not body_bytes:
        # Health check / empty payload
        return {"ok": True}

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError:
        # Not JSON or empty body
        return {"ok": True}

    # PTB needs structured Update object instead of raw dicts
    update = Update.de_json(data, news_app.bot)
    if update is None:
        # Invalid or unsupported Tele payload
        return {"ok": True}

    await news_app.process_update(update)
    return {"ok": True} 