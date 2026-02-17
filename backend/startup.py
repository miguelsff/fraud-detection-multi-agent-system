"""Startup script: ensure DB schema is ready before running the app."""

import asyncio
import subprocess
import sys

from sqlalchemy import text

from app.db.engine import engine, init_db


async def setup_database():
    """Create tables if missing, then run pending Alembic migrations."""
    # 1. Create all tables from models (idempotent - skips existing tables)
    await init_db()

    # 2. Check if alembic_version table exists and has entries
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_name = 'alembic_version'"
                ")"
            )
        )
        has_alembic = result.scalar()

        if has_alembic:
            result = await conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
            count = result.scalar()
        else:
            count = 0

    if count == 0:
        # Fresh DB: stamp head (create_all already made the full schema)
        subprocess.run([sys.executable, "-m", "alembic", "stamp", "head"], check=True)
    else:
        # Existing DB: run pending migrations
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

    await engine.dispose()


asyncio.run(setup_database())
