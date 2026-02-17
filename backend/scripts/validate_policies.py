"""
Simple validation script for policy management system.
Runs basic tests without pytest to verify functionality.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.policy_service import PolicyService
from app.models.policy import PolicyCreate, PolicyUpdate


def test_policy_service():
    """Test PolicyService CRUD operations."""
    print("\n" + "="*60)
    print("TESTING POLICY SERVICE")
    print("="*60)

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    print(f"\n✓ Created temp directory: {temp_dir}")

    try:
        service = PolicyService(policies_dir=temp_dir)
        print("✓ PolicyService initialized")

        # Test 1: Create policy
        print("\n[TEST 1] Creating policy...")
        policy = PolicyCreate(
            policy_id="FP-99",
            title="Test Policy",
            description="This is a test policy for validation",
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

        created = service.create_policy(policy)
        assert created.policy_id == "FP-99"
        assert created.title == "Test Policy"
        print("✓ Policy created successfully")

        # Verify file exists
        policy_file = Path(temp_dir) / "FP-99.md"
        assert policy_file.exists()
        print(f"✓ Policy file created: {policy_file.name}")

        # Test 2: List policies
        print("\n[TEST 2] Listing policies...")
        policies = service.list_policies()
        assert len(policies) == 1
        assert policies[0].policy_id == "FP-99"
        print(f"✓ Found {len(policies)} policy")

        # Test 3: Get policy
        print("\n[TEST 3] Getting policy by ID...")
        retrieved = service.get_policy("FP-99")
        assert retrieved.policy_id == "FP-99"
        assert retrieved.title == "Test Policy"
        print("✓ Policy retrieved successfully")

        # Test 4: Update policy
        print("\n[TEST 4] Updating policy...")
        updates = PolicyUpdate(
            title="Updated Test Policy",
            severity="HIGH",
        )
        updated = service.update_policy("FP-99", updates)
        assert updated.title == "Updated Test Policy"
        assert updated.severity == "HIGH"
        assert updated.description == policy.description  # Unchanged
        print("✓ Policy updated successfully")

        # Test 5: Verify update persisted
        print("\n[TEST 5] Verifying update persisted...")
        retrieved_again = service.get_policy("FP-99")
        assert retrieved_again.title == "Updated Test Policy"
        assert retrieved_again.severity == "HIGH"
        print("✓ Update verified")

        # Test 6: Delete policy
        print("\n[TEST 6] Deleting policy...")
        result = service.delete_policy("FP-99")
        assert result is True
        assert not policy_file.exists()
        print("✓ Policy deleted successfully")

        # Test 7: Verify deletion
        print("\n[TEST 7] Verifying deletion...")
        policies_after_delete = service.list_policies()
        assert len(policies_after_delete) == 0
        print("✓ Deletion verified")

        # Test 8: Error handling - Get non-existent
        print("\n[TEST 8] Testing error handling (get non-existent)...")
        try:
            service.get_policy("FP-99")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "not found" in str(e)
            print("✓ Correct error raised for non-existent policy")

        # Test 9: Error handling - Invalid ID format
        print("\n[TEST 9] Testing error handling (invalid ID format)...")
        try:
            service.get_policy("INVALID-ID")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid policy_id format" in str(e)
            print("✓ Correct error raised for invalid ID format")

        # Test 10: Multiple policies
        print("\n[TEST 10] Creating multiple policies...")
        for i in range(1, 4):
            policy_id = f"FP-{i:02d}"
            p = PolicyCreate(
                policy_id=policy_id,
                title=f"Policy {i}",
                description=f"Description {i}",
                criteria=["criterion 1"],
                thresholds=["threshold 1"],
                action_recommended="CHALLENGE",
                severity="MEDIUM",
            )
            service.create_policy(p)

        policies = service.list_policies()
        assert len(policies) == 3
        assert policies[0].policy_id == "FP-01"
        assert policies[1].policy_id == "FP-02"
        assert policies[2].policy_id == "FP-03"
        print(f"✓ Created and listed {len(policies)} policies correctly")

        print("\n" + "="*60)
        print("ALL TESTS PASSED! ✓")
        print("="*60)

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temp directory")


def test_markdown_parsing():
    """Test markdown parsing functionality."""
    print("\n" + "="*60)
    print("TESTING MARKDOWN PARSING")
    print("="*60)

    temp_dir = tempfile.mkdtemp()

    try:
        service = PolicyService(policies_dir=temp_dir)

        # Sample markdown
        markdown = """## FP-01: Política de Montos Inusuales

