"""Tests for policy management API endpoints."""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.models.policy import PolicyCreate
from app.services.policy_service import PolicyService


@pytest.fixture
def temp_policies_dir():
    """Create a temporary directory for policy files during tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def setup_test_policies(temp_policies_dir):
    """Create sample policies for testing."""
    service = PolicyService(policies_dir=temp_policies_dir)

    # Create 3 test policies
    policies = [
        PolicyCreate(
            policy_id="FP-01",
            title="High Amount Policy",
            description="Detects transactions with high amounts",
            criteria=[
                "Amount > 3x average",
                "Amount > 2x average AND off-hours",
            ],
            thresholds=[
                "Critical ratio: > 3.0x",
                "Elevated ratio: > 2.0x",
            ],
            action_recommended="CHALLENGE",
            severity="MEDIUM",
        ),
        PolicyCreate(
            policy_id="FP-02",
            title="Foreign Country Policy",
            description="Detects transactions from unusual countries",
            criteria=[
                "Country not in usual list",
                "High-risk country",
            ],
            thresholds=[
                "First transaction in new country: CHALLENGE",
                "High-risk country: BLOCK",
            ],
            action_recommended="BLOCK",
            severity="HIGH",
        ),
        PolicyCreate(
            policy_id="FP-03",
            title="Unknown Device Policy",
            description="Detects transactions from unknown devices",
            criteria=[
                "Device ID not in history",
                "New device + foreign country",
            ],
            thresholds=[
                "New device only: CHALLENGE",
                "New device + foreign: BLOCK",
            ],
            action_recommended="CHALLENGE",
            severity="MEDIUM",
        ),
    ]

    for policy in policies:
        service.create_policy(policy)

    return temp_policies_dir


@pytest.fixture
def client_with_temp_policies(setup_test_policies, monkeypatch):
    """Test client with policies directory mocked to temp directory."""
    # Monkeypatch PolicyService to use temp directory
    monkeypatch.setattr(
        "app.routers.policies.PolicyService",
        lambda: PolicyService(policies_dir=setup_test_policies),
    )

    return TestClient(app)


# ============================================================================
# GET /api/v1/policies - List Policies
# ============================================================================


def test_list_policies_success(client_with_temp_policies):
    """Test listing all policies returns 200 with policy array."""
    response = client_with_temp_policies.get("/api/v1/policies/")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Verify structure of first policy
    assert data[0]["policy_id"] == "FP-01"
    assert data[0]["title"] == "High Amount Policy"
    assert "description" in data[0]
    assert "criteria" in data[0]
    assert "thresholds" in data[0]
    assert "action_recommended" in data[0]
    assert "severity" in data[0]
    assert "file_path" in data[0]


def test_list_policies_sorted_by_id(client_with_temp_policies):
    """Test that policies are returned sorted by policy_id."""
    response = client_with_temp_policies.get("/api/v1/policies/")
    data = response.json()

    policy_ids = [p["policy_id"] for p in data]
    assert policy_ids == ["FP-01", "FP-02", "FP-03"]


def test_list_policies_empty(monkeypatch, temp_policies_dir):
    """Test listing policies when directory is empty."""
    # Monkeypatch to use empty temp directory
    monkeypatch.setattr(
        "app.routers.policies.PolicyService",
        lambda: PolicyService(policies_dir=temp_policies_dir),
    )

    client = TestClient(app)
    response = client.get("/api/v1/policies/")

    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# GET /api/v1/policies/{id} - Get Single Policy
# ============================================================================


def test_get_policy_success(client_with_temp_policies):
    """Test getting a single policy by ID returns 200."""
    response = client_with_temp_policies.get("/api/v1/policies/FP-01")

    assert response.status_code == 200

    data = response.json()
    assert data["policy_id"] == "FP-01"
    assert data["title"] == "High Amount Policy"
    assert data["action_recommended"] == "CHALLENGE"
    assert data["severity"] == "MEDIUM"


def test_get_policy_not_found(client_with_temp_policies):
    """Test getting non-existent policy returns 404."""
    response = client_with_temp_policies.get("/api/v1/policies/FP-99")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_policy_invalid_id_format(client_with_temp_policies):
    """Test getting policy with invalid ID format returns 404."""
    response = client_with_temp_policies.get("/api/v1/policies/INVALID-ID")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# POST /api/v1/policies - Create Policy
# ============================================================================


def test_create_policy_success(client_with_temp_policies):
    """Test creating a new policy returns 201."""
    new_policy = {
        "policy_id": "FP-99",
        "title": "New Test Policy",
        "description": "This is a new test policy created via API",
        "criteria": [
            "Test criterion 1",
            "Test criterion 2",
        ],
        "thresholds": [
            "Test threshold 1",
            "Test threshold 2",
        ],
        "action_recommended": "BLOCK",
        "severity": "HIGH",
    }

    response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=new_policy,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["policy_id"] == "FP-99"
    assert data["title"] == "New Test Policy"
    assert data["action_recommended"] == "BLOCK"
    assert data["severity"] == "HIGH"
    assert "file_path" in data

    # Verify it can be retrieved
    get_response = client_with_temp_policies.get("/api/v1/policies/FP-99")
    assert get_response.status_code == 200


def test_create_policy_duplicate_returns_409(client_with_temp_policies):
    """Test creating duplicate policy returns 409 Conflict."""
    duplicate_policy = {
        "policy_id": "FP-01",  # Already exists
        "title": "Duplicate Policy",
        "description": "This should fail",
        "criteria": ["criterion"],
        "thresholds": ["threshold"],
        "action_recommended": "CHALLENGE",
        "severity": "MEDIUM",
    }

    response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=duplicate_policy,
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_create_policy_invalid_id_format_returns_422(client_with_temp_policies):
    """Test creating policy with invalid ID format returns 422 validation error."""
    invalid_policy = {
        "policy_id": "INVALID",  # Should be FP-XX format
        "title": "Invalid Policy",
        "description": "Invalid policy ID format",
        "criteria": ["criterion"],
        "thresholds": ["threshold"],
        "action_recommended": "CHALLENGE",
        "severity": "MEDIUM",
    }

    response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=invalid_policy,
    )

    assert response.status_code == 422  # Pydantic validation error


def test_create_policy_missing_required_field_returns_422(client_with_temp_policies):
    """Test creating policy without required fields returns 422."""
    incomplete_policy = {
        "policy_id": "FP-99",
        "title": "Incomplete Policy",
        # Missing description, criteria, thresholds, etc.
    }

    response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=incomplete_policy,
    )

    assert response.status_code == 422


def test_create_policy_empty_criteria_returns_422(client_with_temp_policies):
    """Test creating policy with empty criteria list returns 422."""
    policy_with_empty_criteria = {
        "policy_id": "FP-99",
        "title": "Policy with empty criteria",
        "description": "Description",
        "criteria": [],  # Should have at least one
        "thresholds": ["threshold"],
        "action_recommended": "CHALLENGE",
        "severity": "MEDIUM",
    }

    response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=policy_with_empty_criteria,
    )

    assert response.status_code == 422


# ============================================================================
# PUT /api/v1/policies/{id} - Update Policy
# ============================================================================


def test_update_policy_success(client_with_temp_policies):
    """Test updating an existing policy returns 200."""
    updates = {
        "title": "Updated High Amount Policy",
        "severity": "CRITICAL",
    }

    response = client_with_temp_policies.put(
        "/api/v1/policies/FP-01",
        json=updates,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Updated High Amount Policy"
    assert data["severity"] == "CRITICAL"
    # Other fields should remain unchanged
    assert data["description"] == "Detects transactions with high amounts"


def test_update_policy_all_fields(client_with_temp_policies):
    """Test updating all fields of a policy."""
    updates = {
        "title": "Completely Updated",
        "description": "New description",
        "criteria": ["New criterion 1", "New criterion 2"],
        "thresholds": ["New threshold 1"],
        "action_recommended": "BLOCK",
        "severity": "HIGH",
    }

    response = client_with_temp_policies.put(
        "/api/v1/policies/FP-01",
        json=updates,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Completely Updated"
    assert data["description"] == "New description"
    assert len(data["criteria"]) == 2
    assert data["action_recommended"] == "BLOCK"
    assert data["severity"] == "HIGH"


def test_update_policy_not_found_returns_404(client_with_temp_policies):
    """Test updating non-existent policy returns 404."""
    updates = {"title": "Updated Title"}

    response = client_with_temp_policies.put(
        "/api/v1/policies/FP-99",
        json=updates,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_policy_empty_body(client_with_temp_policies):
    """Test updating with empty body (no changes) is allowed."""
    response = client_with_temp_policies.put(
        "/api/v1/policies/FP-01",
        json={},
    )

    # Should succeed (no changes made)
    assert response.status_code == 200


# ============================================================================
# DELETE /api/v1/policies/{id} - Delete Policy
# ============================================================================


def test_delete_policy_success(client_with_temp_policies):
    """Test deleting a policy returns 204."""
    response = client_with_temp_policies.delete("/api/v1/policies/FP-01")

    assert response.status_code == 204
    assert response.text == ""  # No content

    # Verify it's actually deleted
    get_response = client_with_temp_policies.get("/api/v1/policies/FP-01")
    assert get_response.status_code == 404


def test_delete_policy_not_found_returns_404(client_with_temp_policies):
    """Test deleting non-existent policy returns 404."""
    response = client_with_temp_policies.delete("/api/v1/policies/FP-99")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_policy_removes_from_list(client_with_temp_policies):
    """Test that deleted policy no longer appears in list."""
    # Delete FP-02
    delete_response = client_with_temp_policies.delete("/api/v1/policies/FP-02")
    assert delete_response.status_code == 204

    # List should now have only 2 policies
    list_response = client_with_temp_policies.get("/api/v1/policies/")
    data = list_response.json()

    assert len(data) == 2
    policy_ids = [p["policy_id"] for p in data]
    assert "FP-02" not in policy_ids
    assert "FP-01" in policy_ids
    assert "FP-03" in policy_ids


# ============================================================================
# POST /api/v1/policies/reingest - Manual Reingest
# ============================================================================


def test_manual_reingest_success(client_with_temp_policies):
    """Test manual reingest endpoint returns 202."""
    response = client_with_temp_policies.post("/api/v1/policies/reingest")

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Reingest started"


# ============================================================================
# Integration Tests - Full CRUD Workflow
# ============================================================================


def test_full_crud_workflow(client_with_temp_policies):
    """Test complete CRUD workflow: create, read, update, delete."""
    # 1. Create a new policy
    new_policy = {
        "policy_id": "FP-99",
        "title": "Workflow Test Policy",
        "description": "Testing full CRUD workflow",
        "criteria": ["criterion 1", "criterion 2"],
        "thresholds": ["threshold 1"],
        "action_recommended": "CHALLENGE",
        "severity": "MEDIUM",
    }

    create_response = client_with_temp_policies.post(
        "/api/v1/policies/",
        json=new_policy,
    )
    assert create_response.status_code == 201

    # 2. Read the created policy
    read_response = client_with_temp_policies.get("/api/v1/policies/FP-99")
    assert read_response.status_code == 200
    assert read_response.json()["title"] == "Workflow Test Policy"

    # 3. Update the policy
    update_response = client_with_temp_policies.put(
        "/api/v1/policies/FP-99",
        json={"title": "Updated Workflow Test Policy", "severity": "HIGH"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Workflow Test Policy"
    assert update_response.json()["severity"] == "HIGH"

    # 4. Verify update persisted
    read_again_response = client_with_temp_policies.get("/api/v1/policies/FP-99")
    assert read_again_response.json()["title"] == "Updated Workflow Test Policy"

    # 5. Delete the policy
    delete_response = client_with_temp_policies.delete("/api/v1/policies/FP-99")
    assert delete_response.status_code == 204

    # 6. Verify deletion
    final_read_response = client_with_temp_policies.get("/api/v1/policies/FP-99")
    assert final_read_response.status_code == 404


def test_list_after_multiple_operations(client_with_temp_policies):
    """Test that list endpoint reflects all CRUD operations correctly."""
    # Initial state: 3 policies
    initial_list = client_with_temp_policies.get("/api/v1/policies/").json()
    assert len(initial_list) == 3

    # Create a new policy
    client_with_temp_policies.post(
        "/api/v1/policies/",
        json={
            "policy_id": "FP-99",
            "title": "Test Policy",
            "description": "Test policy description for testing",
            "criteria": ["test criterion"],
            "thresholds": ["test threshold"],
            "action_recommended": "CHALLENGE",
            "severity": "MEDIUM",
        },
    )

    # Should now have 4
    after_create = client_with_temp_policies.get("/api/v1/policies/").json()
    assert len(after_create) == 4

    # Delete one
    client_with_temp_policies.delete("/api/v1/policies/FP-99")

    # Should be back to 3
    after_delete = client_with_temp_policies.get("/api/v1/policies/").json()
    assert len(after_delete) == 3
