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

### Production (`.env.production`)

- **LLM**: Azure OpenAI
- **Database**: Azure PostgreSQL Flexible Server
- **ChromaDB**: Azure Files Share (`/mnt/chromadb`)
- **Log Level**: INFO
- **CORS**: Production frontend URL (Azure Container Apps)
- **API**: https://ca-fraudguard-backend.blacksea-a48ea308.westus2.azurecontainerapps.io

## 🔐 Azure Container Apps

When deploying to Azure Container Apps, you can:

1. **Option A**: Include `.env.production` in the container image (not recommended for secrets)
2. **Option B**: Set environment variables in Azure Container Apps (recommended)

Azure Container Apps environment variables will **override** values in `.env.production`.

### Setting Environment Variables in Azure

```bash
az containerapp update \
  --name ca-fraudguard-backend \
  --resource-group rg-fraudguard-dev \
  --set-env-vars \
    APP_ENV=production \
    DATABASE_URL=secretref:database-url \
    AZURE_OPENAI_KEY=secretref:azure-openai-key
```

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