**Descripción:**
Esta política detecta transacciones con montos significativamente superiores.

**Criterios de Activación:**
- Monto > 3x promedio
- Monto > 2x promedio Y fuera de horario
- Incremento abrupto

**Umbrales Específicos:**
- Ratio crítico: > 3.0x
- Ratio elevado: > 2.0x
- Monto mínimo: 100 PEN

**Acción Recomendada:**
CHALLENGE - Solicitar verificación adicional.

**Severidad:**
MEDIUM
"""

        print("\n[TEST] Parsing markdown to model...")
        policy = service._parse_markdown_to_model(markdown, "FP-01.md")

        assert policy.policy_id == "FP-01"
        assert policy.title == "Política de Montos Inusuales"
        assert "montos significativamente superiores" in policy.description
        assert len(policy.criteria) == 3
        assert len(policy.thresholds) == 3
        assert policy.action_recommended == "CHALLENGE"
        assert policy.severity == "MEDIUM"
        print("✓ Markdown parsed correctly")

        print("\n[TEST] Converting model to markdown...")
        policy_create = PolicyCreate(
            policy_id="FP-02",
            title="Test Policy",
            description="Test description",
            criteria=["Criterion 1", "Criterion 2"],
            thresholds=["Threshold 1"],
            action_recommended="BLOCK",
            severity="HIGH",
        )

        generated_markdown = service._model_to_markdown(policy_create)

        assert "## FP-02: Test Policy" in generated_markdown
        assert "**Descripción:**" in generated_markdown
        assert "Test description" in generated_markdown
        assert "- Criterion 1" in generated_markdown
        assert "- Criterion 2" in generated_markdown
        assert "BLOCK" in generated_markdown
        assert "HIGH" in generated_markdown
        print("✓ Model converted to markdown correctly")

        print("\n" + "="*60)
        print("MARKDOWN PARSING TESTS PASSED! ✓")
        print("="*60)

    finally:
        shutil.rmtree(temp_dir)


def test_real_policies():
    """Test with real policy files."""
    print("\n" + "="*60)
    print("TESTING WITH REAL POLICY FILES")
    print("="*60)

    policies_dir = Path(__file__).parent.parent / "policies"

    if not policies_dir.exists():
        print("⚠ Policies directory not found, skipping real file tests")
        return

    service = PolicyService(policies_dir=str(policies_dir))

    print("\n[TEST] Listing real policies...")
    policies = service.list_policies()
    print(f"✓ Found {len(policies)} real policies")

    if policies:
        # Test reading first policy
        first_policy = policies[0]
        print(f"\n[TEST] Reading policy {first_policy.policy_id}...")
        retrieved = service.get_policy(first_policy.policy_id)
        assert retrieved.policy_id == first_policy.policy_id
        assert retrieved.title == first_policy.title
        print(f"✓ Successfully read policy: {retrieved.title}")

        # Display summary
        print("\n" + "-"*60)
        print("REAL POLICIES SUMMARY:")
        print("-"*60)
        for p in policies:
            print(f"  {p.policy_id}: {p.title}")
            print(f"    Action: {p.action_recommended}, Severity: {p.severity}")
        print("-"*60)

    print("\n" + "="*60)
    print("REAL POLICY TESTS PASSED! ✓")
    print("="*60)


if __name__ == "__main__":
    try:
        test_policy_service()
        test_markdown_parsing()
        test_real_policies()

        print("\n" + "="*60)
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("="*60)
        print("\nThe Policy Management system is working correctly.")
        print("You can now:")
        print("  1. Start the backend server: cd backend && python -m uvicorn app.main:app --reload")
        print("  2. Test the API endpoints at http://localhost:8000/api/v1/policies")
        print("  3. View API docs at http://localhost:8000/docs")
        print()

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
