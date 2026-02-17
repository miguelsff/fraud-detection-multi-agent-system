"""Façade service for fraud policy CRUD operations.

Composes PolicyParser and PolicyFileRepository to provide a unified API.
Orchestrates ChromaDB synchronization after mutations.
"""

import re

from ..exceptions import PolicyExistsError, PolicyNotFoundError
from ..models.policy import PolicyCreate, PolicyResponse, PolicyUpdate
from ..rag.vector_store import ingest_policies
from ..utils.logger import get_logger
from .policy_parser import model_to_markdown, parse_markdown_to_model
from .policy_repository import PolicyFileRepository

logger = get_logger(__name__)


class PolicyService:
    """Façade for managing fraud detection policies."""

    def __init__(self, policies_dir: str = "./policies"):
        self.repo = PolicyFileRepository(policies_dir)

    def list_policies(self) -> list[PolicyResponse]:
        """List all policies from markdown files."""
        policies = []
        for policy_file in self.repo.list_files():
            try:
                content = policy_file.read_text(encoding="utf-8")
                policy = parse_markdown_to_model(content, policy_file.name)
                policies.append(policy)
            except Exception as e:
                logger.error("policy_parse_failed", file=policy_file.name, error=str(e))
                continue

        logger.info("policies_listed", count=len(policies))
        return policies

    def get_policy(self, policy_id: str) -> PolicyResponse:
        """Get a single policy by ID.

        Raises:
            PolicyNotFoundError: If policy_id format is invalid or file doesn't exist
        """
        if not re.match(r"^FP-\d{2}$", policy_id):
            raise PolicyNotFoundError(policy_id)

        if not self.repo.exists(policy_id):
            raise PolicyNotFoundError(policy_id)

        content = self.repo.read(policy_id)
        policy = parse_markdown_to_model(content, f"{policy_id}.md")

        logger.info("policy_retrieved", policy_id=policy_id)
        return policy

    def create_policy(self, policy: PolicyCreate) -> PolicyResponse:
        """Create a new policy.

        Raises:
            PolicyExistsError: If policy_id already exists
        """
        if self.repo.exists(policy.policy_id):
            raise PolicyExistsError(policy.policy_id)

        markdown_content = model_to_markdown(policy)
        file_path = self.repo.write(policy.policy_id, markdown_content)
        self._reingest_chromadb()

        logger.info("policy_created", policy_id=policy.policy_id)
        return PolicyResponse(**policy.model_dump(), file_path=f"policies/{file_path.name}")

    def update_policy(self, policy_id: str, updates: PolicyUpdate) -> PolicyResponse:
        """Update an existing policy.

        Raises:
            PolicyNotFoundError: If policy doesn't exist
        """
        existing = self.get_policy(policy_id)

        update_data = updates.model_dump(exclude_unset=True)
        updated_data = existing.model_dump()
        updated_data.update(update_data)
        updated_data.pop("file_path", None)

        updated_policy = PolicyCreate(**updated_data)
        markdown_content = model_to_markdown(updated_policy)
        file_path = self.repo.write(policy_id, markdown_content)
        self._reingest_chromadb()

        logger.info("policy_updated", policy_id=policy_id, fields=list(update_data.keys()))
        return PolicyResponse(**updated_policy.model_dump(), file_path=f"policies/{file_path.name}")

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy.

        Raises:
            PolicyNotFoundError: If policy doesn't exist
        """
        if not self.repo.exists(policy_id):
            raise PolicyNotFoundError(policy_id)

        self.repo.delete(policy_id)
        self._reingest_chromadb()

        logger.info("policy_deleted", policy_id=policy_id)
        return True

    def _reingest_chromadb(self) -> None:
        """Reingest all policies into ChromaDB after mutations."""
        try:
            count = ingest_policies(str(self.repo.policies_dir))
            logger.info("chromadb_reingested", chunks=count)
        except Exception as e:
            logger.error("chromadb_reingest_failed", error=str(e))
