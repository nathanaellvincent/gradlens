"""Query → results. The retrieval entry point used by the HTTP layer.

For MVP this is a pure first-stage search (embed query → LanceDB
nearest-neighbour → Hit list). A second-stage reranker slots in here
in a later commit without changing the caller contract.
"""

from __future__ import annotations

from pathlib import Path

from gradlens_api.search.embed import encode_query
from gradlens_api.search.index import Hit, search


def retrieve(query: str, data_dir: Path, *, k: int = 10) -> list[Hit]:
    """Semantic search entry point. Empty query yields an empty list."""
    query = query.strip()
    if not query:
        return []
    vec = encode_query(query)
    return search(data_dir, vec, k=k)
