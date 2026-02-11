"""Central configuration loaded from environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from environment variables.

    Reads from a ``.env`` file located in the backend directory.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Database
    database_url: str = "postgresql+asyncpg://fraud_user:fraud_pass_dev@localhost:5432/fraud_detection"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # App
    app_env: str = "development"
    log_level: str = "DEBUG"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
