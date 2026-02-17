# DevOps Configuration

Development and deployment configurations for the Fraud Detection Multi-Agent System.

---

## 📁 Docker Compose Files

### `docker-compose.yml` (Development)

**Purpose:** Local development environment
**Location:** `devops/docker-compose.yml`
**Services:** PostgreSQL only

**Usage:**
```bash
# Start PostgreSQL for development
docker compose -f devops/docker-compose.yml up -d

# Or use Makefile shortcut
make setup
```

**Why only PostgreSQL?**
- Backend runs locally with `uvicorn --reload` for hot-reload
- Frontend runs locally with `npm run dev` for fast refresh
- Only the database needs to be containerized for development

**Services:**
- **postgres** - PostgreSQL 16 (Alpine)
  - Port: 5432
  - User: `fraud_user`
  - Password: `fraud_pass_dev`
  - Database: `fraud_detection`
  - Volume: `pgdata` (persistent)

---

### `../docker-compose.prod.yml` (Production)

**Purpose:** Full-stack deployment (CI/CD, staging, production)
**Location:** `docker-compose.prod.yml` (project root)
**Services:** PostgreSQL + Backend + Frontend

**Usage:**
```bash
# Start full stack
docker compose -f docker-compose.prod.yml up -d

# Build and start
docker compose -f docker-compose.prod.yml up --build -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop all services
docker compose -f docker-compose.prod.yml down
```

**Services:**
1. **postgres** - PostgreSQL 16
   - Port: 5432
   - Health check enabled

2. **backend** - FastAPI application
   - Port: 8000
   - Depends on: postgres
   - Environment: production
   - Ollama URL: `http://host.docker.internal:11434`

3. **frontend** - Next.js application
   - Port: 3000
   - Depends on: backend
   - API URL: `http://localhost:8000`

**Network:**
- `fraud-network` (bridge) - Isolates services

---

## 🚀 Quick Start

### Development Workflow

```bash
# 1. Start PostgreSQL
make setup

# 2. Run backend locally (hot-reload)
make dev

# 3. Run frontend locally (separate terminal)
cd frontend && npm run dev
```

### Production Deployment

```bash
# 1. Build and start all services
docker compose -f docker-compose.prod.yml up --build -d

# 2. Verify health
docker compose -f docker-compose.prod.yml ps

# 3. Check logs
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 🔧 Environment Variables

### Development (devops/docker-compose.yml)
```env
POSTGRES_USER=fraud_user
POSTGRES_PASSWORD=fraud_pass_dev
POSTGRES_DB=fraud_detection
```

### Production (docker-compose.prod.yml)
```env
# Database
DATABASE_URL=postgresql+asyncpg://fraud_user:fraud_pass_dev@postgres:5432/fraud_detection

# LLM Config
LLM_MODEL=llama3.2:3b
LLM_BASE_URL=http://host.docker.internal:11434

# App Config
ENVIRONMENT=production
LOG_LEVEL=info

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NODE_ENV=production
```

---

## 🔍 Troubleshooting

### PostgreSQL not starting

```bash
# Check logs
docker compose -f devops/docker-compose.yml logs postgres

# Reset database (WARNING: deletes all data)
make db-reset
```

### Backend can't connect to Ollama

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
make ollama

# Pull model
ollama pull llama3.2
```

### Port conflicts

```bash
# Check what's using port 5432
netstat -ano | findstr :5432  # Windows
lsof -i :5432                  # macOS/Linux

# Stop existing PostgreSQL
docker compose -f devops/docker-compose.yml down
```

---

## 📊 Health Checks

All services include health checks for orchestration:

**PostgreSQL:**
```bash
pg_isready -U fraud_user -d fraud_detection
```

**Backend:**
```bash
curl -f http://localhost:8000/api/v1/health
```

**Frontend:**
```bash
curl -f http://localhost:3000
```

---

## 🗂️ Volumes

### pgdata (PostgreSQL Data)

**Type:** Named volume (persistent)
**Location:** Docker managed
**Backup:**
```bash
# Export database
docker exec fraud-db pg_dump -U fraud_user fraud_detection > backup.sql

# Restore database
docker exec -i fraud-db psql -U fraud_user fraud_detection < backup.sql
```

---

## 🌐 Networks

### fraud-network (Bridge)

**Driver:** bridge
**Purpose:** Isolate fraud detection services from other Docker containers

**Inspect:**
```bash
docker network inspect fraud-network
```

---

## 📝 Best Practices

1. **Development**: Use `devops/docker-compose.yml` + local backend/frontend
2. **CI/CD**: Use `docker-compose.prod.yml` for integration tests
3. **Production**: Use Terraform + Azure Container Apps (not docker-compose)
4. **Secrets**: Never commit real passwords — use `.env` files or secret managers
5. **Logs**: Use `docker compose logs -f` to debug container issues

---

## 🔐 Security Notes

⚠️ **The default password `fraud_pass_dev` is for DEVELOPMENT ONLY**

For production:
- Use strong passwords (min 32 chars, random)
- Store in Azure Key Vault or AWS Secrets Manager
- Enable SSL/TLS for PostgreSQL connections
- Use Docker secrets (not environment variables)

Example production setup:
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

secrets:
  db_password:
    external: true
```

---

## 📚 References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Docker](https://nextjs.org/docs/deployment#docker-image)
