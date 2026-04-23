"""CLI entry — `uv run gradlens-api` launches the dev server.

Thin wrapper around uvicorn so the package exposes one canonical way
to start the app. For production we invoke uvicorn directly with
prod-tuned flags from the Fly.io Procfile.
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "gradlens_api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
