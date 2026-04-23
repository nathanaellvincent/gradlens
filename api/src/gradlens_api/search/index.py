"""LanceDB vector index for semantic search.

LanceDB is an embedded, file-backed vector store — no separate server
process, which keeps the Fly.io deploy footprint minimal. The table
is denormalised: every row carries enough metadata (title, url,
location, company) to render a result card without a follow-up SQL
join. Full JD content stays in SQLite and is fetched lazily when the
LLM answer layer needs it (deferred milestone).

Schema evolution strategy: we drop-and-rebuild on index updates
rather than streaming upserts. With <2k jobs and ~5s rebuild time,
the simplicity is worth more than the incrementalism. Revisit if the
corpus grows past ~50k.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import lancedb
import numpy as np
import pyarrow as pa

from gradlens_api.search.embed import VECTOR_DIM

TABLE_NAME = "jobs"


class IndexRow(TypedDict):
    """Row payload going into LanceDB. Keep in sync with `_arrow_schema`."""

    source: str
    company: str
    upstream_id: str
    title: str
    url: str
    location: str
    snippet: str  # first ~300 chars of content, for result-card preview
    vector: list[float]


class Hit(TypedDict):
    """Search result — mirrors IndexRow minus the vector, plus a distance."""

    source: str
    company: str
    upstream_id: str
    title: str
    url: str
    location: str
    snippet: str
    distance: float  # L2 distance; lower is better


def _arrow_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("source", pa.string()),
            pa.field("company", pa.string()),
            pa.field("upstream_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("url", pa.string()),
            pa.field("location", pa.string()),
            pa.field("snippet", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
        ]
    )


def _lance_dir(data_dir: Path) -> Path:
    return data_dir / "lance"


def open_db(data_dir: Path) -> lancedb.DBConnection:
    _lance_dir(data_dir).mkdir(parents=True, exist_ok=True)
    return lancedb.connect(_lance_dir(data_dir))


def build(data_dir: Path, rows: list[IndexRow]) -> int:
    """Drop-and-rebuild the jobs table. Returns row count."""
    db = open_db(data_dir)
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
    table = db.create_table(TABLE_NAME, data=rows, schema=_arrow_schema())
    return len(table)


def search(data_dir: Path, query_vec: np.ndarray, k: int = 10) -> list[Hit]:
    """Vector search — returns top-k rows by L2 distance."""
    db = open_db(data_dir)
    if TABLE_NAME not in db.table_names():
        return []

    table = db.open_table(TABLE_NAME)
    results = (
        table.search(query_vec.tolist())
        .metric("l2")
        .limit(k)
        .to_list()
    )

    hits: list[Hit] = []
    for r in results:
        hits.append(
            Hit(
                source=r["source"],
                company=r["company"],
                upstream_id=r["upstream_id"],
                title=r["title"],
                url=r["url"],
                location=r["location"],
                snippet=r["snippet"],
                distance=float(r["_distance"]),
            )
        )
    return hits


def row_count(data_dir: Path) -> int:
    db = open_db(data_dir)
    if TABLE_NAME not in db.table_names():
        return 0
    return db.open_table(TABLE_NAME).count_rows()
