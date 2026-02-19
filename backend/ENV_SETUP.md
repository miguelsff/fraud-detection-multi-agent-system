# Environment Configuration Guide

This project uses **environment-specific configuration files** for better separation between development, staging, and production environments.

## 📁 File Structure

```
backend/
├── .env                    # Base fallback (optional, git-ignored)
├── .env.development        # Local development (git-ignored)
├── .env.production         # Production/Azure (git-ignored)
└── .env.example            # Template with all variables (committed to git)
```

## 🚀 Quick Start

### 1. Initial Setup

Copy the example file to create your development environment:

```bash
cd backend
cp .env.example .env.development
```

Edit `.env.development` with your local configuration (PostgreSQL password, API keys, etc.)

### 2. Running the Application

The application automatically loads the correct `.env` file based on the `APP_ENV` environment variable:

**Development (default):**
```bash
# APP_ENV defaults to "development" if not set
python -m uv run uvicorn app.main:app --reload
```

**Production (Azure):**
```bash
export APP_ENV=production
python -m uv run uvicorn app.main:app
```

## 🔄 Configuration Priority

Configuration values are loaded in this order (highest priority first):

1. **System environment variables** (highest priority)
2. **`.env.{APP_ENV}` file** (e.g., `.env.production`)
3. **`.env` file** (fallback)
4. **Default values in `config.py`** (lowest priority)

### Example

If you have:
- `DATABASE_URL` set in system environment → **Uses this**
- `DATABASE_URL` in `.env.production` → Ignored (system env wins)
- `DATABASE_URL` in `.env` → Ignored (system env wins)

If you DON'T have `DATABASE_URL` in system env:
- `.env.production` value is used (when `APP_ENV=production`)

## 🌍 Environment-Specific Configuration

### Development (`.env.development`)

- **LLM**: Ollama (local)
- **Database**: Local PostgreSQL via Docker
- **ChromaDB**: Local file-based storage (`./data/chroma`)
- **Log Level**: DEBUG
- **CORS**: Allow `http://localhost:3000`
- **API**: http://localhost:8000

### Production (`terraform/main.tf` → Azure Container Apps)

- **LLM**: Azure OpenAI
- **Database**: Supabase PostgreSQL (via pooler)
- **ChromaDB**: Azure Files Share (`/app/data/chroma`)
- **Log Level**: INFO (configurable in Terraform)
- **CORS**: Production frontend URL (dynamic via Terraform)
- **Secrets**: Azure Key Vault (referenced by Terraform)

> `.env.production` mirrors these values for local simulation only.

## 🔐 Azure Container Apps (Production)

**Single Source of Truth**: `terraform/main.tf` defines all production environment variables.

- Non-secret values → hardcoded in Terraform `env {}` blocks
- Secrets (`DATABASE_PASSWORD`, `AZURE_OPENAI_API_KEY`, etc.) → Azure Key Vault, referenced via `secret_name` in Terraform

`.env.production` is **NOT deployed** to Azure (excluded by `.dockerignore`). It exists only for local simulation of production mode:
```bash
APP_ENV=production python -m uv run uvicorn app.main:app
```

If values in `.env.production` and `terraform/main.tf` differ, **Terraform wins** — it's what actually runs in Azure.

## 📋 Required Variables

See `.env.example` for the complete list of required variables. Key variables include:

### LLM Configuration
- `OLLAMA_BASE_URL` (development)
- `AZURE_OPENAI_ENDPOINT` (production/staging)
- `AZURE_OPENAI_KEY` (production/staging)
- `USE_AZURE_OPENAI` (true/false)

### Database
- `DATABASE_URL` (PostgreSQL connection string)

### App
- `APP_ENV` (development/staging/production)
- `LOG_LEVEL` (DEBUG/INFO/WARNING/ERROR)

### External APIs
- `OPENSANCTIONS_API_KEY` (optional, graceful degradation if missing)

## 🧪 Testing Configuration

To test configuration loading:

```python
from app.config import settings

print(f"Environment: {settings.app_env}")
print(f"Database URL: {settings.database_url.get_secret_value()}")
print(f"Using Azure OpenAI: {settings.use_azure_openai}")
```

## ⚠️ Security Best Practices

1. **NEVER commit** `.env`, `.env.development`, `.env.staging`, or `.env.production` to git
2. **ALWAYS use** `SecretStr` for sensitive values in `config.py`
3. **Store secrets** in Azure Key Vault for production (reference via Container Apps)
4. **Rotate credentials** regularly
5. **Use different credentials** for dev/staging/prod environments

## 🐛 Troubleshooting

### Wrong environment being loaded

Check that `APP_ENV` is set correctly:
```bash
echo $APP_ENV
```

### Configuration not being read

Verify the file exists and has the correct name:
```bash
ls -la backend/.env*
```

### Permission denied

Ensure `.env` files are readable:
```bash
chmod 600 backend/.env.development
```

## 📚 Additional Resources

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Azure Container Apps Environment Variables](https://learn.microsoft.com/en-us/azure/container-apps/environment-variables)
