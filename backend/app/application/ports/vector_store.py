"""Vector store port — interface for policy RAG operations."""

from typing import Protocol


class VectorStorePort(Protocol):
    """Port for vector store operations (policy retrieval and ingestion)."""

    def query(self, query: str, n_results: int = 5) -> list[dict]:
        """Query the vector store for relevant fraud policies.

        Args:
            query: Natural language query describing transaction characteristics.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: id, text, metadata, score (0-1, higher is better).
            Empty list if no results or on error.
        """
        ...

    def ingest(self, policies_dir: str) -> int:
        """Ingest fraud policy markdown files into the vector store.

        Args:
            policies_dir: Path to directory containing .md policy files.

        Returns:
            Number of chunks ingested.
        """
        ...
