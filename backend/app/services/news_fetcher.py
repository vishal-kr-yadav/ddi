"""
News Fetcher Service
====================
Fetches news from 10 sources covering USA, Europe, and Asia:

Always-available (no API key):
  1. GDELT Project       - Global, free, massive database
  2. Google News RSS US  - USA edition
  3. Google News RSS EU  - UK/Europe edition
  4. Google News RSS AS  - India/Asia edition

Optional (require API key in .env):
  5. NewsAPI.org         - Global/USA
  6. The Guardian        - UK/Europe
  7. New York Times      - USA
  8. GNews               - Global (strong Asia)
  9. Currents API        - Global
  10. Mediastack         - Global
  11. Bing News Search   - Global (bonus)
"""

import asyncio
import httpx
import feedparser
import re
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_date_range():
    now = datetime.utcnow()
    return now, now - timedelta(days=30)


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def normalize(
    title: str,
    description: str,
    url: str,
    source: str,
    published_at: str,
    content: str = "",
) -> dict:
    return {
        "title": strip_html(title or ""),
        "description": strip_html(description or "")[:500],
        "url": url or "",
        "source": source or "Unknown",
        "published_at": published_at or "",
        "content": strip_html(content or "")[:800],
    }


# ---------------------------------------------------------------------------
# Source 1: GDELT Project (free, no key, global)
# ---------------------------------------------------------------------------
async def fetch_gdelt(query: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        now, from_dt = get_date_range()
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={quote_plus(query)}"
            f"&mode=artlist"
            f"&maxrecords={limit * 2}"
            f"&format=json"
            f"&startdatetime={from_dt.strftime('%Y%m%d%H%M%S')}"
            f"&enddatetime={now.strftime('%Y%m%d%H%M%S')}"
        )
        r = await client.get(url, timeout=15.0)
        if r.status_code != 200:
            return []
        data = r.json()
        results = []
        for item in data.get("articles", [])[:limit]:
            results.append(normalize(
                title=item.get("title", ""),
                description=item.get("seendesc", ""),
                url=item.get("url", ""),
                source=item.get("domain", "GDELT"),
                published_at=item.get("seendate", ""),
            ))
        logger.info(f"GDELT returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"GDELT error: {e}")
        return []


# ---------------------------------------------------------------------------
# Sources 2/3/4: Google News RSS (free, no key, regional)
# ---------------------------------------------------------------------------
GOOGLE_NEWS_REGIONS = {
    "US": ("en-US", "US", "US:en", "USA"),
    "GB": ("en-GB", "GB", "GB:en", "Europe/UK"),
    "IN": ("en-IN", "IN", "IN:en", "Asia/India"),
}

async def fetch_google_news_rss(
    query: str,
    region: str,
    client: httpx.AsyncClient,
    limit: int = 5,
) -> List[dict]:
    try:
        hl, gl, ceid, label = GOOGLE_NEWS_REGIONS.get(region, GOOGLE_NEWS_REGIONS["US"])
        rss_url = (
            f"https://news.google.com/rss/search"
            f"?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"
        )
        r = await client.get(rss_url, timeout=15.0)
        feed = feedparser.parse(r.text)

        results = []
        for entry in feed.entries[:limit]:
            results.append(normalize(
                title=entry.get("title", ""),
                description=entry.get("summary", ""),
                url=entry.get("link", ""),
                source=f"Google News ({label})",
                published_at=entry.get("published", ""),
            ))
        logger.info(f"Google News {region} returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"Google News RSS ({region}) error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 5: NewsAPI.org
# ---------------------------------------------------------------------------
async def fetch_newsapi(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        _, from_dt = get_date_range()
        r = await client.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": from_dt.strftime("%Y-%m-%d"),
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": limit,
                "apiKey": api_key,
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("articles", []):
            results.append(normalize(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=item.get("source", {}).get("name", "NewsAPI"),
                published_at=item.get("publishedAt", ""),
                content=item.get("content", ""),
            ))
        logger.info(f"NewsAPI returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"NewsAPI error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 6: The Guardian
# ---------------------------------------------------------------------------
async def fetch_guardian(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        _, from_dt = get_date_range()
        r = await client.get(
            "https://content.guardianapis.com/search",
            params={
                "q": query,
                "from-date": from_dt.strftime("%Y-%m-%d"),
                "api-key": api_key,
                "show-fields": "headline,trailText",
                "page-size": limit,
                "order-by": "relevance",
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("response", {}).get("results", []):
            fields = item.get("fields", {})
            results.append(normalize(
                title=fields.get("headline", item.get("webTitle", "")),
                description=fields.get("trailText", ""),
                url=item.get("webUrl", ""),
                source="The Guardian",
                published_at=item.get("webPublicationDate", ""),
            ))
        logger.info(f"Guardian returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"Guardian error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 7: New York Times
# ---------------------------------------------------------------------------
async def fetch_nyt(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        _, from_dt = get_date_range()
        r = await client.get(
            "https://api.nytimes.com/svc/search/v2/articlesearch.json",
            params={
                "q": query,
                "begin_date": from_dt.strftime("%Y%m%d"),
                "api-key": api_key,
                "sort": "relevance",
                "fl": "headline,abstract,web_url,pub_date,snippet",
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("response", {}).get("docs", [])[:limit]:
            headline = item.get("headline", {})
            results.append(normalize(
                title=headline.get("main", ""),
                description=item.get("abstract", "") or item.get("snippet", ""),
                url=item.get("web_url", ""),
                source="New York Times",
                published_at=item.get("pub_date", ""),
            ))
        logger.info(f"NYT returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"NYT error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 8: GNews
# ---------------------------------------------------------------------------
async def fetch_gnews(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        _, from_dt = get_date_range()
        r = await client.get(
            "https://gnews.io/api/v4/search",
            params={
                "q": query,
                "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lang": "en",
                "max": limit,
                "token": api_key,
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("articles", []):
            results.append(normalize(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=item.get("source", {}).get("name", "GNews"),
                published_at=item.get("publishedAt", ""),
                content=item.get("content", ""),
            ))
        logger.info(f"GNews returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"GNews error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 9: Currents API
# ---------------------------------------------------------------------------
async def fetch_currents(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        _, from_dt = get_date_range()
        r = await client.get(
            "https://api.currentsapi.services/v1/search",
            params={
                "keywords": query,
                "language": "en",
                "start_date": from_dt.strftime("%Y-%m-%d"),
                "apiKey": api_key,
                "limit": limit,
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("news", []):
            results.append(normalize(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=item.get("author", "Currents API"),
                published_at=item.get("published", ""),
            ))
        logger.info(f"Currents API returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"Currents API error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 10: Mediastack
# ---------------------------------------------------------------------------
async def fetch_mediastack(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        r = await client.get(
            "http://api.mediastack.com/v1/news",
            params={
                "access_key": api_key,
                "keywords": query,
                "languages": "en",
                "limit": limit,
                "sort": "popularity",
            },
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("data", []):
            results.append(normalize(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=item.get("source", "Mediastack"),
                published_at=item.get("published_at", ""),
            ))
        logger.info(f"Mediastack returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"Mediastack error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 11: Bing News Search (bonus)
# ---------------------------------------------------------------------------
async def fetch_bing_news(query: str, api_key: str, client: httpx.AsyncClient, limit: int = 5) -> List[dict]:
    try:
        r = await client.get(
            "https://api.bing.microsoft.com/v7.0/news/search",
            params={
                "q": query,
                "mkt": "en-US",
                "freshness": "Month",
                "count": limit,
                "sortBy": "Relevance",
            },
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=15.0,
        )
        data = r.json()
        results = []
        for item in data.get("value", []):
            provider = item.get("provider", [{}])[0].get("name", "Bing News")
            results.append(normalize(
                title=item.get("name", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=provider,
                published_at=item.get("datePublished", ""),
            ))
        logger.info(f"Bing News returned {len(results)} articles")
        return results
    except Exception as e:
        logger.warning(f"Bing News error: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 12: Major outlet RSS feeds (free, no key, cloud-friendly)
# ---------------------------------------------------------------------------
MAJOR_RSS_FEEDS = [
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC News"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "NYT RSS"),
    ("https://feeds.npr.org/1001/rss.xml", "NPR"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://rss.cnn.com/rss/edition.rss", "CNN"),
]


async def fetch_major_rss(
    query: str, client: httpx.AsyncClient, limit: int = 10,
) -> List[dict]:
    """Fetch from major outlet RSS feeds and filter by query keywords."""
    keywords = [w.lower() for w in query.split() if len(w) > 2]
    all_results = []

    async def _fetch_one(feed_url: str, source_name: str):
        try:
            r = await client.get(feed_url, timeout=10.0)
            feed = feedparser.parse(r.text)
            matched = []
            for entry in feed.entries:
                title = (entry.get("title", "") or "").lower()
                summary = (entry.get("summary", "") or "").lower()
                if any(kw in title or kw in summary for kw in keywords):
                    matched.append(normalize(
                        title=entry.get("title", ""),
                        description=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source=source_name,
                        published_at=entry.get("published", ""),
                    ))
            return matched
        except Exception as e:
            logger.warning(f"RSS {source_name} error: {e}")
            return []

    feed_tasks = [_fetch_one(url, name) for url, name in MAJOR_RSS_FEEDS]
    results = await asyncio.gather(*feed_tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_results.extend(result)

    logger.info(f"Major RSS feeds returned {len(all_results)} matching articles")
    return all_results[:limit]


# ---------------------------------------------------------------------------
# Main Fetcher Class
# ---------------------------------------------------------------------------
class NewsFetcher:
    def __init__(self, settings):
        self.settings = settings

    async def fetch_all(self, query: str) -> List[dict]:
        limit = self.settings.MAX_ARTICLES_PER_SOURCE

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
            timeout=httpx.Timeout(20.0),
        ) as client:
            # Always-available sources
            tasks = [
                fetch_gdelt(query, client, limit),
                fetch_google_news_rss(query, "US", client, limit),
                fetch_google_news_rss(query, "GB", client, limit),
                fetch_google_news_rss(query, "IN", client, limit),
                fetch_major_rss(query, client, limit),
            ]

            # Optional sources (activated when API key is present)
            s = self.settings
            if s.NEWSAPI_KEY:
                tasks.append(fetch_newsapi(query, s.NEWSAPI_KEY, client, limit))
            if s.GUARDIAN_API_KEY:
                tasks.append(fetch_guardian(query, s.GUARDIAN_API_KEY, client, limit))
            if s.NYT_API_KEY:
                tasks.append(fetch_nyt(query, s.NYT_API_KEY, client, limit))
            if s.GNEWS_API_KEY:
                tasks.append(fetch_gnews(query, s.GNEWS_API_KEY, client, limit))
            if s.CURRENTS_API_KEY:
                tasks.append(fetch_currents(query, s.CURRENTS_API_KEY, client, limit))
            if s.MEDIASTACK_API_KEY:
                tasks.append(fetch_mediastack(query, s.MEDIASTACK_API_KEY, client, limit))
            if s.BING_NEWS_API_KEY:
                tasks.append(fetch_bing_news(query, s.BING_NEWS_API_KEY, client, limit))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten, deduplicate by URL
        all_articles: List[dict] = []
        seen_urls: set = set()
        for result in results:
            if not isinstance(result, list):
                continue
            for article in result:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)

        logger.info(
            f"Total unique articles fetched: {len(all_articles)} "
            f"from {len(tasks)} sources"
        )
        return all_articles
