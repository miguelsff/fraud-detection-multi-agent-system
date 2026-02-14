# Docker Deployment Guide

This guide explains how to build and deploy the Fraud Detection Multi-Agent System using Docker.

## Overview

The system consists of three containerized services:

1. **PostgreSQL Database** - Stores transaction records, decisions, and HITL cases
2. **FastAPI Backend** - Python 3.13 + LangGraph multi-agent pipeline
3. **Next.js Frontend** - React 18 + TypeScript UI

All services are orchestrated via `docker-compose.prod.yml` with health checks and automatic dependency management.

**Note:** For local development, use `devops/docker-compose.yml` (PostgreSQL only) and run backend/frontend locally with hot-reload. This guide covers **production deployment** with all services containerized.

---

## Prerequisites

- **Docker**: Version 24.0+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 2.20+ (included with Docker Desktop)
- **Ollama** (optional): For local LLM inference ([Install Ollama](https://ollama.ai))

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended for LLM inference)
- **Storage**: 5GB free space
- **Ports**: 3000 (frontend), 8000 (backend), 5432 (database)

---

## Quick Start

### 1. Build and Start All Services

```bash
# From project root
make docker-all
```

This command:
- Builds Docker images for backend and frontend
- Starts PostgreSQL, backend, and frontend containers
- Runs database migrations
- Sets up networking between services

### 2. Access the Application

Once all services are healthy (30-60 seconds):

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: `postgresql://fraud_user:fraud_pass_dev@localhost:5432/fraud_detection`

### 3. Verify Services

```bash
# Check all services are running
docker compose ps

# View logs
make docker-logs

# Or view logs for specific service
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f postgres
```

---

## Makefile Commands

### Development

```bash
make frontend         # Run Next.js dev server (port 3000)
make dev              # Run FastAPI dev server (port 8000)
make build-frontend   # Build Next.js production bundle
```

### Docker Operations

```bash
make docker-all       # Build and start all services
make docker-build     # Build Docker images only
make docker-up        # Start services (no rebuild)
make docker-down      # Stop all services
make docker-logs      # View logs from all services
```

### Database & Testing

```bash
make ingest           # Ingest fraud policies into ChromaDB
make seed             # Seed database with synthetic data
make test             # Run all tests
make db-reset         # Reset database (WARNING: deletes data)
```

### Cleanup

```bash
make clean            # Remove build artifacts and caches
docker compose down -v  # Stop and remove volumes (full cleanup)
```

---

## Docker Architecture

### Multi-Stage Builds

Both backend and frontend use optimized multi-stage Dockerfiles:

#### Frontend (Next.js)
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Runtime
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
USER nextjs
CMD ["node", "server.js"]
```

**Benefits:**
- ✅ Standalone output (~50MB vs ~500MB)
- ✅ No dev dependencies in production
- ✅ Optimized layer caching
- ✅ Non-root user for security

#### Backend (FastAPI)
```dockerfile
FROM python:3.13-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev
COPY . .
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

**Benefits:**
- ✅ Fast dependency installation with uv
- ✅ No test/dev dependencies
- ✅ Automatic migrations on startup
- ✅ Non-root user for security

### Network Configuration

All services are connected via `fraud-network` bridge network:

```yaml
networks:
  fraud-network:
    driver: bridge
```

**Service Communication:**
- Frontend → Backend: `http://backend:8000`
- Backend → Database: `postgresql://postgres:5432`
- External → Services: Via exposed ports (3000, 8000, 5432)

### Health Checks

All services have health checks for reliable startup:

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U fraud_user"]
  interval: 5s
  timeout: 3s
  retries: 5

# Backend
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  start_period: 40s

# Frontend
healthcheck:
  test: ["CMD-SHELL", "node -e 'require(\"http\").get(...)'"]
  interval: 30s
  timeout: 10s
```

**Startup Sequence:**
1. PostgreSQL starts and waits for `pg_isready`
2. Backend waits for PostgreSQL health check
3. Frontend waits for Backend health check

---

## Environment Variables

### Backend (`backend/.env`)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://fraud_user:fraud_pass_dev@postgres:5432/fraud_detection

# LLM Configuration
LLM_MODEL=llama3.2:3b
LLM_BASE_URL=http://host.docker.internal:11434

# Application
ENVIRONMENT=production
LOG_LEVEL=info
```

### Frontend (Build-time)

Set in `docker-compose.yml`:

```yaml
environment:
  NEXT_PUBLIC_API_URL: http://localhost:8000
  NEXT_PUBLIC_WS_URL: ws://localhost:8000
  NODE_ENV: production
```

**Note:** `NEXT_PUBLIC_*` variables are embedded at build time. To change them, rebuild the image.

---

## Production Deployment

### 1. Update Environment Variables

Create production `.env` files:

```bash
# backend/.env.production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/fraud_detection
LLM_MODEL=llama3.2:3b
LLM_BASE_URL=http://ollama-server:11434
ENVIRONMENT=production
LOG_LEVEL=warning
```

### 2. Update docker-compose.yml

```yaml
# docker-compose.prod.yml
services:
  backend:
    env_file:
      - backend/.env.production

  frontend:
    environment:
      NEXT_PUBLIC_API_URL: https://api.yourdomain.com
      NEXT_PUBLIC_WS_URL: wss://api.yourdomain.com
```

### 3. Build and Deploy

```bash
# Build with production config
docker compose -f docker-compose.prod.yml build

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Verify
docker compose -f docker-compose.prod.yml ps
```

### 4. Reverse Proxy (Nginx Example)

```nginx
# nginx.conf
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /api/v1/ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Troubleshooting

### Services Won't Start

1. **Check port conflicts**:
   ```bash
   # Check if ports are in use
   netstat -ano | findstr :3000
   netstat -ano | findstr :8000
   netstat -ano | findstr :5432
   ```

2. **Check Docker resources**:
   - Docker Desktop → Settings → Resources
   - Increase RAM allocation to 8GB+

3. **View service logs**:
   ```bash
   docker compose logs backend
   docker compose logs frontend
   ```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U fraud_user -d fraud_detection -c "SELECT 1;"
```

### Backend Won't Connect to Ollama

If using local Ollama on host machine:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      LLM_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Frontend Can't Reach Backend

1. **Check backend health**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Verify environment variables**:
   ```bash
   docker compose exec frontend printenv | grep NEXT_PUBLIC
   ```

3. **Rebuild if needed**:
   ```bash
   docker compose build frontend
   docker compose up -d frontend
   ```

### Out of Disk Space

```bash
# Remove unused images and containers
docker system prune -a

# Remove all volumes (WARNING: deletes data)
docker compose down -v
```

---

## Performance Optimization

### Layer Caching

Both Dockerfiles are optimized for layer caching:

1. **Copy package files first** → Cached if dependencies don't change
2. **Install dependencies** → Cached layer
3. **Copy source code** → Only rebuilds if code changes

### Build Time Optimization

```bash
# Use BuildKit for parallel builds
DOCKER_BUILDKIT=1 docker compose build

# Build specific service
docker compose build backend
docker compose build frontend
```

### Runtime Optimization

1. **Limit container resources**:
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 4G
   ```

2. **Use volumes for development** (hot-reload):
   ```yaml
   services:
     backend:
       volumes:
         - ./backend/app:/app/app  # Mount source code
   ```

---

## Monitoring

### Health Check Status

```bash
# Check health status
docker compose ps

# Continuous monitoring
watch -n 5 docker compose ps
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend
```

### Metrics (Optional)

Add Prometheus + Grafana:

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

---

## Summary

✅ **Multi-stage builds** for optimized images
✅ **Health checks** for reliable startup
✅ **Automatic migrations** on backend startup
✅ **Non-root users** for security
✅ **Layer caching** for fast rebuilds
✅ **Makefile commands** for easy management
✅ **Production-ready** configuration

For local development, use `make dev` + `make frontend`.
For deployment, use `make docker-all`.

---

## Next Steps

1. **Run the system**: `make docker-all`
2. **Seed test data**: `docker compose exec backend python -m app.services.seed_service`
3. **Ingest policies**: `docker compose exec backend python -m app.rag.ingest`
4. **Access UI**: http://localhost:3000
5. **Test analysis**: Click "Analyze New" in the header

For more information, see the main [README.md](./README.md).
