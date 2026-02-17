"""Central configuration loaded from environment variables / .env file."""

import os
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from environment variables.

    Reads from environment-specific .env files:
    - .env.development (local development)
    - .env.production (production/Azure)

    Falls back to .env if environment-specific file doesn't exist.
    Environment variables always take precedence over .env files.
    """

    model_config = SettingsConfigDict(
        env_file=[
            # Base configuration (lowest priority)
            Path(__file__).resolve().parent.parent / ".env",
            # Environment-specific (higher priority, overrides base)
            Path(__file__).resolve().parent.parent / f".env.{os.getenv('APP_ENV', 'development')}",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM - Ollama (for local/dev)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:30b"

    # Azure OpenAI (for cloud production)
    azure_openai_endpoint: str = ""
    azure_openai_key: SecretStr = SecretStr("")
    azure_openai_deployment: str = "gpt-5.2-chat"  # Single deployment name
    azure_openai_gpt4_deployment: str = ""  # DEPRECATED: Use azure_openai_deployment
    azure_openai_gpt35_deployment: str = ""  # DEPRECATED: Use azure_openai_deployment
    use_azure_openai: bool = False  # Feature flag

    # Database
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://fraud_user:fraud_pass_dev@localhost:5432/fraud_detection"
    )

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_azure_storage_account: str = ""
    chroma_azure_share_name: str = "chromadb-share"

    # App
    app_env: Literal["development", "production"] = "development"
    log_level: str = "DEBUG"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS - Frontend origins (production/staging)
    cors_frontend_prod_url: str = "https://ca-fraud-frontend-prod.azurecontainerapps.io"
    cors_frontend_staging_url: str = "https://ca-fraud-frontend-staging.azurecontainerapps.io"

    # Threat Intelligence APIs
    opensanctions_api_key: SecretStr = SecretStr("")

    # Threat Intelligence Feature Flags
    threat_intel_enable_osint: bool = True
    threat_intel_enable_sanctions: bool = True
    threat_intel_osint_max_results: int = 5


settings = Settings()
