"""ChromaDB vector store adapter — implements VectorStorePort."""

import math
import re
from pathlib import Path
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaDBVectorStoreAdapter:
    """VectorStorePort implementation backed by ChromaDB.

    Wraps the existing rag/vector_store.py logic with a clean interface.
    """

    def __init__(self, chroma_client: "chromadb.ClientAPI"):  # type: ignore  # noqa: F821
        self._client = chroma_client
        self._collection = None

    def _get_collection(self):
        """Lazily initialize the fraud_policies collection."""
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name="fraud_policies",
                metadata={"description": "Fraud detection policy documents"},
            )
        return self._collection

    def query(self, query: str, n_results: int = 5) -> list[dict]:
        """Query ChromaDB for relevant fraud policies."""
        if not query.strip():
            logger.warning("empty_query_provided")
            return []

        collection = self._get_collection()

        count = collection.count()
        if count == 0:
            logger.warning("chromadb_collection_empty", collection="fraud_policies")
            return []

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
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

    def ingest(self, policies_dir: str) -> int:
        """Ingest fraud policy markdown files into ChromaDB."""
        collection = self._get_collection()

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
            chunks = self._split_markdown_sections(content, md_file.name)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("no_chunks_extracted")
            return 0

        collection.upsert(
            ids=[chunk["id"] for chunk in all_chunks],
            documents=[chunk["document"] for chunk in all_chunks],
            metadatas=[chunk["metadata"] for chunk in all_chunks],
        )

        logger.info("policies_ingested", count=len(all_chunks), files=len(md_files))
        return len(all_chunks)

    @staticmethod
    def _split_markdown_sections(content: str, file_name: str) -> list[dict]:
        """Split markdown content by ## FP-XX headers."""
        pattern = r"^## (FP-\d{2}):\s*(.+)$"

        chunks = []
        lines = content.split("\n")
        current_section: Optional[dict] = None
        section_index = 0

        for line in lines:
            match = re.match(pattern, line)
            if match:
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
                current_section["document"] += line + "\n"

        if current_section:
            chunks.append(current_section)

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
