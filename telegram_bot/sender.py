"""Script for telegram notifications."""

from typing import Dict, Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram_bot.feedback import has_enough_articles
from recommend import get_recommendations


async def send_article_notification(
    bot: Bot,
    chat_id: int,
    article: Dict[str, Any],
    supabase: Any
    ) -> None:
    """Send an article notification message with feedback actions.

    It sends along inline keyboard buttons.
    If sufficient articles remain in the database, ad additional
        "More recommendations" button is included.

    Args:
        bot: Telegram Bot instance used to send the message.
        chat_id: Telegram chat ID where the message will be sent.
        article: Article data containing relevant metadata.
        supabase: Supabase client used to check article availability.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "Interested!",
                callback_data=f"feedback:up:{article['id']}"
                ),
            InlineKeyboardButton(
                "Not interested",
                callback_data=f"feedback:down:{article['id']}"
                ),
            ]
    ]

    if has_enough_articles(supabase, min_count=8):
        keyboard.append([
            InlineKeyboardButton(
                "More recommendations",
                callback_data="recommend_more"
            )
        ])
        
    await bot.send_message(
        chat_id=chat_id,
        text=format_article_message(article),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
        disable_web_page_preview=True,
        
    )


async def send_recommendations_on_demand(
    bot: Bot,
    chat_id: int,
    supabase: Any
    ) -> None:
    """Send an article recommendation message with upon user requests.

    It checks the available recommendation articles and shows maximum two.
    It sends it in one single message.

    Args:
        bot: Telegram Bot instance used to send the message.
        chat_id: Telegram chat ID where the message will be sent.
        supabase: Supabase client used to check article availability.
    """
    recs = get_recommendations(supabase, limit=2)

    if not recs:
        await bot.send_message(chat_id, "No new recommendations yet.")
        return
 
    lines = [format_recommendation_message(article) for article in recs]

    message = (
        "⭐ <b>Recommended for you</b>\n\n"
        + "\n".join(lines)
    )   

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


def format_article_message(article: Dict[str, Any]) -> str:
    """Format the article message.

    Args:
        article: Article data containing relevant metadata.

    Returns:
        Shows the article and its metadata and link as a message output.
    """
    return f"""
<b>{article["title_en"]}</b>

<b>Category:</b> {article["category"]}
<b>Topic:</b> {article["topic"]}
<b>Sentiment:</b> {article["sentiment"]}
<b>Urgency:</b> {article["urgency"]}

<b>Overview:</b>
{article["summary_en"]}

🔗 <a href="{article['article_url']}">Read full article here</a>
""".strip()


def format_recommendation_message(article: Dict[str, Any]) -> str:
    """Format a compact recommendation message.

    Args:
        article: Article data containing relevant metadata.

    Returns:
        [Topic] Title (clickable)
    """
    return (
        f"<b>[{article['topic']}]</b> "
        f"<a href=\"{article['article_url']}\">"
        f"{article['title_en']}"
        f"</a>"
    )