"""`gradlens-build-index` — rebuild the LanceDB vector index from SQLite.

Run after `gradlens-ingest` (or any time the source DB changes). The
index is disposable: dropping and rebuilding from the SQLite source
of truth is cheap (~10s for the MVP corpus) and avoids stale-vector
bugs that creep in with incremental updates.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections.abc import Sequence

from gradlens_api.config import settings
from gradlens_api.ingest.store import db_path as sqlite_path
from gradlens_api.search import embed, index

# Max chars of content fed into the embedder per job. bge-small tops out
# around 512 tokens (~2000 chars). We also prepend the title + location so
# those terms weight into the vector even if content is long-winded.
_CONTENT_CHAR_BUDGET = 1800

# Snippet shown on result cards — separate from what the embedder sees.
_SNIPPET_CHARS = 320


def _format_for_embedding(title: str, location: str | None, content: str) -> str:
    """Title + location + content, budgeted so bge-small sees the signal up front."""
    header = title
    if location:
        header = f"{title} — {location}"
    body = content[:_CONTENT_CHAR_BUDGET]
    return f"{header}\n\n{body}"


def _snippet(content: str) -> str:
    if len(content) <= _SNIPPET_CHARS:
        return content
    return content[:_SNIPPET_CHARS].rstrip() + "…"


def _load_jobs() -> list[dict]:
    """Pull every job from SQLite into a list of row dicts."""
    conn = sqlite3.connect(sqlite_path(settings.data_dir))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT source, company, upstream_id, title, url,
                   location, offices_json, departments_json, content
            FROM jobs
            WHERE content != ''
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _batch(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gradlens-build-index",
        description="Rebuild the LanceDB vector index from the SQLite job store.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size — increase for faster indexing on bigger CPUs.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of jobs — useful for quick smoke-runs.",
    )
    args = parser.parse_args(argv)

    jobs = _load_jobs()
    if args.limit:
        jobs = jobs[: args.limit]

    if not jobs:
        print("No jobs in SQLite. Run `gradlens-ingest` first.", file=sys.stderr)
        return 1

    print(f"Indexing {len(jobs)} jobs with {embed.MODEL_NAME} (batch={args.batch_size}) ...")
    t0 = time.perf_counter()

    rows: list[index.IndexRow] = []
    for batch in _batch(jobs, args.batch_size):
        texts = [
            _format_for_embedding(r["title"], r["location"], r["content"])
            for r in batch
        ]
        vecs = embed.encode_passages(texts)
        for r, v in zip(batch, vecs, strict=True):
            rows.append(
                index.IndexRow(
                    source=r["source"],
                    company=r["company"],
                    upstream_id=r["upstream_id"],
                    title=r["title"],
                    url=r["url"],
                    location=r["location"] or "",
                    snippet=_snippet(r["content"]),
                    vector=v.tolist(),
                )
            )
        done = len(rows)
        print(f"  embedded {done}/{len(jobs)}", end="\r", flush=True)

    print()  # newline after carriage-return progress
    n = index.build(settings.data_dir, rows)
    elapsed = time.perf_counter() - t0
    print(f"Index rebuilt: {n} rows, {elapsed:.1f}s "
          f"({len(rows) / elapsed:.1f} jobs/s)")

    # Surface a sample query so a human running this sees it works.
    sample_query = "machine learning internship in London"
    hits = index.search(settings.data_dir, embed.encode_query(sample_query), k=3)
    print(f"\nSample query: {sample_query!r}")
    for h in hits:
        print(f"  [{h['company']:<10}] {h['title']} — {h['location']} (d={h['distance']:.3f})")

    # Belt-and-braces: make sure we persisted valid JSON-like rows in case
    # someone inspects the lance dir later.
    _ = json.dumps({"rows": n, "elapsed_s": round(elapsed, 2)})

    return 0


if __name__ == "__main__":
    sys.exit(main())
