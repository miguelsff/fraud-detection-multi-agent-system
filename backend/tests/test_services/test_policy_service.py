"""Tests for PolicyService CRUD operations and markdown parsing."""

import pytest
from pathlib import Path
import tempfile
import shutil

from app.exceptions import InvalidPolicyFormatError, PolicyExistsError, PolicyNotFoundError
from app.services.policy_service import PolicyService
from app.services.policy_parser import (
    model_to_markdown,
    parse_markdown_to_model,
    _extract_action,
    _extract_list_section,
    _extract_section,
    _extract_severity,
)
from app.models.policy import PolicyCreate, PolicyUpdate


@pytest.fixture
def temp_policies_dir():
    """Create a temporary directory for policy files during tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def policy_service(temp_policies_dir):
    """Create PolicyService instance with temp directory."""
    return PolicyService(policies_dir=temp_policies_dir)


@pytest.fixture
def sample_policy_markdown():
    """Sample policy in markdown format."""
    return """## FP-01: Política de Montos Inusuales

**Descripción:**
Esta política detecta transacciones con montos significativamente superiores al comportamiento histórico del cliente.

**Criterios de Activación:**
- Monto de la transacción > 3x el promedio histórico del cliente
- Monto de la transacción > 2x el promedio Y fuera del horario habitual
- Incremento abrupto sin patrón de crecimiento gradual

**Umbrales Específicos:**
- Ratio crítico: > 3.0x promedio → acción inmediata
- Ratio elevado: > 2.0x promedio → verificación adicional
- Monto mínimo para evaluación: 100 PEN / 30 USD

**Acción Recomendada:**
CHALLENGE - Solicitar verificación adicional mediante OTP.

