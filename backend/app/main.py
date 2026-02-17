"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .db.engine import init_db
from .rag.vector_store import ingest_policies
from .routers import health, hitl, policies, transactions, websocket
from .utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    setup_logging()
    logger.info("app_starting", env=settings.app_env)

    await init_db()  # Create tables if they don't exist (safe: create_all is idempotent)
    logger.info("database_initialized")

    # Auto-ingest policies into ChromaDB if collection is empty (idempotent via upsert)
    try:
        from pathlib import Path

        policies_dir = Path(__file__).parent.parent / "policies"
        if policies_dir.exists():
            count = ingest_policies(str(policies_dir))
            logger.info("rag_policies_ingested", count=count)
        else:
            logger.warning("policies_directory_not_found", path=str(policies_dir))
    except Exception as e:
        logger.error("rag_ingestion_failed", error=str(e))

    yield

    # Shutdown
    logger.info("app_shutting_down")


app = FastAPI(
    title="Fraud Detection Multi-Agent System",
    description="LangGraph-powered fraud detection with 8 specialized agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - restrictive in production
if settings.app_env == "development":
    cors_origins = ["*"]
elif settings.app_env == "staging":
    cors_origins = [settings.cors_frontend_staging_url, "http://localhost:3000"]
else:  # production
    cors_origins = [settings.cors_frontend_prod_url]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(hitl.router, prefix="/api/v1/hitl", tags=["HITL"])
app.include_router(policies.router)
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket", "Analytics"])


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""
    logger.error("validation_error", path=request.url.path, errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error("http_error", path=request.url.path, status=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
