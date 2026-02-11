"""ChromaDB vector store for fraud policy retrieval."""

import math
import re
from pathlib import Path
from typing import Optional

from ..dependencies import get_chroma
from ..utils.logger import get_logger

logger = get_logger(__name__)


def initialize_collection() -> "chromadb.Collection":  # type: ignore
    """Initialize or get the fraud_policies ChromaDB collection.

    Returns:
        chromadb.Collection configured with default embedding function

    Note:
        Uses ChromaDB default embedding (sentence-transformers/all-MiniLM-L6-v2)
        which provides decent multilingual support including Spanish.
    """
    client = get_chroma()

    collection = client.get_or_create_collection(
        name="fraud_policies",
        metadata={"description": "Fraud detection policy documents"},
        # ChromaDB uses default embedding function automatically
    )

    return collection


def ingest_policies(policies_dir: str = "./policies") -> int:
    """Ingest fraud policy markdown files into ChromaDB.

    Args:
        policies_dir: Path to directory containing .md policy files

    Returns:
        Number of chunks ingested

    Raises:
        FileNotFoundError: If policies_dir doesn't exist
    """
    collection = initialize_collection()

    policies_path = Path(policies_dir)
    if not policies_path.exists():
        raise FileNotFoundError(f"Policies directory not found: {policies_dir}")

    md_files = list(policies_path.glob("*.md"))
    if not md_files:
        logger.warning("no_policy_files_found", path=policies_dir)
        return 0

    all_chunks = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        chunks = _split_markdown_sections(content, md_file.name)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("no_chunks_extracted")
        return 0

    # Upsert to ChromaDB (idempotent - can run multiple times safely)
    collection.upsert(
        ids=[chunk["id"] for chunk in all_chunks],
        documents=[chunk["document"] for chunk in all_chunks],
        metadatas=[chunk["metadata"] for chunk in all_chunks],
    )

    logger.info("policies_ingested", count=len(all_chunks), files=len(md_files))
    return len(all_chunks)


def _split_markdown_sections(content: str, file_name: str) -> list[dict]:
    """Split markdown content by ## FP-XX headers.

    Args:
        content: Full markdown file content
        file_name: Name of the source file

    Returns:
        List of chunk dicts with id, document, and metadata

    Note:
        Each policy section (## FP-XX: Title) becomes a separate chunk.
        Metadata includes policy_id, section_name, file_name, section_index,
        and action_recommended if found in text.
    """
    # Regex to find policy sections: ## FP-01: Title
    pattern = r"^## (FP-\d{2}):\s*(.+)$"

    chunks = []
    lines = content.split("\n")
    current_section: Optional[dict] = None
    section_index = 0

    for line in lines:
        match = re.match(pattern, line)
        if match:
            # Save previous section before starting new one
            if current_section:
                chunks.append(current_section)

            policy_id = match.group(1)
            section_name = match.group(2).strip()

            current_section = {
                "id": f"{policy_id.lower()}-section-{section_index}",
                "document": line + "\n",
                "metadata": {
                    "policy_id": policy_id,
                    "section_name": section_name,
                    "file_name": file_name,
                    "section_index": section_index,
                },
            }
            section_index += 1
        elif current_section:
            # Append to current section
            current_section["document"] += line + "\n"

    # Add last section
    if current_section:
        chunks.append(current_section)

    # Extract action_recommended if present in text
    for chunk in chunks:
        doc = chunk["document"]
        if "BLOCK" in doc:
            chunk["metadata"]["action_recommended"] = "BLOCK"
        elif "CHALLENGE" in doc:
            chunk["metadata"]["action_recommended"] = "CHALLENGE"
        elif "APPROVE" in doc:
            chunk["metadata"]["action_recommended"] = "APPROVE"
        elif "ESCALATE" in doc or "ESCALATE_TO_HUMAN" in doc:
            chunk["metadata"]["action_recommended"] = "ESCALATE_TO_HUMAN"

    return chunks


def query_policies(query: str, n_results: int = 5) -> list[dict]:
    """Query ChromaDB for relevant fraud policies.

    Args:
        query: Natural language query describing transaction characteristics
        n_results: Maximum number of results to return

    Returns:
        List of dicts with keys: id, text, metadata, score (0-1, higher is better)

    Note:
        - Returns empty list if query is empty or collection is empty
        - Scores are converted from L2 distance using exponential decay
        - Results are sorted by relevance (highest score first)
    """
    if not query.strip():
        logger.warning("empty_query_provided")
        return []

    collection = initialize_collection()

    # Check if collection is empty
    count = collection.count()
    if count == 0:
        logger.warning("chromadb_collection_empty", collection="fraud_policies")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    # ChromaDB returns distance (lower is better), convert to score (higher is better)
    # Using exponential decay: score = exp(-distance)
    formatted_results = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            # Convert distance to similarity score
            # For L2 distance, use exponential decay
            score = math.exp(-distance)

            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": round(score, 4),
                }
            )

    logger.info(
        "policies_queried",
        query=query[:50],
        results_count=len(formatted_results),
    )
    return formatted_results
