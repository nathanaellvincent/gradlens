"""SQLite store for ingested job descriptions.

Source of truth for metadata + content. The vector index (LanceDB) only
holds the embedding + IDs; everything human-readable lives here, so we
can rebuild the index from scratch without re-fetching from upstream.

Schema deliberately simple — single `jobs` table with a composite unique
key on (source, company, upstream_id). Upsert replaces the row so the
DB stays point-in-time (latest snapshot from upstream).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from gradlens_api.ingest.models import Job

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source            TEXT    NOT NULL,
    company           TEXT    NOT NULL,
    upstream_id       TEXT    NOT NULL,
    title             TEXT    NOT NULL,
    url               TEXT    NOT NULL,
    location          TEXT,
    offices_json      TEXT    NOT NULL DEFAULT '[]',
    departments_json  TEXT    NOT NULL DEFAULT '[]',
    content           TEXT    NOT NULL,
    updated_at        TEXT,
    first_published   TEXT,
    fetched_at        TEXT    NOT NULL,
    PRIMARY KEY (source, company, upstream_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
"""


def db_path(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "jobs.db"


@contextmanager
def connect(data_dir: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, ensure schema, yield. Commits on clean exit."""
    conn = sqlite3.connect(db_path(data_dir))
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_job(conn: sqlite3.Connection, job: Job) -> str:
    """Insert or replace one job. Returns 'inserted' | 'updated'."""
    existing = conn.execute(
        "SELECT 1 FROM jobs WHERE source = ? AND company = ? AND upstream_id = ?",
        (job.source, job.company, job.upstream_id),
    ).fetchone()

    conn.execute(
        """
        INSERT OR REPLACE INTO jobs (
            source, company, upstream_id, title, url, location,
            offices_json, departments_json, content,
            updated_at, first_published, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.source,
            job.company,
            job.upstream_id,
            job.title,
            str(job.url),
            job.location,
            json.dumps(job.offices),
            json.dumps(job.departments),
            job.content,
            job.updated_at.isoformat() if job.updated_at else None,
            job.first_published.isoformat() if job.first_published else None,
            job.fetched_at.isoformat(),
        ),
    )

    return "updated" if existing else "inserted"


def count_all(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def count_by_company(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT company, COUNT(*) FROM jobs GROUP BY company ORDER BY 2 DESC"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]
