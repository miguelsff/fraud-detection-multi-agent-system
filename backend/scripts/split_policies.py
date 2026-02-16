#!/usr/bin/env python3
"""
Migration script to split fraud_policies.md into individual policy files.

This script:
1. Reads the monolithic backend/policies/fraud_policies.md file
2. Splits it by policy headers (## FP-XX: Title)
3. Creates individual FP-XX.md files for each policy
4. Backs up the original file as fraud_policies.md.bak

Usage:
    python backend/scripts/split_policies.py
"""

import re
import sys
from pathlib import Path


def split_policies(
    source_file: Path = Path("backend/policies/fraud_policies.md"),
    target_dir: Path = Path("backend/policies"),
) -> None:
    """Split monolithic policy file into individual files.

    Args:
        source_file: Path to the monolithic fraud_policies.md file
        target_dir: Directory where individual policy files will be created
    """
    # Check if source file exists
    if not source_file.exists():
        print(f"[ERROR] Source file not found: {source_file}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)

    # Read the source file
    print(f"[INFO] Reading source file: {source_file}")
    content = source_file.read_text(encoding="utf-8")

    # Split by policy headers: ## FP-XX: Title
    # The pattern captures: policy_id (FP-XX), title, and everything until the next policy or end
    pattern = r"^## (FP-\d{2}):\s*(.+?)$(.+?)(?=^## FP-\d{2}:|\Z)"

    matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))

    if not matches:
        print("[ERROR] No policies found in the source file")
        print("   Expected format: ## FP-XX: Title")
        sys.exit(1)

    print(f"[OK] Found {len(matches)} policies\n")

    # Create individual files
    created_files = []

    for match in matches:
        policy_id = match.group(1)  # e.g., "FP-01"
        title = match.group(2).strip()  # e.g., "Política de Montos Inusuales"
        body = match.group(3).strip()  # Policy content

        # Reconstruct the policy with header
        policy_content = f"## {policy_id}: {title}\n\n{body}\n"

        # Remove trailing separator if present
        policy_content = policy_content.rstrip()
        if policy_content.endswith("---"):
            policy_content = policy_content[:-3].rstrip()
        policy_content += "\n"

        # Create output file
        output_file = target_dir / f"{policy_id}.md"

        # Check if file already exists
        if output_file.exists():
            print(f"[WARN] File already exists: {output_file} (overwriting)")

        output_file.write_text(policy_content, encoding="utf-8")
        created_files.append(output_file)
        print(f"[OK] Created {output_file.name} - {title}")

    # Backup original file
    backup_file = source_file.with_suffix(".md.bak")
    print(f"\n[INFO] Creating backup: {backup_file.name}")

    if backup_file.exists():
        print(f"[WARN] Backup already exists: {backup_file} (overwriting)")

    source_file.rename(backup_file)
    print(f"[OK] Original file backed up as {backup_file.name}")

    # Summary
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Migration complete!")
    print(f"   Created {len(created_files)} policy files")
    print(f"   Backed up original to {backup_file.name}")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. Review the generated files in backend/policies/")
    print("2. Test policy loading")
    print("3. Reingest into ChromaDB")


if __name__ == "__main__":
    # Allow running from project root or backend directory
    if Path("backend/policies").exists():
        # Running from project root
        split_policies(
            source_file=Path("backend/policies/fraud_policies.md"),
            target_dir=Path("backend/policies"),
        )
    elif Path("policies").exists():
        # Running from backend directory
        split_policies(
            source_file=Path("policies/fraud_policies.md"),
            target_dir=Path("policies"),
        )
    else:
        print("[ERROR] Could not find policies directory")
        print(f"   Current directory: {Path.cwd()}")
        print("   Please run from project root or backend directory")
        sys.exit(1)
