"""RAG (Retrieval-Augmented Generation) module for policy retrieval."""

from .vector_store import initialize_collection, ingest_policies, query_policies

__all__ = [
    "initialize_collection",
    "ingest_policies",
    "query_policies",
]
