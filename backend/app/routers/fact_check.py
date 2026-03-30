import time
import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from app.models.schemas import ClaimRequest, FactCheckResponse, ArticleSchema
from app.services.news_fetcher import NewsFetcher
from app.services.fact_checker import FactChecker, select_top_articles
from app.services.scraper import scrape_articles
from app.services.credibility import get_credibility
from app.mongo import store_fact_check, get_fact_check_by_id, get_device_usage, record_device_check
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

news_fetcher = NewsFetcher(settings)
fact_checker = FactChecker()


# ---------------------------------------------------------------------------
# Helper: serialize an article dict with credibility scores attached
# ---------------------------------------------------------------------------
def _enrich_article(article: dict, sa: dict) -> dict:
    cred = get_credibility(article.get("source", ""))
    return {
        "title":             article.get("title", ""),
        "description":       article.get("description", ""),
        "url":               article.get("url", ""),
        "source":            article.get("source", ""),
        "published_at":      article.get("published_at", ""),
        "stance":            sa.get("stance", "NEUTRAL"),
        "key_point":         sa.get("key_point", ""),
        "relevance":         sa.get("relevance", 0),
        "credibility_score": cred["score"],
        "credibility_tier":  cred["tier"],
        "credibility_color": cred["color"],
    }


def _sse(event: str, **data) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'event': event, **data})}\n\n"


# ---------------------------------------------------------------------------
# SSE Streaming endpoint  (PRIMARY)
# POST /api/v1/fact-check/stream
# ---------------------------------------------------------------------------
async def _stream(claim: str, device_id: str):
    start = time.time()
    fact_check_id = str(uuid.uuid4())

    try:
        # ── Step 1: Fetch ──────────────────────────────────────────────────
        yield _sse("progress", step="fetching",
                   message="Searching 10+ global news sources…")
        all_articles = await news_fetcher.fetch_all(claim)
        logger.info(f"Fetched {len(all_articles)} articles")

        if not all_articles:
            yield _sse("error", message="No articles found. Try rephrasing your claim.")
            return

        # ── Step 2: Rank ───────────────────────────────────────────────────
        yield _sse("progress", step="selecting",
                   message=f"Found {len(all_articles)} articles — ranking by relevance…")
        top = select_top_articles(all_articles, claim, top_n=settings.TOP_ARTICLES_FOR_ANALYSIS)

        # ── Step 3: Scrape ─────────────────────────────────────────────────
        yield _sse("progress", step="scraping",
                   message=f"Scraping full content from {len(top)} sources…")
        try:
            top = await scrape_articles(top)
        except Exception as e:
            logger.warning(f"Scraping failed, continuing: {e}")

        # ── Step 4: AI Analysis ────────────────────────────────────────────
        yield _sse("progress", step="analyzing",
                   message="AI engine is reading and cross-referencing all sources…")
        analysis = await fact_checker.analyze(claim, top)

        # ── Step 5: Build result ───────────────────────────────────────────
        yield _sse("progress", step="building",
                   message="Generating your fact-check report…")

        sa_map = {
            item["index"]: item
            for item in analysis.get("source_analysis", [])
            if isinstance(item.get("index"), int) and 0 <= item["index"] < len(top)
        }

        articles_out = [_enrich_article(a, sa_map.get(i, {})) for i, a in enumerate(top)]

        result = {
            "id":                  fact_check_id,
            "claim":               claim,
            "verdict":             analysis.get("verdict", "UNVERIFIED"),
            "confidence":          analysis.get("confidence", 0),
            "verdict_explanation": analysis.get("verdict_explanation", ""),
            "summary":             analysis.get("summary", ""),
            "guidance":            analysis.get("guidance", ""),
            "key_findings":        analysis.get("key_findings", []),
            "articles":            articles_out,
            "sources_searched":    len(all_articles),
            "processing_time":     round(time.time() - start, 2),
        }

        # ── Step 6: Store & record usage ──────────────────────────────────
        try:
            await store_fact_check(result, device_id)
            await record_device_check(device_id)
        except Exception as e:
            logger.error(f"DB store / usage error: {e}")

        yield _sse("result", data=result)

    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield _sse("error", message="Something went wrong. Please try again.")


@router.post("/fact-check/stream")
async def fact_check_stream(
    request: ClaimRequest,
    x_device_id: str = Header(...),
):
    device_id = x_device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required.")

    # Check rate limit
    usage = await get_device_usage(device_id)
    if usage["checks_remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({settings.DAILY_DEVICE_LIMIT} checks). Resets at {usage['resets_at']}.",
        )

    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")
    if len(claim) > 500:
        raise HTTPException(status_code=400, detail="Claim too long (max 500 chars).")

    logger.info(f"Stream fact-check: '{claim}' by device {device_id[:8]}…")
    return StreamingResponse(
        _stream(claim, device_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET stored result by ID   (for shareable URLs)
# GET /api/v1/result/{id}
# ---------------------------------------------------------------------------
@router.get("/result/{fact_check_id}")
async def get_result(fact_check_id: str):
    result = await get_fact_check_by_id(fact_check_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fact-check not found.")
    return result
