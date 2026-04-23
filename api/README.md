# gradlens-api

FastAPI backend for GradLens. Owns:

- Semantic search over indexed job descriptions
- Ingestion pipeline (Greenhouse → LanceDB)
- Evaluation harness (separate CLI, shares the index)

## Run locally

```bash
# Prereqs: Python 3.12+, uv

uv sync --all-extras
uv run gradlens-api      # dev server on :8000 with --reload

# or directly:
uv run uvicorn gradlens_api.main:app --reload
```

Verify:

```bash
curl http://127.0.0.1:8000/health
# => {"status":"ok","version":"0.1.0","env":"dev"}
```

## Layout

```
src/gradlens_api/
├── __init__.py
├── cli.py              # entry point for `uv run gradlens-api`
├── config.py           # pydantic-settings, env-derived config
├── main.py             # FastAPI app factory + middleware
└── routers/            # HTTP surface — one module per resource
    └── health.py
```

Search, ingest, and eval modules land in follow-up commits.

## Config

All runtime config reads from env vars prefixed `GRADLENS_`. See
`src/gradlens_api/config.py` for the full schema. Copy `.env.example`
to `.env` for local overrides.
