"""Semantic search endpoint — `GET /search`.

Thin shim over `gradlens_api.search.retrieve`. Validates query params,
measures per-request latency (surfaced in the response so the frontend
can show it — useful for the "built the infra myself" story), and
returns the hit list plus metadata.

GET (not POST) because queries are safe, cacheable, and we want clean
curl-ability during development. `q` and `k` are simple enough that
a query-string contract beats a JSON body.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from gradlens_api.config import settings
from gradlens_api.search import index, retrieve

router = APIRouter(tags=["search"])


class SearchHit(BaseModel):
    """Result card payload. Mirrors `search.index.Hit` as a Pydantic model."""

    source: str
    company: str
    upstream_id: str
    title: str
    url: str
    location: str
    snippet: str
    # L2 distance from query vec. Lower = more similar. Kept raw rather
    # than converted to a 0-1 score so the UI can decide how to present
    # it (raw number, rank-only, or hidden).
    distance: float


class SearchResponse(BaseModel):
    query: str
    k: int
    total: int = Field(description="Number of hits returned (≤ k).")
    index_size: int = Field(description="Total jobs currently in the index.")
    latency_ms: float = Field(description="End-to-end handler latency.")
    hits: list[SearchHit]


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=500, description="Natural-language query."),
    k: int = Query(10, ge=1, le=50, description="Max hits to return."),
) -> SearchResponse:
    t0 = time.perf_counter()
    hits = retrieve.retrieve(q, settings.data_dir, k=k)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return SearchResponse(
        query=q,
        k=k,
        total=len(hits),
        index_size=index.row_count(settings.data_dir),
        latency_ms=round(latency_ms, 2),
        hits=[SearchHit(**h) for h in hits],
    )
