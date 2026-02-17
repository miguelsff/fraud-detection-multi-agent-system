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
    settings.effective_database_url, echo=(settings.app_env == "development")
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, ensuring cleanup on exit."""
    async with async_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Azure AD Token Provider (lazy singleton — same pattern as get_chroma)
# ---------------------------------------------------------------------------
_token_provider = None


def _get_azure_token_provider():
    """Return a cached Azure AD token provider for Cognitive Services."""
    global _token_provider
    if _token_provider is None:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        credential = DefaultAzureCredential(
            managed_identity_client_id=settings.azure_client_id or None,
        )
        _token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    return _token_provider


# ---------------------------------------------------------------------------
# LLM Factory (Ollama for local dev, Azure OpenAI for cloud production)
# ---------------------------------------------------------------------------
def get_llm(use_gpt4: bool = False) -> BaseChatModel:
    """Return LLM instance based on configuration.

    Args:
        use_gpt4: DEPRECATED - Ignored. Kept for backward compatibility.

    Returns:
        BaseChatModel: Either ChatOllama (local) or AzureChatOpenAI (cloud)
    """
    if settings.use_azure_openai:
        if not settings.azure_openai_endpoint:
            raise ValueError(
                "USE_AZURE_OPENAI=true but AZURE_OPENAI_ENDPOINT not configured"
            )

        deployment_name = settings.azure_openai_deployment
        if not deployment_name:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT not configured")

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=_get_azure_token_provider(),
            deployment_name=deployment_name,
            api_version=settings.azure_openai_api_version,
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
