"""Dependency factories for FastAPI injection."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    import chromadb

from .config import settings

# ---------------------------------------------------------------------------
# SQLAlchemy async engine & session factory (module-level singletons)
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.effective_database_url, echo=(settings.app_env == "development")
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, ensuring cleanup on exit."""
    async with async_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# LLM Factory (Ollama for local dev, Azure OpenAI for cloud production)
# ---------------------------------------------------------------------------
def get_llm(use_gpt4: bool = False) -> BaseChatModel:
    """Return LLM instance based on configuration.

    Args:
        use_gpt4: DEPRECATED - Ignored. Kept for backward compatibility.

    Returns:
        BaseChatModel: Either ChatOllama (local) or ChatOpenAI (Azure endpoint)
    """
    if settings.use_azure_openai:
        if not settings.azure_openai_endpoint:
            raise ValueError("USE_AZURE_OPENAI=true but AZURE_OPENAI_ENDPOINT not configured")

        # Azure OpenAI via OpenAI-compatible endpoint (/openai/v1/)
        base_url = settings.azure_openai_endpoint.rstrip('/') + '/openai/v1/'

        return ChatOpenAI(
            base_url=base_url,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            model=settings.azure_openai_deployment,  # deployment name as model
            temperature=0.1,
        )
    else:
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1,
        )


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
def get_chroma() -> "chromadb.ClientAPI":
    """Return a persistent ChromaDB client."""
    import chromadb

    return chromadb.PersistentClient(path=settings.chroma_persist_dir)
