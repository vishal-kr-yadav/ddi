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
from app.mongo import store_fact_check, get_fact_check_by_id, get_user_history, log_activity
from app.services.user_store import check_rate_limit, record_usage
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
async def _stream(claim: str, email: str):
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
            await store_fact_check(result, email)
            await record_usage(email, claim, fact_check_id)
        except Exception as e:
            logger.error(f"DB store / usage error: {e}")

        yield _sse("result", data=result)

    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield _sse("error", message="Something went wrong. Please try again.")


@router.post("/fact-check/stream")
async def fact_check_stream(
    request: ClaimRequest,
    x_user_email: str = Header(...),
):
    email = x_user_email.strip().lower()

    # Check rate limit
    try:
        usage = await check_rate_limit(email)
    except ValueError:
        raise HTTPException(status_code=403, detail="Email not registered.")
    if not usage["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Weekly limit reached ({settings.WEEKLY_FACT_CHECK_LIMIT} checks). Resets at {usage['resets_at']}.",
        )

    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")
    if len(claim) > 500:
        raise HTTPException(status_code=400, detail="Claim too long (max 500 chars).")

    logger.info(f"Stream fact-check: '{claim}' by {email}")
    return StreamingResponse(
        _stream(claim, email),
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


# ---------------------------------------------------------------------------
# User's own fact-check history
# GET /api/v1/my-history?email=user@example.com
# ---------------------------------------------------------------------------
@router.get("/my-history")
async def my_history(email: str):
    email = email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
    history = await get_user_history(email)
    return {"history": history}


# ---------------------------------------------------------------------------
# Non-streaming fallback  (kept for API clients / testing)
# POST /api/v1/fact-check
# ---------------------------------------------------------------------------
@router.post("/fact-check", response_model=FactCheckResponse)
async def fact_check_sync(
    request: ClaimRequest,
    x_user_email: str = Header(...),
):
    email = x_user_email.strip().lower()
    try:
        usage = await check_rate_limit(email)
    except ValueError:
        raise HTTPException(status_code=403, detail="Email not registered.")
    if not usage["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Weekly limit reached ({settings.WEEKLY_FACT_CHECK_LIMIT} checks).",
        )

    start = time.time()
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")

    all_articles = await news_fetcher.fetch_all(claim)
    if not all_articles:
        raise HTTPException(status_code=404, detail="No articles found.")

    top = select_top_articles(all_articles, claim, top_n=settings.TOP_ARTICLES_FOR_ANALYSIS)
    try:
        top = await scrape_articles(top)
    except Exception:
        pass

    try:
        analysis = await fact_checker.analyze(claim, top)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=502, detail="AI analysis failed.")

    sa_map = {
        item["index"]: item
        for item in analysis.get("source_analysis", [])
        if isinstance(item.get("index"), int) and 0 <= item["index"] < len(top)
    }

    enriched = [
        ArticleSchema(**_enrich_article(a, sa_map.get(i, {})))
        for i, a in enumerate(top)
    ]

    return FactCheckResponse(
        claim=claim,
        verdict=analysis.get("verdict", "UNVERIFIED"),
        confidence=analysis.get("confidence", 0),
        verdict_explanation=analysis.get("verdict_explanation", ""),
        summary=analysis.get("summary", ""),
        guidance=analysis.get("guidance", ""),
        key_findings=analysis.get("key_findings", []),
        articles=enriched,
        sources_searched=len(all_articles),
        processing_time=round(time.time() - start, 2),
    )
