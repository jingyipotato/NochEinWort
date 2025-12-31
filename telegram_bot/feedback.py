"""Script for handling telegram feedbacks."""

from typing import Any
from datetime import datetime, timezone


def handle_thumbs_up(
    supabase: Any,
    article_id: int,
    ) -> None:
    """Record positive user feedback for an article.

    Updates the db with feedback status to `up` and feedback time.

    Args:
        supabase: Supabase client used to check article availability.
        article_id: ID of the article.
    """
    supabase.table("deutsch").update({
        "feedback": "up",
        "feedback_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", article_id).execute()


def handle_thumbs_down(
    supabase: Any,
    article_id: int,
    ) -> None:
    """Record negative user feedback for an article.

    Updates the db with feedback status to `down` and feedback time.

    Args:
        supabase: Supabase client used to check article availability.
        article_id: ID of the article.
    """
    supabase.table("deutsch").update({
        "feedback": "down",
        "feedback_at": datetime.now(timezone.utc).isoformat(),
        "active": False,
    }).eq("id", article_id).execute()


def has_enough_articles(
    supabase: Any,
    min_count: int,
    ) -> bool:
    """Checks if there are enough active articles in the database.

    Args:
        supabase: Supabase client used to check article availability.
        min_count: The minimum number of active articles in db.

    Returns:
        True if enough active articles, otherwise False.
    """
    result = (
        supabase
        .table("deutsch")
        .select("id", count="exact")
        .eq("active", True)
        .execute()
    )
    return (result.count or 0) >= min_count