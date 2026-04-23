"""Semantic search — embeddings + vector index + retrieval.

Stages:
  1. embed.py    — bge-small-en-v1.5 via fastembed (ONNX, CPU)
  2. index.py    — LanceDB table, one row per job
  3. retrieve.py — query → vector → top-k (adds reranker in a later commit)
"""
