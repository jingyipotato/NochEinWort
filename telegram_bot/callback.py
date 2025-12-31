"""Telegram callback handler."""

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.feedback import handle_thumbs_down, handle_thumbs_up
from telegram_bot.sender import send_recommendations_on_demand
from utils.logging import get_logger

logger = get_logger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Callback Handler fired!")
    query = update.callback_query
    await query.answer()

    supabase = context.bot_data["supabase"]

    try:
        data = query.data
        supabase = context.bot_data["supabase"]
        chat_id = query.message.chat_id if query.message else query.from_user.id

    except (ValueError, KeyError, TypeError) as e:
        context.application.logger.error(e)
        await query.message.reply_text("Something went wrong. Please try again.")
        return

    if data.startswith("feedback"):
        _, value, article_id = data.split(":")
        article_id = int(article_id)

        row = (
            supabase
            .table("deutsch")
            .select("title_en")
            .eq("id", article_id)
            .single()
            .execute()
        ).data

        title = row["title_en"]

        if value == "up":
            handle_thumbs_up(supabase, article_id)
            await query.message.reply_text(f"<b>Saved:</b> {title}",
                                           parse_mode="HTML")
        else:
            handle_thumbs_down(supabase, article_id)
            await query.message.reply_text(f"<b>Not saved:</b> {title}",
                                           parse_mode="HTML")

    elif data == "recommend_more":
        await send_recommendations_on_demand(
            bot=context.bot,
            chat_id=chat_id,
            supabase=supabase
        )

    else:
        raise ValueError(f"Unknown callback data: {data}")