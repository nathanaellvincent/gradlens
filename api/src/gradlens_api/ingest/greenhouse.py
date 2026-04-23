"""Greenhouse Job Board API adapter.

Greenhouse exposes a public, unauthenticated read API at
`boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`. This
adapter pulls the listing, normalises each entry into the canonical
`Job` schema, and hands it to the caller.

Notes on the API shape:
- `jobs[].content` is HTML. We strip to plain text via stdlib
  `html.parser` — no bs4 dep — because the markup is already flat
  paragraphs and lists, nothing exotic to preserve.
- `jobs[].id` is an integer but we store as str because future sources
  (Ashby, Lever) use UUIDs and the downstream schema assumes string.
- `absolute_url` is the human-facing URL; we keep it as the canonical
  link so the UI can deep-link straight to the apply page.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime
from html.parser import HTMLParser

import httpx

from gradlens_api.ingest.models import Job

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
REQUEST_TIMEOUT = httpx.Timeout(20.0)


class _TextExtractor(HTMLParser):
    """Flatten HTML to text while preserving paragraph breaks."""

    _BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # noqa: ARG002
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        # Collapse the runaway whitespace that HTML stripping produces
        # (triple newlines, leading spaces per line, etc.) into something
        # the embedder can chew on without noise.
        lines = [line.strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def _strip_html(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(raw))
    return parser.text()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # Greenhouse returns ISO-8601 with tz offset, e.g. "2026-04-22T12:24:13-04:00".
    # fromisoformat handles this on Python 3.11+.
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fetch_company(slug: str, *, client: httpx.Client | None = None) -> list[Job]:
    """Fetch every currently-open job for one Greenhouse board.

    Raises `httpx.HTTPStatusError` on non-2xx so the CLI can surface
    per-company failures without aborting the whole run.
    """
    owned_client = client is None
    c = client or httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True)
    try:
        url = f"{BASE_URL}/{slug}/jobs"
        resp = c.get(url, params={"content": "true"})
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owned_client:
            c.close()

    now = datetime.now(tz=UTC)
    jobs: list[Job] = []
    for raw in payload.get("jobs", []):
        jobs.append(
            Job(
                source="greenhouse",
                company=slug,
                upstream_id=str(raw["id"]),
                title=raw["title"],
                url=raw["absolute_url"],
                location=(raw.get("location") or {}).get("name"),
                offices=[o["name"] for o in raw.get("offices", []) if o.get("name")],
                departments=[d["name"] for d in raw.get("departments", []) if d.get("name")],
                content=_strip_html(raw.get("content", "")),
                updated_at=_parse_dt(raw.get("updated_at")),
                first_published=_parse_dt(raw.get("first_published")),
                fetched_at=now,
            )
        )
    return jobs
