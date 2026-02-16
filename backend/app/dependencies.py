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
        use_gpt4: If True and using Azure OpenAI, return GPT-4 deployment.
                  If False, return GPT-3.5 Turbo deployment (cheaper).
                  Ignored when using Ollama.

    Returns:
        BaseChatModel: Either ChatOllama (local) or AzureChatOpenAI (cloud)

    Cost-optimized strategy (Azure OpenAI):
        - Simple agents (PolicyRAG, ExternalThreat, ProFraud, ProCustomer):
          use_gpt4=False → GPT-3.5 Turbo (~$0.002/1K tokens)
        - Critical agents (DecisionArbiter, Explainability):
          use_gpt4=True → GPT-4 (~$0.03/1K tokens)
    """
    if settings.use_azure_openai:
        # Azure OpenAI for cloud production
        if not settings.azure_openai_endpoint or not settings.azure_openai_key.get_secret_value():
            raise ValueError(
                "USE_AZURE_OPENAI=true but AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY not configured"
            )

        deployment_name = (
            settings.azure_openai_gpt4_deployment if use_gpt4
            else settings.azure_openai_gpt35_deployment
        )

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key.get_secret_value(),
            deployment_name=deployment_name,
            api_version="2024-02-01",
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
