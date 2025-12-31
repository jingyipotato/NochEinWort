"""Script for recommending articles."""

from datetime import datetime, timezone, date
from typing import Any, Dict, List, TypedDict

from utils.logging import get_logger

logger = get_logger(__name__)


class TopicPreference(TypedDict):
    count: int
    latest: datetime


Article = Dict[str, Any]


def get_topic_preferences(supabase: Any) -> Dict[str, TopicPreference]:
    """Build topic preference profile from previously liked articles.

    The preference captures:
    - How frequently a topic was liked
    - How recent the topic was liked

    Args:
        supabase: Supabase client used to check article availability.
 
    Returns:
        Example:
        {
            "Heath": {"count": 5, "latest": datetime},
            "Economy": {"count": 2, "latest: datetime}
        }
    """
    rows = (
        supabase
        .table("deutsch")
        .select("topic, feedback_at")
        .eq("feedback", "up")
        .eq("active", True)
        .execute()
    ).data

    prefs: Dict[str, TopicPreference] = {}

    for row in rows:
        topic = row.get("topic")
        feedback_at = row.get("feedback_at")

        if not topic or not feedback_at:
            continue

        ts = datetime.fromisoformat(feedback_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        pref = prefs.get(topic)
        if pref is None:
            pref = prefs[topic] = {"count": 0, "latest": ts}

        pref["count"] += 1
        if pref["count"] == 1 or ts > pref["latest"]:
            pref["latest"] = ts

    return prefs


def get_unseen_articles(supabase: Any) -> List[Article]:
    """Fetch all active, unrecommended, not liked/disliked articles.
    
    Args:
        supabase: Supabase client used to check article availability.
    
    Returns:
        A list of unseen articles.
    """

    return (
        supabase
        .table("deutsch")
        .select(
            "id, title_en, article_url, topic, published_date"
        )
        .eq("active", True)
        .is_("feedback", None)
        .is_("recommended_at", None)
        .execute()
    ).data
    

def score_article(
    article: Article,
    topic_prefs: Dict[str, TopicPreference],
    ) -> float:
    """Score an article based on the following criterias below.
    
    Args:
        article: Article data containing relevant metadata.
        topic_prefs: The topic with its associated count and latest date.

    1. Topic frequency (dominant signal)
        - Up to +3 points per previous like
    2. Topic recency
        - Up to +5 points, decays daily
    3. Article freshness
        - Up to +3 points or very recent articles

    Returns:
        A floating point score. Higher the better.
    """
    score = 0.0
    now = datetime.now(timezone.utc)

    topic = article.get("topic")
    if topic and topic in topic_prefs:
        pref = topic_prefs[topic]

        # Topic frequency
        score += pref["count"] * 3

        # Topic recency (decays over days)
        days_since_like = (now - pref["latest"]).days
        score += max(0, 5 - days_since_like)

    # Article freshness bonus
    published_date = article.get("published_date")
    if published_date:
        created_date = date.fromisoformat(published_date[:10])
        days_old = (date.today() - created_date).days
        score += max(0, 3 - days_old)

    return score


def mark_as_recommended(
    supabase: Any, 
    articles: List[Article],
    ) -> None:
    """Mark articles as recommended to avoid repeating suggestions.
    
    Args:
        supabase: Supabase client used to check article availability.
        articles: Article data containing relevant metadata.
    """

    if not articles:
        return

    now = datetime.now(timezone.utc).isoformat()

    for article in articles:
        supabase.table("deutsch").update(
            {"recommended_at": now}
        ).eq("id", article["id"]).execute()


def get_recommendations(
    supabase: Any,
    limit: int,
    ) -> List[Article]:
    """Return ranked article recommendations.

    Steps:
    1. Builds topic preferences
    2. Fetch unseen articles
    3. Score each article
    4. Sort by score (descending)
    5. Return top-limit
    6. Mark as recommended

    Args:
        supabase: Supabase client used to check article availability.
        limit: Max number of articles to recommend.

    Returns:
        A list of recommended articles.
    """
    topic_prefs = get_topic_preferences(supabase)
    if not topic_prefs:
        logger.info("No liked topics yet, skipping recommendations.")
        return []

    candidates = get_unseen_articles(supabase)
    if not candidates:
        logger.info("No unseen articles available.")
        return []

    scored = [
        (score_article(article, topic_prefs), article)
        for article in candidates
    ]

    scored.sort(key=lambda x: x[0], reverse=True)

    recommendations = [article for _, article in scored[:limit]]

    mark_as_recommended(supabase, recommendations)

    return recommendations