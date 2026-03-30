"""
Fact Checker Service
====================
Uses Claude AI to:
  1. Score article relevance
  2. Select top-N articles
  3. Analyze claim vs. articles
  4. Produce structured verdict + summary + guidance
"""

import json
import logging
from typing import List
from anthropic import AsyncAnthropic
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Relevance Scoring (fast keyword-based pre-filter)
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "had", "her", "was", "one", "our", "out", "day", "get", "has", "him",
    "his", "how", "did", "its", "let", "may", "now", "old", "see", "two",
    "way", "who", "boy", "did", "its", "too", "use", "with", "that", "this",
    "will", "from", "they", "been", "have", "more", "than", "when", "what",
    "were", "said", "each", "which", "their", "would", "could", "about",
    "there", "into", "some", "than", "then", "also", "just",
}


def extract_keywords(text: str) -> List[str]:
    words = text.lower().split()
    return [w.strip(".,!?\"'") for w in words if len(w) > 3 and w not in STOP_WORDS]


def score_article(article: dict, keywords: List[str]) -> int:
    if not keywords:
        return 0
    title = article.get("title", "").lower()
    desc = article.get("description", "").lower()
    content = article.get("content", "").lower()

    score = 0
    for kw in keywords:
        if kw in title:
            score += 4      # title match is most valuable
        if kw in desc:
            score += 2
        if kw in content:
            score += 1
    return min(100, int((score / (len(keywords) * 7)) * 100))


def select_top_articles(articles: List[dict], query: str, top_n: int = 10) -> List[dict]:
    keywords = extract_keywords(query)

    for article in articles:
        article["_score"] = score_article(article, keywords)

    # Sort by relevance, filter out completely unrelated
    scored = sorted(articles, key=lambda x: x["_score"], reverse=True)

    # Take top_n, but always ensure at least top_n articles even with score=0
    top = scored[:top_n]
    return top


# ---------------------------------------------------------------------------
# Claude Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert fact-checker and investigative journalist with decades of experience
verifying claims across global news sources. You are impartial, thorough, and evidence-based.
Your role is to analyze news claims and provide accurate, unbiased fact-checks based solely on
the evidence presented in the provided articles."""

FACT_CHECK_PROMPT = """A user wants to fact-check the following claim:

CLAIM: "{claim}"

I have gathered {article_count} news articles from reputable sources worldwide (past 30 days):

{articles_text}

---

Carefully analyze these articles against the claim. Consider:
- Which articles directly confirm or deny the claim?
- Which are tangentially related but relevant context?
- What is the overall consensus across global sources?
- Are credible sources contradicting each other?

Return your analysis as a valid JSON object with EXACTLY this structure (pure JSON, no markdown wrapping):
{{
  "verdict": "<VERIFIED|FALSE|MISLEADING|UNVERIFIED>",
  "confidence": <integer 0-100>,
  "verdict_explanation": "<One clear sentence explaining the verdict>",
  "summary": "<2-3 paragraphs. What do sources collectively say about this topic? Be specific and cite source names.>",
  "guidance": "<2-3 sentences of clear, actionable guidance. Tell the user what is real, what is not, and what to watch for.>",
  "key_findings": [
    "<Specific finding 1 with source reference>",
    "<Specific finding 2 with source reference>",
    "<Specific finding 3 with source reference>"
  ],
  "source_analysis": [
    {{
      "index": <0-based article index>,
      "stance": "<SUPPORTS|CONTRADICTS|NEUTRAL|UNRELATED>",
      "relevance": <0-100>,
      "key_point": "<What this specific article says that is relevant to the claim>"
    }}
  ]
}}

Verdict guidelines:
- VERIFIED: Claim is confirmed by multiple credible sources with solid evidence
- FALSE: Claim is directly and clearly contradicted by credible evidence
- MISLEADING: Claim contains partial truth but lacks important context or is framed deceptively
- UNVERIFIED: Insufficient evidence to confirm or deny — this is the honest answer when uncertain"""


def format_articles_for_prompt(articles: List[dict]) -> str:
    parts = []
    for i, a in enumerate(articles):
        lines = [f"[Article {i}]"]
        lines.append(f"Source: {a.get('source', 'Unknown')}")
        lines.append(f"Title: {a.get('title', 'No title')}")
        if a.get("description"):
            lines.append(f"Summary: {a['description']}")
        if a.get("content") and len(a["content"]) > 60:
            lines.append(f"Content excerpt: {a['content'][:600]}")
        lines.append(f"Published: {a.get('published_at', 'Unknown date')}")
        lines.append(f"URL: {a.get('url', '')}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Fact Checker Class
# ---------------------------------------------------------------------------

class FactChecker:
    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=httpx.Timeout(120.0, connect=30.0),
            max_retries=3,
        )

    async def analyze(self, claim: str, articles: List[dict]) -> dict:
        articles_text = format_articles_for_prompt(articles)
        prompt = FACT_CHECK_PROMPT.format(
            claim=claim,
            article_count=len(articles),
            articles_text=articles_text,
        )

        logger.info(f"Calling Anthropic API (model=claude-opus-4-6, articles={len(articles)})")
        message = await self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.info(f"Anthropic API responded (usage: {message.usage})")

        raw = message.content[0].text.strip()

        # Strip markdown fences if Claude wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error from Claude: {e}\nRaw: {raw[:500]}")
            return {
                "verdict": "UNVERIFIED",
                "confidence": 0,
                "verdict_explanation": "Analysis could not be completed due to a processing error.",
                "summary": "We were unable to complete the analysis. Please try again.",
                "guidance": "Please try rephrasing your claim and submitting again.",
                "key_findings": [],
                "source_analysis": [],
            }
