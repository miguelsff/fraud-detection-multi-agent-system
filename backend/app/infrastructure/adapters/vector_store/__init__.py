"""Vector store adapter package.

Provides ChromaDBVectorStoreAdapter and standalone convenience functions
(initialize_collection, ingest_policies, query_policies) for backward
compatibility with code that used the old rag.vector_store module.
"""

from .chromadb_adapter import ChromaDBVectorStoreAdapter
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "ChromaDBVectorStoreAdapter",
    "initialize_collection",
    "ingest_policies",
    "query_policies",
]

# Lazy singleton adapter for standalone functions
_adapter: ChromaDBVectorStoreAdapter | None = None


def _get_adapter() -> ChromaDBVectorStoreAdapter:
    global _adapter
    if _adapter is None:
        import chromadb

        if settings.chroma_use_http:
            client = chromadb.HttpClient(
                host=settings.chroma_host, port=settings.chroma_port
            )
        else:
            client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _adapter = ChromaDBVectorStoreAdapter(chroma_client=client)
    return _adapter


def initialize_collection():
    """Initialize or get the fraud_policies ChromaDB collection."""
    return _get_adapter()._get_collection()


def ingest_policies(policies_dir: str = "./policies") -> int:
    """Ingest fraud policy markdown files into ChromaDB."""
    return _get_adapter().ingest(policies_dir)


def query_policies(query: str, n_results: int = 5) -> list[dict]:
    """Query ChromaDB for relevant fraud policies."""
    return _get_adapter().query(query, n_results=n_results)
