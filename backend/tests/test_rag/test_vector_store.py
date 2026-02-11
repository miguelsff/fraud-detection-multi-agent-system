"""Tests for the RAG vector store."""

import pytest
from pathlib import Path

from app.rag.vector_store import (
    _split_markdown_sections,
    ingest_policies,
    initialize_collection,
    query_policies,
)


@pytest.fixture
def temp_policies_dir(tmp_path):
    """Create temporary policies directory with test markdown."""
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()

    test_policy = """## FP-01: Test Policy One
**Descripción:**
This is a test policy for unit testing.

**Acción Recomendada:**
CHALLENGE

## FP-02: Test Policy Two
**Descripción:**
Another test policy.

**Acción Recomendada:**
BLOCK
"""
    (policies_dir / "test_policies.md").write_text(test_policy, encoding="utf-8")
    return str(policies_dir)


def test_initialize_collection():
    """Test ChromaDB collection initialization."""
    collection = initialize_collection()
    assert collection.name == "fraud_policies"


def test_split_markdown_sections():
    """Test markdown splitting logic."""
    content = """## FP-01: Policy One
Content for policy one.

## FP-02: Policy Two
Content for policy two."""

    chunks = _split_markdown_sections(content, "test.md")

    assert len(chunks) == 2
    assert chunks[0]["metadata"]["policy_id"] == "FP-01"
    assert chunks[0]["metadata"]["section_name"] == "Policy One"
    assert chunks[0]["id"] == "fp-01-section-0"
    assert chunks[1]["metadata"]["policy_id"] == "FP-02"


def test_split_markdown_extracts_action():
    """Test action_recommended extraction."""
    content = """## FP-03: Test Policy
Acción Recomendada: BLOCK"""

    chunks = _split_markdown_sections(content, "test.md")
    assert chunks[0]["metadata"]["action_recommended"] == "BLOCK"


def test_split_markdown_extracts_challenge():
    """Test CHALLENGE action extraction."""
    content = """## FP-04: Test Policy
Acción Recomendada: CHALLENGE"""

    chunks = _split_markdown_sections(content, "test.md")
    assert chunks[0]["metadata"]["action_recommended"] == "CHALLENGE"


def test_ingest_policies(temp_policies_dir):
    """Test policy ingestion."""
    count = ingest_policies(temp_policies_dir)
    assert count == 2  # Two policies in fixture


def test_ingest_policies_no_directory():
    """Test ingestion with non-existent directory."""
    with pytest.raises(FileNotFoundError):
        ingest_policies("/nonexistent/path")


def test_query_policies(temp_policies_dir):
    """Test querying policies after ingestion."""
    ingest_policies(temp_policies_dir)

    results = query_policies("test policy", n_results=2)
    assert len(results) <= 2
    assert all("id" in r for r in results)
    assert all("text" in r for r in results)
    assert all("score" in r for r in results)
    assert all("metadata" in r for r in results)


def test_query_policies_empty_query():
    """Test query with empty string."""
    results = query_policies("", n_results=5)
    assert results == []


def test_query_policies_returns_scores():
    """Test that query returns scores in 0-1 range."""
    # Note: This test requires policies to be ingested first
    # Using a generic query that might match any policy
    results = query_policies("transaction fraud", n_results=3)

    # If results exist, verify score range
    for result in results:
        assert 0.0 <= result["score"] <= 1.0
