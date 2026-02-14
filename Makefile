# Makefile for Fraud Detection Multi-Agent System
# ==================================================

.PHONY: help setup dev test test-unit test-integration ingest seed db-reset ollama all clean \
        frontend build-frontend docker-all docker-build docker-up docker-down docker-logs

# Default target - show help
help:
	@echo "Fraud Detection Multi-Agent System - Available Commands"
	@echo "========================================================"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make setup            - Start PostgreSQL + install dependencies"
	@echo "  make dev              - Run FastAPI development server (with reload)"
	@echo "  make frontend         - Run Next.js development server"
	@echo "  make all              - Full setup: setup + ingest + dev"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests (unit + integration)"
	@echo "  make test-unit        - Run only unit tests (fast, no Ollama needed)"
	@echo "  make test-integration - Run only integration tests (requires Ollama)"
	@echo ""
	@echo "Data & Policies:"
	@echo "  make ingest           - Ingest fraud policies into ChromaDB"
	@echo "  make seed             - Seed database with synthetic test data"
	@echo ""
	@echo "Frontend Build:"
	@echo "  make build-frontend   - Build Next.js production bundle"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-all       - Build and start all services (DB + Backend + Frontend)"
	@echo "  make docker-build     - Build Docker images for backend and frontend"
	@echo "  make docker-up        - Start all Docker services"
	@echo "  make docker-down      - Stop all Docker services"
	@echo "  make docker-logs      - View logs from all Docker services"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make db-reset         - Reset PostgreSQL database (WARNING: deletes data)"
	@echo "  make ollama           - Start Ollama server (for LLM inference)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove Python cache files and ChromaDB data"
	@echo ""

# Setup: Start PostgreSQL + Install dependencies
setup:
	@echo "Starting PostgreSQL..."
	docker compose -f devops/docker-compose.yml up -d
	@echo "Installing backend dependencies..."
	cd backend && python -m uv sync
	@echo "✓ Setup complete!"

# Development: Run FastAPI server with auto-reload
dev:
	@echo "Starting FastAPI development server..."
	@echo "API will be available at: http://localhost:8000"
	@echo "Docs at: http://localhost:8000/docs"
	cd backend && python -m uv run uvicorn app.main:app --reload

# Test: Run all tests
test:
	@echo "Running all tests (unit + integration)..."
	cd backend && python -m uv run pytest tests/ -v

# Test: Run only unit tests (fast, no external dependencies)
test-unit:
	@echo "Running unit tests only (no Ollama/DB required)..."
	cd backend && python -m uv run pytest tests/ -v -m "not integration"

# Test: Run only integration tests (requires Ollama)
test-integration:
	@echo "Running integration tests (requires Ollama running)..."
	@echo "Make sure Ollama is running: make ollama"
	cd backend && python -m uv run pytest tests/ -v -m integration

# Ingest: Load fraud policies into ChromaDB
ingest:
	@echo "Ingesting fraud policies into ChromaDB..."
	cd backend && python -m uv run python -m app.rag.ingest
	@echo "✓ Policy ingestion complete!"

# Seed: Populate database with synthetic test data
seed:
	@echo "Seeding database with synthetic test data..."
	cd backend && python -m uv run python -m app.services.seed_service
	@echo "✓ Database seeding complete!"

# Database: Reset PostgreSQL (WARNING: deletes all data)
db-reset:
	@echo "WARNING: This will delete all database data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Stopping and removing PostgreSQL container..."; \
		docker compose -f devops/docker-compose.yml down -v; \
		echo "Starting fresh PostgreSQL instance..."; \
		docker compose -f devops/docker-compose.yml up -d; \
		echo "✓ Database reset complete!"; \
	else \
		echo "Database reset cancelled."; \
	fi

# Ollama: Start Ollama server
ollama:
	@echo "Starting Ollama server..."
	@echo "This will start the Ollama service for LLM inference."
	@echo "Press Ctrl+C to stop."
	ollama serve

# All: Complete setup + ingest + start dev server
all:
	@echo "Running full setup pipeline..."
	$(MAKE) setup
	@echo ""
	$(MAKE) ingest
	@echo ""
	@echo "Starting development server..."
	$(MAKE) dev

# Frontend: Run Next.js development server
frontend:
	@echo "Starting Next.js development server..."
	@echo "Frontend will be available at: http://localhost:3000"
	cd frontend && npm run dev

# Build Frontend: Create production build
build-frontend:
	@echo "Building Next.js production bundle..."
	cd frontend && npm run build
	@echo "✓ Frontend build complete!"

# Docker: Build and start all services
docker-all:
	@echo "Building and starting all Docker services..."
	docker compose up --build -d
	@echo "✓ All services started!"
	@echo ""
	@echo "Services available at:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  Database:  postgresql://fraud_user:fraud_pass_dev@localhost:5432/fraud_detection"
	@echo ""
	@echo "View logs with: make docker-logs"

# Docker: Build images only
docker-build:
	@echo "Building Docker images..."
	docker compose build
	@echo "✓ Docker images built!"

# Docker: Start services (without rebuild)
docker-up:
	@echo "Starting Docker services..."
	docker compose up -d
	@echo "✓ Services started!"

# Docker: Stop all services
docker-down:
	@echo "Stopping Docker services..."
	docker compose down
	@echo "✓ Services stopped!"

# Docker: View logs
docker-logs:
	@echo "Showing logs from all services (Ctrl+C to exit)..."
	docker compose logs -f

# Clean: Remove Python cache and ChromaDB data
clean:
	@echo "Cleaning Python cache files..."
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name "*.pyc" -delete 2>/dev/null || true
	find backend -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaning ChromaDB data..."
	rm -rf backend/chroma_data 2>/dev/null || true
	@echo "Cleaning Next.js build cache..."
	rm -rf frontend/.next 2>/dev/null || true
	rm -rf frontend/node_modules/.cache 2>/dev/null || true
	@echo "✓ Cleanup complete!"