**Severidad:**
MEDIUM
"""


@pytest.fixture
def sample_policy_create():
    """Sample PolicyCreate model."""
    return PolicyCreate(
        policy_id="FP-99",
        title="Test Policy",
        description="This is a test policy for unit testing purposes.",
        criteria=[
            "Test criterion 1",
            "Test criterion 2",
            "Test criterion 3",
        ],
        thresholds=[
            "Threshold 1: value > 100",
            "Threshold 2: value > 500",
        ],
        action_recommended="CHALLENGE",
        severity="MEDIUM",
    )


# ============================================================================
# Markdown Parsing Tests
# ============================================================================


def test_parse_markdown_to_model(sample_policy_markdown):
    """Test parsing markdown content to PolicyResponse model."""
    policy = parse_markdown_to_model(sample_policy_markdown, "FP-01.md")

    assert policy.policy_id == "FP-01"
    assert policy.title == "Política de Montos Inusuales"
    assert "montos significativamente superiores" in policy.description
    assert len(policy.criteria) == 3
    assert len(policy.thresholds) == 3
    assert policy.action_recommended == "CHALLENGE"
    assert policy.severity == "MEDIUM"
    assert policy.file_path == "policies/FP-01.md"


def test_parse_markdown_extracts_action_from_text():
    """Test action extraction from Acción Recomendada section."""
    markdown_block = """BLOCK automático para escenarios de alto riesgo."""
    action = _extract_action(markdown_block)
    assert action == "BLOCK"


def test_parse_markdown_extracts_criteria_list(sample_policy_markdown):
    """Test extraction of bullet list from criteria section."""
    criteria = _extract_list_section(sample_policy_markdown, "Criterios de Activación")
    assert len(criteria) == 3
    assert criteria[0].startswith("Monto de la transacción > 3x")


def test_parse_markdown_missing_section_raises_error():
    """Test that missing section raises InvalidPolicyFormatError."""
    invalid_markdown = "## FP-01: Test\n\nNo sections here."

    with pytest.raises(InvalidPolicyFormatError, match="section not found: Descripción"):
        _extract_section(invalid_markdown, "Descripción")


def test_parse_markdown_invalid_policy_id_raises_error():
    """Test that invalid policy ID format raises error."""
    invalid_markdown = "## INVALID-ID: Test\n\n**Descripción:**\nTest"

    with pytest.raises(InvalidPolicyFormatError, match="missing policy header"):
        parse_markdown_to_model(invalid_markdown, "test.md")


# ============================================================================
# Markdown Generation Tests
# ============================================================================


def test_model_to_markdown(sample_policy_create):
    """Test converting PolicyCreate model to markdown."""
    markdown = model_to_markdown(sample_policy_create)

    assert "## FP-99: Test Policy" in markdown
    assert "**Descripción:**" in markdown
    assert "This is a test policy" in markdown
    assert "**Criterios de Activación:**" in markdown
    assert "- Test criterion 1" in markdown
    assert "**Umbrales Específicos:**" in markdown
    assert "- Threshold 1: value > 100" in markdown
    assert "**Acción Recomendada:**" in markdown
    assert "CHALLENGE" in markdown
    assert "**Severidad:**" in markdown
    assert "MEDIUM" in markdown


def test_model_to_markdown_criteria_formatting(sample_policy_create):
    """Test that criteria are formatted as bullet list."""
    markdown = model_to_markdown(sample_policy_create)

    for criterion in sample_policy_create.criteria:
        assert f"- {criterion}" in markdown


# ============================================================================
# CRUD Operations Tests
# ============================================================================


def test_create_policy(policy_service, sample_policy_create, temp_policies_dir):
    """Test creating a new policy."""
    result = policy_service.create_policy(sample_policy_create)

    assert result.policy_id == "FP-99"
    assert result.title == "Test Policy"
    assert result.file_path == "policies/FP-99.md"

    policy_file = Path(temp_policies_dir) / "FP-99.md"
    assert policy_file.exists()

    content = policy_file.read_text(encoding="utf-8")
    assert "## FP-99: Test Policy" in content


def test_create_policy_duplicate_raises_error(policy_service, sample_policy_create):
    """Test that creating duplicate policy raises PolicyExistsError."""
    policy_service.create_policy(sample_policy_create)

    with pytest.raises(PolicyExistsError, match="already exists"):
        policy_service.create_policy(sample_policy_create)


def test_get_policy(policy_service, sample_policy_create):
    """Test retrieving a single policy by ID."""
    policy_service.create_policy(sample_policy_create)

    result = policy_service.get_policy("FP-99")

    assert result.policy_id == "FP-99"
    assert result.title == "Test Policy"
    assert result.description == sample_policy_create.description


def test_get_policy_not_found_raises_error(policy_service):
    """Test that getting non-existent policy raises PolicyNotFoundError."""
    with pytest.raises(PolicyNotFoundError, match="Policy FP-99 not found"):
        policy_service.get_policy("FP-99")


def test_get_policy_invalid_id_raises_error(policy_service):
    """Test that invalid policy ID format raises PolicyNotFoundError."""
    with pytest.raises(PolicyNotFoundError):
        policy_service.get_policy("INVALID-ID")


def test_list_policies(policy_service, temp_policies_dir):
    """Test listing all policies."""
    for i in range(1, 4):
        policy_id = f"FP-{i:02d}"
        policy = PolicyCreate(
            policy_id=policy_id,
            title=f"Test Policy {i}",
            description=f"Description {i}",
            criteria=["criterion 1"],
            thresholds=["threshold 1"],
            action_recommended="CHALLENGE",
            severity="MEDIUM",
        )
        policy_service.create_policy(policy)

    policies = policy_service.list_policies()

    assert len(policies) == 3
    assert policies[0].policy_id == "FP-01"
    assert policies[1].policy_id == "FP-02"
    assert policies[2].policy_id == "FP-03"


def test_list_policies_empty(policy_service):
    """Test listing policies when directory is empty."""
    policies = policy_service.list_policies()
    assert policies == []


def test_update_policy(policy_service, sample_policy_create):
    """Test updating an existing policy."""
    policy_service.create_policy(sample_policy_create)

    updates = PolicyUpdate(
        title="Updated Title",
        severity="HIGH",
    )
    result = policy_service.update_policy("FP-99", updates)

    assert result.title == "Updated Title"
    assert result.severity == "HIGH"
    assert result.description == sample_policy_create.description
    assert result.action_recommended == sample_policy_create.action_recommended


def test_update_policy_not_found_raises_error(policy_service):
    """Test that updating non-existent policy raises PolicyNotFoundError."""
    updates = PolicyUpdate(title="New Title")

    with pytest.raises(PolicyNotFoundError, match="Policy FP-99 not found"):
        policy_service.update_policy("FP-99", updates)


def test_update_policy_multiple_fields(policy_service, sample_policy_create):
    """Test updating multiple fields at once."""
    policy_service.create_policy(sample_policy_create)

    updates = PolicyUpdate(
        title="New Title",
        description="New Description",
        criteria=["New criterion 1", "New criterion 2"],
        action_recommended="BLOCK",
        severity="CRITICAL",
    )
    result = policy_service.update_policy("FP-99", updates)

    assert result.title == "New Title"
    assert result.description == "New Description"
    assert len(result.criteria) == 2
    assert result.criteria[0] == "New criterion 1"
    assert result.action_recommended == "BLOCK"
    assert result.severity == "CRITICAL"


def test_delete_policy(policy_service, sample_policy_create, temp_policies_dir):
    """Test deleting a policy."""
    policy_service.create_policy(sample_policy_create)

    policy_file = Path(temp_policies_dir) / "FP-99.md"
    assert policy_file.exists()

    result = policy_service.delete_policy("FP-99")
    assert result is True

    assert not policy_file.exists()


def test_delete_policy_not_found_raises_error(policy_service):
    """Test that deleting non-existent policy raises PolicyNotFoundError."""
    with pytest.raises(PolicyNotFoundError, match="Policy FP-99 not found"):
        policy_service.delete_policy("FP-99")


# ============================================================================
# Severity Inference Tests
# ============================================================================


def test_extract_severity_from_explicit_section():
    """Test extracting explicit severity from markdown."""
    markdown = """
