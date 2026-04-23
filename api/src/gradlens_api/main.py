"""FastAPI application entry point.

Bootstraps the app, wires CORS for the Next.js frontend, and mounts
the routers. Kept thin — business logic lives in dedicated modules
(`search`, `ingest`) so this file stays a readable table-of-contents
for the HTTP surface.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gradlens_api import __version__
from gradlens_api.config import settings
from gradlens_api.routers import health, search


def create_app() -> FastAPI:
    app = FastAPI(
        title="GradLens API",
        version=__version__,
        description=(
            "Semantic search over graduate-scheme job descriptions. "
            "Retrieval-first — LLM answer generation is deferred to a "
            "later milestone to keep the MVP eval-grounded."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(health.router)
    app.include_router(search.router)

    return app


app = create_app()
