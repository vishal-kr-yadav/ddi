from pydantic import BaseModel
from typing import List, Optional


class ClaimRequest(BaseModel):
    claim: str


class ArticleSchema(BaseModel):
    title: str
    description: str
    url: str
    source: str
    published_at: str
    stance: Optional[str] = None            # SUPPORTS | CONTRADICTS | NEUTRAL | UNRELATED
    key_point: Optional[str] = None         # Claude's insight about this article
    relevance: Optional[int] = None         # 0-100
    credibility_score: Optional[int] = None    # 0-100 trust score
    credibility_tier: Optional[str] = None     # Highly Credible | Credible | Mixed | Low | Unrated
    credibility_color: Optional[str] = None    # green | blue | yellow | red | gray


class FactCheckResponse(BaseModel):
    claim: str
    verdict: str                       # VERIFIED | FALSE | MISLEADING | UNVERIFIED
    confidence: int                    # 0-100
    verdict_explanation: str
    summary: str
    guidance: str
    key_findings: List[str]
    articles: List[ArticleSchema]
    sources_searched: int
    processing_time: float