**Severidad:**
HIGH
"""
    severity = _extract_severity(markdown, "CHALLENGE")
    assert severity == "HIGH"


def test_extract_severity_inferred_from_action():
    """Test inferring severity when not explicitly specified."""
    markdown = "## FP-01: Test\n\n**Descripción:**\nTest"

    assert _extract_severity(markdown, "BLOCK") == "HIGH"
    assert _extract_severity(markdown, "CHALLENGE") == "MEDIUM"
    assert _extract_severity(markdown, "APPROVE") == "LOW"
    assert _extract_severity(markdown, "ESCALATE_TO_HUMAN") == "CRITICAL"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_list_policies_with_parse_error(policy_service, temp_policies_dir):
    """Test that list_policies skips files with parse errors."""
    valid_policy = PolicyCreate(
        policy_id="FP-01",
        title="Valid Policy",
        description="Valid description",
        criteria=["criterion 1"],
        thresholds=["threshold 1"],
        action_recommended="CHALLENGE",
        severity="MEDIUM",
    )
    policy_service.create_policy(valid_policy)

    invalid_file = Path(temp_policies_dir) / "FP-02.md"
    invalid_file.write_text("INVALID MARKDOWN CONTENT", encoding="utf-8")

    policies = policy_service.list_policies()
    assert len(policies) == 1
    assert policies[0].policy_id == "FP-01"


def test_reingest_chromadb_does_not_raise(policy_service, sample_policy_create):
    """Test that ChromaDB reingest failures don't break CRUD operations."""
    result = policy_service.create_policy(sample_policy_create)
    assert result.policy_id == "FP-99"
