"""CLI script to ingest fraud policies into ChromaDB."""

import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.rag.vector_store import ingest_policies
from app.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def main():
    """Ingest fraud policies from policies/ directory."""
    policies_dir = Path(__file__).parent.parent.parent / "policies"

    if not policies_dir.exists():
        logger.error("policies_directory_not_found", path=str(policies_dir))
        print(f"ERROR: Policies directory not found at {policies_dir}")
        print("Please create the directory and add fraud_policies.md")
        sys.exit(1)

    logger.info("starting_ingestion", path=str(policies_dir))
    print(f"Ingesting policies from: {policies_dir}")

    try:
        count = ingest_policies(str(policies_dir))
        logger.info("ingestion_complete", chunks_count=count)
        print(f"[OK] Successfully ingested {count} policy chunks")

    except Exception as e:
        logger.error("ingestion_failed", error=str(e), exc_info=True)
        print(f"ERROR: Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
