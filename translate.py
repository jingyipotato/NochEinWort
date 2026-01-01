"""Script for translating German to English article."""

import os
import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from telegram import Bot

import prompts
from utils.logging import get_logger
from telegram_bot.sender import send_article_notification
from scrape import process_one_article_status
from database.client import get_supabase_client

logger = get_logger(__name__)
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
supabase = get_supabase_client()

class Translation(BaseModel):
    title_en: str
    content_en: str
    summary_en: str


class Classification(BaseModel):
    topic: str
    sentiment: str
    urgency: str


model = AnthropicModel(
    "claude-sonnet-4-5",
    provider=AnthropicProvider(api_key=ANTHROPIC_API_KEY)
)

translator = Agent(
    model=model,
    output_type=Translation,
    system_prompt=prompts.TRANSLATOR_AGENT_PROMPT
    )

classifier = Agent(
    model=model,
    output_type=Classification,
    system_prompt=prompts.CLASSIFICATION_AGENT_PROMPT
    )


async def translate_and_summarize(
    title_de: str,
    content_de: str,
    ) -> Translation:
    """Translates a German news article into English and generate a short summary.

    Args:
        title_de: Original German article title.
        content_de: Original German article content.

    Returns:
        The English title, translated content and a short English summary.
    """
    prompt = prompts.TRANSLATOR_PROMPT.format(
        title_de=title_de,
        content_de=content_de
    )
    run = await translator.run(prompt)
    return run.output


async def translate_step(article: Dict[str, Any]) -> Translation:
    """Translate and summarize a scraped German article.

    A thin wrapper around `translate_and_summarize` that extracts
        required fields from a database article record.

    Args:
        article: Article record containing `title_en` and `content_de` fields.

    Returns:
        Translated article and summary in English.
    """
    return await translate_and_summarize(
        article["title_de"],
        article["content_de"],
    )


async def classify_article(
    title_en: str,
    content_en: str,
    ) -> Classification:
    """Classifies a German news article with topic, sentiment and urgency.

    Args:
        title_en: Translated English article title.
        content_en: Translated English article content.

    Returns:
        The classified topic, sentiment and urgency values based on article content.
    """
    prompt = prompts.CLASSIFICATION_PROMPT.format(
        title_en=title_en,
        content_en=content_en
    )
    run = await classifier.run(prompt)
    return run.output


async def classify_step(translation: Translation) -> Classification:
    """Classifies the translated article into categories.

    A thin wrapper around `classify_article` that extracts
        required fields from a database article record.

    Args:
        translation: The translated article and summary in English.

    Returns:
        Classified article in English.
    """
    return await classify_article(
        translation.title_en,
        translation.content_en,
    )


def save_translation_and_classification(
    article_id: int,
    translation: Translation,
    classification: Classification,
    ) -> None:
    """Updates the database with translated article's metadata.

    Args:
        article_id: The article ID being translated and classified.
        translation: The English title, translated content and a short English summary.
        classification: The classified topic, sentiment and urgency values based on article content.
    """
    supabase.table("deutsch").update({
        "title_en": translation.title_en,
            "content_en": translation.content_en,
            "summary_en": translation.summary_en,
            "topic": classification.topic,
            "sentiment": classification.sentiment,
            "urgency": classification.urgency,
            "status": "translated",
        }).eq("id", article_id).execute() 


async def process_steps() -> None:
    """Process scraped articles through translation, classification and notification."""

    while True:
        article = process_one_article_status("scrapped", "translating")
        if not article:
            break

        logger.info("Translating and classifying article...")
        try:
            translation = await translate_step(article)
            classification = await classify_step(translation)
            save_translation_and_classification(article["id"], translation, classification)

            logger.info("Article updated and saved in db.")

            row = (
                supabase.table("deutsch")
                .select("id, article_url, title_en, summary_en, topic, sentiment, urgency, category")
                .eq("id", article["id"])
                .single()
                .execute()
            ).data

            await send_article_notification(
                bot=bot,
                chat_id=TELEGRAM_CHAT_ID,
                article=row,
                supabase=supabase
            )

            logger.info(f"Notified to telegram user: {article['article_url']}")

        except (ValidationError, RuntimeError) as e:
            logger.exception(f"LLM failure: {e}")
            supabase.table("deutsch").update({
                "status": "failed"
            }).eq("id", article["id"]).execute()


if __name__ == "__main__":
    asyncio.run(process_steps())