"""
Article Scraper Service
=======================
Visits each article URL and extracts full body text using BeautifulSoup.
Runs in parallel (semaphore-limited) after the fetch phase, before Claude analysis.
Failures are silent — article falls back to its original description.
"""

import asyncio
import httpx
import logging
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# CSS selectors tried in order — stops at first one with enough text
ARTICLE_SELECTORS = [
    "article",
    '[class*="article-body"]',
    '[class*="article-content"]',
    '[class*="article__body"]',
    '[class*="story-body"]',
    '[class*="story-content"]',
    '[class*="post-content"]',
    '[class*="entry-content"]',
    '[class*="main-content"]',
    "main",
]

# Tags that add noise — removed before extraction
NOISE_TAGS = ["script", "style", "nav", "header", "footer", "aside",
              "figure", "figcaption", "form", "button", "iframe"]

MAX_CONTENT_CHARS = 2500
MIN_PARAGRAPH_LEN = 40


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Try structured selectors first
    for selector in ARTICLE_SELECTORS:
        el = soup.select_one(selector)
        if el:
            paragraphs = el.find_all("p")
            text = " ".join(
                p.get_text(" ", strip=True)
                for p in paragraphs
                if len(p.get_text(strip=True)) >= MIN_PARAGRAPH_LEN
            )
            if len(text) > 200:
                return text[:MAX_CONTENT_CHARS]

    # Fallback: all <p> tags on the page
    paragraphs = soup.find_all("p")
    text = " ".join(
        p.get_text(" ", strip=True)
        for p in paragraphs
        if len(p.get_text(strip=True)) >= MIN_PARAGRAPH_LEN
    )
    return text[:MAX_CONTENT_CHARS]


async def _scrape_one(article: dict, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> dict:
    url = article.get("url", "")
    if not url:
        return article

    async with semaphore:
        try:
            r = await client.get(url, timeout=8.0)
            if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                extracted = _extract_text(r.text)
                if extracted and len(extracted) > len(article.get("content", "")):
                    return {**article, "content": extracted}
        except Exception as e:
            logger.debug(f"Scrape failed [{url[:60]}]: {e}")

    return article


async def scrape_articles(articles: List[dict], max_concurrent: int = 5) -> List[dict]:
    """
    Enrich articles with full body text.
    Runs max_concurrent scrapes at a time; failures return the original article unchanged.
    """
    if not articles:
        return articles

    semaphore = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers=HEADERS,
        timeout=httpx.Timeout(10.0),
    ) as client:
        tasks = [_scrape_one(a, client, semaphore) for a in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    scraped_count = 0
    for original, result in zip(articles, results):
        if isinstance(result, dict):
            if len(result.get("content", "")) > len(original.get("content", "")):
                scraped_count += 1
            enriched.append(result)
        else:
            enriched.append(original)

    logger.info(f"Scraping complete: {scraped_count}/{len(articles)} articles enriched with full text")
    return enriched
