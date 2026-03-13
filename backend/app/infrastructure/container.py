"""Composition root — manual dependency injection container.

Creates and wires all adapters from Settings. No DI framework needed.
"""

from functools import cached_property
from pathlib import Path

from .adapters.broadcast import WebSocketBroadcastAdapter
from .adapters.llm import LangChainLLMAdapter
from .adapters.persistence import SQLAlchemyPersistenceAdapter
from .adapters.vector_store import ChromaDBVectorStoreAdapter
from app.config import Settings
from .adapters.persistence.engine import async_session, init_db
from .adapters.broadcast.connection_manager import manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Container:
    """Application-level dependency container.

    Lazily initializes adapters from settings. Thread-safe via cached_property.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @cached_property
    def llm_port(self) -> LangChainLLMAdapter:
        return LangChainLLMAdapter(
            use_azure_openai=self.settings.use_azure_openai,
            ollama_base_url=self.settings.ollama_base_url,
            ollama_model=self.settings.ollama_model,
            azure_openai_endpoint=self.settings.azure_openai_endpoint,
            azure_openai_api_key=self.settings.azure_openai_api_key.get_secret_value(),
            azure_openai_deployment=self.settings.azure_openai_deployment,
        )

    @cached_property
    def persistence(self) -> SQLAlchemyPersistenceAdapter:
        return SQLAlchemyPersistenceAdapter(session_factory=async_session)

    @cached_property
    def vector_store(self) -> ChromaDBVectorStoreAdapter:
        import chromadb

        if self.settings.chroma_use_http:
            client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port,
            )
        else:
            client = chromadb.PersistentClient(path=self.settings.chroma_persist_dir)

        return ChromaDBVectorStoreAdapter(chroma_client=client)

    @cached_property
    def broadcast(self) -> WebSocketBroadcastAdapter:
        return WebSocketBroadcastAdapter(connection_manager=manager)

    async def initialize(self) -> None:
        """Run startup initialization (DB tables + policy ingestion)."""
        await init_db()
        logger.info("database_initialized")

        try:
            policies_dir = Path(__file__).parent.parent.parent / "policies"
            if policies_dir.exists():
                count = self.vector_store.ingest(str(policies_dir))
                logger.info("rag_policies_ingested", count=count)
            else:
                logger.warning("policies_directory_not_found", path=str(policies_dir))
        except Exception as e:
            logger.error("rag_ingestion_failed", error=str(e))

    def build_pipeline_config(self, transaction_id: str) -> dict:
        """Build configurable dict for LangGraph pipeline invocation."""
        return {
            "llm_port": self.llm_port,
            "persistence": self.persistence,
            "vector_store": self.vector_store,
            "broadcast": self.broadcast,
            "transaction_id": transaction_id,
        }
