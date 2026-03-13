"""File-based repository for fraud detection policy markdown files.

Handles all filesystem I/O for policy files. Extracted from PolicyService following SRP.
"""

from pathlib import Path


class PolicyFileRepository:
    """Repository for policy markdown files on the filesystem."""

    def __init__(self, policies_dir: str = "./policies"):
        self.policies_dir = Path(policies_dir)
        self.policies_dir.mkdir(parents=True, exist_ok=True)

    def list_files(self) -> list[Path]:
        """List all policy files sorted by name."""
        return sorted(self.policies_dir.glob("FP-*.md"))

    def read(self, policy_id: str) -> str:
        """Read policy file content.

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = self._file_path(policy_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_id}")
        return file_path.read_text(encoding="utf-8")

    def write(self, policy_id: str, content: str) -> Path:
        """Write content to a policy file. Returns the file path."""
        file_path = self._file_path(policy_id)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def delete(self, policy_id: str) -> None:
        """Delete a policy file.

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = self._file_path(policy_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_id}")
        file_path.unlink()

    def exists(self, policy_id: str) -> bool:
        """Check if a policy file exists."""
        return self._file_path(policy_id).exists()

    def _file_path(self, policy_id: str) -> Path:
        return self.policies_dir / f"{policy_id}.md"
