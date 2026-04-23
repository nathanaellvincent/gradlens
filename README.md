# GradLens

> Semantic search for graduate schemes, internships, and entry-level engineering roles — built for final-year students drowning in 50-tab job boards.

Type a natural-language query like *"AI/ML grad schemes in London that sponsor visas, starting September 2026"* and get a ranked list of real, currently-open postings with citations back to the source JD.

**Status:** MVP in progress. Semantic retrieval working end-to-end (day 1). LLM-generated answers + visa-sponsorship auto-flag land in week 2.

## Why this exists

I'm graduating in July 2026 and currently applying. Existing job boards are either:

- **Keyword-matching only** — "machine learning" doesn't find JDs titled "ML Engineer, New Grad"
- **Opaque about filters that actually matter** — visa sponsorship, start dates, whether they take final-year undergrads
- **Walled-garden aggregators** — scrape-blocked, paywalled, or abandoned

GradLens is the tool I wanted while job-hunting, so I'm building it and using it myself.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Embeddings | `BAAI/bge-small-en-v1.5` (local, CPU) | No API keys, $0 per query |
| Reranker | `cross-encoder/ms-marco-MiniLM-L6-v2` | Second-stage relevance, local |
| Vector store | LanceDB | Embedded, columnar, arrow-based |
| Backend | FastAPI (Python 3.12, `uv`) | Async, typed, small footprint |
| Frontend | Next.js 16 App Router + Tailwind 4 | Matches my portfolio stack |
| Data source | Greenhouse public JSON API | Free, stable, thousands of JDs |
| Eval | Custom harness (Python CLI) | Recall@k, latency p95, cost tracking |

**No OpenAI / Anthropic / Pinecone / Cohere.** Every component runs locally or on free tiers. Upgrade paths are documented (`docs/upgrade-paths.md`) for when retrieval quality demands hosted embeddings or a managed reranker.

## Architecture

```
  ┌────────────────┐
  │ Greenhouse API │──► parse ──► chunk ──► embed (bge-small) ──┐
  │ (per company)  │                                             ▼
  └────────────────┘                                      ┌──────────┐
                                                          │ LanceDB  │
                                                          └────┬─────┘
                                                               │
  user query ──► embed ──► top-20 ──► reranker ──► top-5 ──► Next.js UI
                                      (MiniLM)
```

LLM generation (week 2) plugs in between reranker and UI, constrained to cite only the retrieved chunks.

## Getting started

```bash
# Prereqs: Node 20+, Python 3.12+, uv, pnpm (or npm)

# Backend
cd api
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd web
pnpm install
pnpm dev
```

Full dev setup + ingestion scripts: [`docs/dev-setup.md`](./docs/dev-setup.md) (coming).

## Roadmap

- [x] Day 1 — repo scaffold, ingestion from 5 Greenhouse companies, semantic search end-to-end
- [ ] Day 2 — eval harness (recall@k over hand-curated query set)
- [ ] Day 3 — LLM answer layer (Groq / Llama 3.3 70B) with citation-only generation
- [ ] Week 2 — visa sponsorship flag, deadline filter, multi-source ingest (Ashby, Lever)
- [ ] Week 3 — faithfulness eval, deployment, public launch

## License

MIT © 2026 Vincent Nathanael
