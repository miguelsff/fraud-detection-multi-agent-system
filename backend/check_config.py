#!/usr/bin/env python3
"""
Configuration validation script.
Checks that all required environment variables are set and valid.

Usage:
    python check_config.py
    APP_ENV=production python check_config.py
"""

import sys
from pathlib import Path


def main() -> int:
    """Validate configuration and print summary."""
    try:
        from app.config import settings
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1

    print("=" * 60)
    print("Configuration Summary")
    print("=" * 60)

    # Environment info
    print(f"\n📍 Environment: {settings.app_env}")
    print(f"📝 Log Level: {settings.log_level}")
    print(f"🌐 API Host: {settings.api_host}:{settings.api_port}")

    # Check which .env file was loaded
    backend_dir = Path(__file__).parent
    env_file = backend_dir / f".env.{settings.app_env}"
    if env_file.exists():
        print(f"✅ Loaded: .env.{settings.app_env}")
    else:
        print(f"⚠️  File not found: .env.{settings.app_env} (using defaults)")

    # LLM Configuration
    print("\n🤖 LLM Configuration:")
    if settings.use_azure_openai:
        print(f"   Provider: Azure OpenAI")
        print(f"   Endpoint: {settings.azure_openai_endpoint or '❌ NOT SET'}")
        print(f"   Deployment: {settings.azure_openai_deployment}")
        print(f"   API Key: {'✅ Set' if settings.azure_openai_key.get_secret_value() else '❌ NOT SET'}")
    else:
        print(f"   Provider: Ollama (local)")
        print(f"   Base URL: {settings.ollama_base_url}")
        print(f"   Model: {settings.ollama_model}")

    # Database
    print("\n💾 Database:")
    db_url = settings.database_url.get_secret_value()
    if db_url:
        # Hide password in output
        if "@" in db_url:
            parts = db_url.split("@")
            masked = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]
            print(f"   URL: {masked}")
        else:
            print(f"   URL: {db_url}")
    else:
        print("   ❌ DATABASE_URL not set")

    # ChromaDB
    print("\n📚 ChromaDB:")
    print(f"   Persist Dir: {settings.chroma_persist_dir}")
    if settings.chroma_azure_storage_account:
        print(f"   Azure Storage: {settings.chroma_azure_storage_account}")
        print(f"   Share Name: {settings.chroma_azure_share_name}")
    else:
        print("   Azure Storage: Not configured (using local storage)")

    # CORS
    print("\n🔐 CORS Origins:")
    print(f"   Production: {settings.cors_frontend_prod_url}")
    print(f"   Staging: {settings.cors_frontend_staging_url}")

    # External APIs
    print("\n🌐 External APIs:")
    has_sanctions_key = bool(settings.opensanctions_api_key.get_secret_value())
    print(f"   OpenSanctions: {'✅ Key set' if has_sanctions_key else '⚠️  No key (graceful degradation)'}")

    # Feature Flags
    print("\n🚩 Feature Flags:")
    print(f"   OSINT: {'✅ Enabled' if settings.threat_intel_enable_osint else '❌ Disabled'}")
    print(f"   Sanctions: {'✅ Enabled' if settings.threat_intel_enable_sanctions else '❌ Disabled'}")
    print(f"   OSINT Max Results: {settings.threat_intel_osint_max_results}")

    # Warnings
    warnings = []

    if settings.app_env == "production":
        if not settings.use_azure_openai:
            warnings.append("⚠️  Production is using Ollama instead of Azure OpenAI")
        if settings.log_level == "DEBUG":
            warnings.append("⚠️  Production is using DEBUG log level (should be INFO)")
        if "localhost" in db_url:
            warnings.append("⚠️  Production is using localhost database")

    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   {warning}")

    print("\n" + "=" * 60)
    print("✅ Configuration loaded successfully!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
