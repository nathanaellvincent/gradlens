"""Canonical Job schema shared by every source adapter.

Adapters (`greenhouse.py`, future `ashby.py`, etc.) normalise their
upstream payload into this shape so downstream stages — storage,
embedding, retrieval — don't need per-source branching.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Job(BaseModel):
    """Normalised job description record."""

    # Composite key: (source, company, upstream_id) must be unique.
    source: str = Field(description="Upstream platform, e.g. 'greenhouse'")
    company: str = Field(description="Company slug on the upstream platform")
    upstream_id: str = Field(description="ID assigned by the upstream platform")

    title: str
    url: HttpUrl
    location: str | None = None
    offices: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)

    # Plain-text content — HTML already stripped. Embeddings run over this.
    # The original HTML is intentionally not stored: we can always refetch,
    # and keeping it bloats the DB 3-5x without improving retrieval quality.
    content: str

    updated_at: datetime | None = None
    first_published: datetime | None = None
    fetched_at: datetime


class IngestSummary(BaseModel):
    """Per-company ingestion result, returned by the CLI for logging."""

    source: str
    company: str
    fetched: int
    inserted: int
    updated: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
