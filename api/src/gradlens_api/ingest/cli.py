"""Ingestion CLI — `uv run gradlens-ingest`.

Usage:
    gradlens-ingest                       # pull all curated companies
    gradlens-ingest stripe monzo          # pull specific slugs
    gradlens-ingest --list                # show curated companies + exit

The MVP company set is deliberately small (5) so a full ingest finishes
in <30s and re-running during dev is cheap. New slugs get added to
`CURATED_COMPANIES` below; the list is source-of-truth for the index's
scope.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import httpx

from gradlens_api.config import settings
from gradlens_api.ingest import greenhouse, store
from gradlens_api.ingest.models import IngestSummary

# Curated grad-scheme-friendly companies. Reasoning for each pick logged
# in ARCHITECTURE.md. Trimmed to 5 for MVP; next wave expands to ~20.
CURATED_COMPANIES: tuple[str, ...] = (
    "stripe",       # infra, strong new-grad programme
    "airbnb",       # consumer, new-grad SWE
    "monzo",        # UK fintech, grad schemes
    "cloudflare",   # infra, UK office presence
    "anthropic",    # AI/ML, research engineer + SWE grad
)


def _ingest_one(slug: str, *, client: httpx.Client) -> IngestSummary:
    summary = IngestSummary(
        source="greenhouse",
        company=slug,
        fetched=0,
        inserted=0,
        updated=0,
        skipped=0,
    )
    try:
        jobs = greenhouse.fetch_company(slug, client=client)
    except httpx.HTTPStatusError as exc:
        summary.errors.append(f"HTTP {exc.response.status_code} from upstream")
        return summary
    except httpx.HTTPError as exc:
        summary.errors.append(f"network error: {exc!r}")
        return summary

    summary.fetched = len(jobs)

    with store.connect(settings.data_dir) as conn:
        for job in jobs:
            # Skip entries with empty content — usually stubs created by
            # the ATS before the JD is written. Re-fetch will pick them
            # up once content lands.
            if not job.content.strip():
                summary.skipped += 1
                continue
            outcome = store.upsert_job(conn, job)
            if outcome == "inserted":
                summary.inserted += 1
            else:
                summary.updated += 1

    return summary


def _print_summary(summaries: Sequence[IngestSummary]) -> None:
    total_fetched = sum(s.fetched for s in summaries)
    total_inserted = sum(s.inserted for s in summaries)
    total_updated = sum(s.updated for s in summaries)
    total_skipped = sum(s.skipped for s in summaries)

    print()
    print(f"{'company':<15} {'fetched':>8} {'inserted':>9} {'updated':>8} {'skipped':>8}")
    print("-" * 54)
    for s in summaries:
        print(f"{s.company:<15} {s.fetched:>8} {s.inserted:>9} {s.updated:>8} {s.skipped:>8}")
        for err in s.errors:
            print(f"  ! {err}")
    print("-" * 54)
    print(
        f"{'TOTAL':<15} {total_fetched:>8} {total_inserted:>9} "
        f"{total_updated:>8} {total_skipped:>8}"
    )

    with store.connect(settings.data_dir) as conn:
        print(f"\nindex now contains {store.count_all(conn)} jobs across "
              f"{len(store.count_by_company(conn))} companies")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gradlens-ingest",
        description="Pull job descriptions from Greenhouse into the local SQLite store.",
    )
    parser.add_argument(
        "companies",
        nargs="*",
        help="Greenhouse board slugs to ingest. Defaults to the curated set.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the curated company list and exit.",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("Curated Greenhouse companies:")
        for c in CURATED_COMPANIES:
            print(f"  - {c}")
        return 0

    targets = tuple(args.companies) if args.companies else CURATED_COMPANIES
    print(f"Ingesting {len(targets)} company boards → {settings.data_dir}/jobs.db")

    summaries: list[IngestSummary] = []
    with httpx.Client(timeout=greenhouse.REQUEST_TIMEOUT, follow_redirects=True) as client:
        for slug in targets:
            print(f"  → {slug} ...", end=" ", flush=True)
            summary = _ingest_one(slug, client=client)
            if summary.errors:
                print(f"FAILED ({summary.errors[0]})")
            else:
                print(f"{summary.fetched} jobs")
            summaries.append(summary)

    _print_summary(summaries)

    # Non-zero exit if every company failed, so CI catches total outages.
    return 0 if any(s.fetched for s in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
