"""Dependency factories for FastAPI injection."""

from collections.abc import AsyncGenerator

from typing import TYPE_CHECKING

from langchain_ollama import ChatOllama
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    import chromadb

from .config import settings

# ---------------------------------------------------------------------------
# SQLAlchemy async engine & session factory (module-level singletons)
# ---------------------------------------------------------------------------
engine = create_async_engine(settings.database_url, echo=(settings.app_env == "development"))
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, ensuring cleanup on exit."""
    async with async_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def get_llm() -> ChatOllama:
    """Return a ChatOllama instance configured from settings."""
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
def get_chroma() -> "chromadb.ClientAPI":
    """Return a persistent ChromaDB client."""
    import chromadb

    return chromadb.PersistentClient(path=settings.chroma_persist_dir)
