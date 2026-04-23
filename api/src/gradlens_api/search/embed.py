"""Embedding model — `BAAI/bge-small-en-v1.5` via fastembed (ONNX, CPU).

Why fastembed over sentence-transformers:
- ~10x smaller install footprint (no torch), matters for Fly.io deploy
- ONNX runtime ≈ torch CPU throughput for this model size
- Identical output vectors — same model weights, just a thinner runtime

bge-small-en-v1.5 is asymmetric: queries get a short instruction prefix
that nudges the encoder toward a retrieval-friendly representation;
passages (job descriptions) are encoded raw. Mixing these up silently
hurts recall, so we expose two dedicated entry points rather than one
generic `encode()`.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384  # bge-small embedding dimensionality

# Per the model card — without this prefix, cross-modal (query vs passage)
# similarity scores drop noticeably. The passage side takes no prefix.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    """Lazily load the embedding model on first use, cache for the process.

    First load downloads ~130MB of ONNX weights to the HuggingFace cache.
    Subsequent process starts are fast (disk read + ONNX session init).
    """
    return TextEmbedding(model_name=MODEL_NAME)


def encode_passages(texts: list[str]) -> np.ndarray:
    """Encode a batch of passages (job descriptions). Returns (N, 384) float32."""
    if not texts:
        return np.zeros((0, VECTOR_DIM), dtype=np.float32)
    vecs = list(_model().embed(texts))
    return np.asarray(vecs, dtype=np.float32)


def encode_query(text: str) -> np.ndarray:
    """Encode a single user query. Returns (384,) float32."""
    prefixed = _QUERY_PREFIX + text
    vec = next(iter(_model().embed([prefixed])))
    return np.asarray(vec, dtype=np.float32)
