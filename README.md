# GradLens

> Semantic search for graduate schemes, internships, and entry-level engineering roles — built for final-year students drowning in 50-tab job boards.

Type a natural-language query like *"new grad machine learning engineer, remote UK"* and get a ranked list of real, currently-open postings with direct links back to the source JD.

**Status — day 1 MVP shipped:**

| Stage | State |
|---|---|
| Ingestion (Greenhouse, 5 companies) | ✅ 1,724 open roles |
| Embedding pipeline (bge-small, ONNX) | ✅ 17 jobs/s on CPU |
| LanceDB vector index | ✅ ~2s cold-open, 384-dim |
| `GET /search` endpoint | ✅ 10ms p50 warm |
| Next.js search console | ✅ wired end-to-end |
| Reranker (Cohere / MiniLM cross-encoder) | ⏳ next commit |
| LLM answer + citations (Groq / Llama 3.3 70B) | ⏳ week 2 |
| Evaluation harness (recall@k, faithfulness) | ⏳ week 2 |
| Public deployment | ⏳ week 2 |

## Why this exists

I'm graduating July 2026 and currently applying. Existing job boards are either:

- **Keyword-matching only** — "machine learning" doesn't find JDs titled *"ML Engineer, New Grad"*
- **Opaque about filters that actually matter** — visa sponsorship, start dates, whether they take final-year undergrads
- **Walled-garden aggregators** — scrape-blocked, paywalled, or abandoned

GradLens is the tool I wanted while job-hunting, so I'm building it and using it myself.

## Architecture

```
                                            ┌──── eval harness ─────┐
                                            │  recall@k, latency,   │
                                            │  faithfulness, cost   │
                                            └──────────▲────────────┘
                                                       │ (week 2+)
┌──────────────┐                                       │
│  Greenhouse  │                                       │
│  boards API  │─► parse ─► strip HTML ─► SQLite ──────┼──► bge-small ──► LanceDB
│  (public)    │            (stdlib)     (metadata)    │    (ONNX CPU)    (vectors)
└──────────────┘                                       │                     │
                                                       │                     │
  user query ─► prefix ─► bge-small ─► top-k ─► [reranker] ─► [LLM] ─► Next.js UI
                          (ONNX CPU)                 ▲           ▲
                                                     │           │
                                             next commit      week 2
```

Both ingestion + index build are idempotent CLIs — the whole pipeline can be rebuilt from upstream in under 2 minutes.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Embeddings | `BAAI/bge-small-en-v1.5` via fastembed | Local, CPU, ONNX — no torch, no GPU, no API key |
| Vector store | LanceDB | Embedded, file-backed, arrow/columnar, no server process |
| Backend | FastAPI + uv (Python 3.12) | Async, typed, fast iter via `uv run` |
| Frontend | Next.js 16 App Router + Tailwind 4 | Turbopack dev loop, App Router server components |
| Data source | Greenhouse public boards API | Free, stable, thousands of JDs via slug curation |
| Reranker *(next)* | `ms-marco-MiniLM-L6-v2` cross-encoder | Local, cheap, material recall bump at top-k |
| LLM *(week 2)* | Groq free tier — Llama 3.3 70B | Zero-cost generation, citation-constrained prompt |

**No OpenAI / Anthropic / Pinecone / Cohere paid keys.** Every component runs locally or on free tiers. Upgrade paths documented in commit history — each component has a swap-in hosted alternative.

## Layout

```
gradlens/
├── api/                         FastAPI backend (uv-managed)
│   ├── src/gradlens_api/
│   │   ├── config.py            pydantic-settings, GRADLENS_ env prefix
│   │   ├── main.py              app factory + CORS + router wiring
│   │   ├── ingest/              upstream fetchers + SQLite store
│   │   │   ├── greenhouse.py    Greenhouse board adapter
│   │   │   ├── models.py        canonical Job schema
│   │   │   ├── store.py         SQLite upsert layer
│   │   │   └── cli.py           `gradlens-ingest`
│   │   ├── search/              embed + index + retrieve
│   │   │   ├── embed.py         fastembed wrapper, query/passage asymmetry
│   │   │   ├── index.py         LanceDB table + search
│   │   │   ├── retrieve.py      query → hits
│   │   │   └── build_cli.py     `gradlens-build-index`
│   │   └── routers/
│   │       ├── health.py        GET /health
│   │       └── search.py        GET /search
│   └── pyproject.toml
├── web/                         Next.js 16 App Router
│   └── src/
│       ├── app/                 layout + home (search console)
│       ├── components/
│       │   └── search-console.tsx
│       └── lib/
│           └── api.ts           typed /search client
└── README.md (this file)
```

## Getting started

```bash
# Prereqs: Node 20+, pnpm, Python 3.12+, uv

# 1. Install
cd api && uv sync && cd -
cd web && pnpm install && cd -

# 2. Pull job descriptions from upstream
cd api && uv run gradlens-ingest
# → ingests ~1700 open roles across 5 curated companies

# 3. Build the vector index
uv run gradlens-build-index
# → ~90s on an M-series CPU. Prints a sample-query probe on completion.

# 4. Run the API
uv run gradlens-api
# → http://127.0.0.1:8000

# 5. Run the frontend (separate terminal)
cd web && pnpm dev --port 3100
# → http://localhost:3100
```

Sanity probes:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","version":"0.1.0","env":"dev"}

curl 'http://127.0.0.1:8000/search?q=new+grad+machine+learning&k=3' | jq '.hits[].title'
```

## Configuration

All runtime config reads from env vars prefixed `GRADLENS_`. See `api/.env.example` for the full schema. Copy to `api/.env` for local overrides.

Frontend API base URL: `NEXT_PUBLIC_API_URL` (defaults to `http://127.0.0.1:8000`).

## Roadmap

- [x] **Day 1 — MVP shipped:** scaffold, Greenhouse ingestion (5 boards, 1724 jobs), bge-small embeddings, LanceDB index, `GET /search`, Next.js search UI
- [ ] **Day 2** — MiniLM cross-encoder reranker, evaluation harness with ~30 golden queries, recall@k + latency p95 tracking
- [ ] **Day 3** — LLM answer layer on top of retrieved chunks (Groq free tier, Llama 3.3 70B), citation-grounded
- [ ] **Week 2** — Ashby + Lever adapters, visa sponsorship auto-flag via zero-shot classifier, deadline filter UI
- [ ] **Week 3** — faithfulness eval (RAGAs-style), Vercel + Fly.io deploy, public beta

## License

MIT © 2026 Vincent Nathanael
