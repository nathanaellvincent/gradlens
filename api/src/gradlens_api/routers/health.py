"""Health probe endpoint.

Used by Fly.io's healthcheck + by the Next.js app to detect backend
availability. Intentionally does not touch the vector index or DB —
a ready-but-cold index should still report healthy so deploys don't
flap during cache warmup.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from gradlens_api import __version__
from gradlens_api.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, env=settings.env)
