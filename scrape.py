"""Script to scrape articles from Tagesschau."""

import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from pydantic import ValidationError
from playwright.sync_api import sync_playwright

from utils.logging import get_logger
from database.client import get_supabase_client

logger = get_logger(__name__)
supabase = get_supabase_client()


def add_new_article() -> Optional[Dict[str, Any]]:
    """Scrapes Tagesschau for a new article and insert into the database.
    
    Steps:
    1. Randomly selects a news category from Tagesschau navigation bar
    2. Scrapes article links from category page using Playwright
    3. Insert an article into the Supabase db without duplication (using 'article_url' field)
    
    Returns:
        - A database row representating the newly inserted article if found OR
        - 'None' if no new article is available in the selected category
    """    
    category_list = [
        "USA",
        "Inland",
        "Ausland",
        "Wirtschaft",
        "Wissen",
        ]

    selected_category = random.choice(category_list)
    logger.info(f"Selected category: {selected_category}")

    with sync_playwright() as p:
            logger.info("Launching browser...")

            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()

            # Homepage
            page.goto("https://www.tagesschau.de")

            # Click category in nav bar (visible only)
            page.click(f"nav a:has-text('{selected_category}'):visible")
            page.wait_for_timeout(2000)

            # Get all article links
            article_links = page.locator("main a[href*='-100.html']")
            count = article_links.count()

            if count == 0:
                browser.close()
                raise RuntimeError("No article links found.")

            logger.info(f"Found {count} article links.")

            seen = set()

            for i in range(count):
                href = article_links.nth(i).get_attribute("href")

                if not href:
                    continue

                # Avoid duplicates in the same page
                if href in seen:
                    continue
                seen.add(href)

                article_url = f"https://www.tagesschau.de{href}"
                logger.info(f"Trying article: {article_url}")

                response = supabase.table("deutsch").upsert({
                    "article_url": article_url,
                    "category": selected_category,
                    },
                    on_conflict="article_url"
                ).execute()

                row = response.data[0]
                if row["status"] == "new":
                    logger.info(f"New article added: {article_url}")
                    browser.close()
                    return row

                logger.info("Article already exists, trying next...")

            browser.close()
            logger.info("No new articles found in this category.")
            return None


def scrape_article(url: str) -> Tuple[str, str, Optional[str]]:
    """Scrapes and article page and extract its title, content and published date.
    
    Steps:
    1. Uses Playwright to load the given article URL
    2. Extracts main title from first <h1> element
    3. Collects paragraph text from article body
    4. Parse the published date if available, otherwise use current time

    Args:
        url: The article url to scrape.
    
    Returns:
        title: The article title text.
        content: The article body text.
        published date: ISO-formatted publication date if found,
            otherwise current date.
    """
    logger.info("Scrapping article...")

    with sync_playwright() as p:
            logger.info("Launching browser for scraping...")

            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()

            # Homepage
            page.goto(url)
            page.wait_for_timeout(2000)

            # Retrieve the title
            if page.locator("h1").count() == 0:
                browser.close()
                raise RuntimeError("No <h1> title found.")

            title = page.locator("h1").first.inner_text().strip()

            # Content            
            paragraphs = page.locator("article p").all_inner_texts()
            content = "\n\n".join(p.strip() for p in paragraphs if p.strip())

            if not content:
                logger.warning("No article body found.")

            # Published date
            published_date = None
            date_locator = page.locator("text=Stand:")

            if date_locator.count() > 0:
                raw = date_locator.first.inner_text().replace("Stand:", "").replace("Uhr", "").strip()

                published_date = datetime.strptime(
                    raw.split()[0],
                    "%d.%m.%Y"
                ).date().isoformat()

            else:
                published_date = datetime.now(timezone.utc).isoformat()

            browser.close()

    return title, content, published_date


def process_one_article_status(
    from_status: str,
    to_status: str,
    ) -> Optional[Dict[str, Any]]:
    """Atomically select and transition one article from one status to another.

    Args:
        from_status: Current status value used to select an article.
        to_status: New status value assigned to the selected article

    Returns:
        The original article row with updated status if successful, otherwise None.
    """
    rows = (
        supabase
        .table("deutsch")
        .select("*")
        .eq("status", from_status)
        .limit(1)
        .execute()
    )

    if not rows.data:
        return None

    article = rows.data[0]

    # lock it
    lock = (
        supabase.table("deutsch")
        .update({"status": to_status})
        .eq("id", article["id"])
        .eq("status", from_status)
        .execute()
    )

    if not lock.data:
        return None

    return article


def scrape_all_new_articles() -> None:
    """Scrapes and process all articles with the status `new`.
    
    Steps:
    1. Continously fetches one article from db with `new` status
    2. Scrapes the content using Playwright
    3. Updates the scraped articles with relevant metadata
    4. Marks article status as `scrapped` or `failed`
    5. Process until now more `new` article is found.
    """
    while True:
        article = process_one_article_status("new", "scraping")
        if article is None:
            logger.info("No more articles to scrape.")
            break

        try:
            title, content, published_date = scrape_article(article["article_url"])

            supabase.table("deutsch").update({
                "title_de": title,
                "content_de": content,
                "published_date": published_date,
                "status": "scrapped"
            }).eq("id", article["id"]).execute()

            logger.info(f"Scrapped {article["article_url"]}")

        except (ValidationError, RuntimeError) as e:
            logger.exception(f"LLM failure: {e}")
            supabase.table("deutsch").update({
                "status": "failed"
            }).eq("id", article["id"]).execute()

            logger.info(f"Failed {article["article_url"]}: {e}")


if __name__ == "__main__":
    add_new_article()
    scrape_all_new_articles()