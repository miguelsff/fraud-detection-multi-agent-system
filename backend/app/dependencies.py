"""Dependency factories for FastAPI injection."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    import chromadb

from .config import settings

# ---------------------------------------------------------------------------
# SQLAlchemy async engine & session factory (module-level singletons)
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.database_url.get_secret_value(), echo=(settings.app_env == "development")
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
        use_gpt4: DEPRECATED - Ignored when using single Azure OpenAI deployment.
                  Kept for backward compatibility.

    Returns:
        BaseChatModel: Either ChatOllama (local) or AzureChatOpenAI (cloud)

    Note:
        When using Azure OpenAI with a single advanced model (e.g., GPT-5.2),
        the use_gpt4 parameter is ignored as the same deployment handles all requests.
    """
    if settings.use_azure_openai:
        # Azure OpenAI for cloud production
        if not settings.azure_openai_endpoint or not settings.azure_openai_key.get_secret_value():
            raise ValueError(
                "USE_AZURE_OPENAI=true but AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY not configured"
            )

        # Use single deployment for all LLM requests
        # Fallback to deprecated config for backward compatibility
        deployment_name = (
            settings.azure_openai_deployment or
            settings.azure_openai_gpt4_deployment or
            settings.azure_openai_gpt35_deployment
        )

        if not deployment_name:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT not configured")

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key.get_secret_value(),
            deployment_name=deployment_name,
            api_version="2025-01-01-preview-preview",  # Updated for GPT-5.2 support
            temperature=0.1,  # Low temperature for deterministic fraud detection
        )
    else:
        # Ollama for local development
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
