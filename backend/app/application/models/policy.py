"""
Pydantic models for fraud policy management.

This module defines the data models for CRUD operations on fraud detection policies.
Policies are stored as individual markdown files and synchronized with ChromaDB for RAG.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Type literals for policy fields
PolicyAction = Literal["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]
PolicySeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class PolicyBase(BaseModel):
    """Base policy model with all core fields."""

    policy_id: str = Field(
        pattern=r"^FP-\d{2}$",
        description="Policy ID in format FP-XX (e.g., FP-01, FP-15)",
        examples=["FP-01", "FP-15"],
    )
    title: str = Field(min_length=5, max_length=200, description="Policy title")
    description: str = Field(min_length=10, description="Detailed policy description")
    criteria: list[str] = Field(
        min_length=1, description="List of triggering conditions for this policy"
    )
    thresholds: list[str] = Field(min_length=1, description="List of numeric thresholds and limits")
    action_recommended: PolicyAction = Field(
        description="Recommended action when policy is triggered"
    )
    severity: PolicySeverity = Field(description="Severity level of the policy violation")


class PolicyCreate(PolicyBase):
    """Model for creating a new policy."""

    pass


class PolicyUpdate(BaseModel):
    """Model for updating an existing policy (all fields optional)."""

    title: str | None = Field(None, min_length=5, max_length=200)
    description: str | None = Field(None, min_length=10)
    criteria: list[str] | None = Field(None, min_length=1)
    thresholds: list[str] | None = Field(None, min_length=1)
    action_recommended: PolicyAction | None = None
    severity: PolicySeverity | None = None


class PolicyResponse(PolicyBase):
    """Model for policy responses with file metadata."""

    file_path: str = Field(description="Relative path to the markdown file")
