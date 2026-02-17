"""Interactive ChromaDB Explorer - CLI tool for exploring fraud_policies collection.

This script provides an interactive menu to explore ChromaDB collections
without needing to start an HTTP server.

Usage:
    python explore_chromadb.py
"""

import json
import math
import sys
from pathlib import Path

import chromadb
from chromadb.config import Settings


class ChromaDBExplorer:
    """Interactive ChromaDB explorer."""

    def __init__(self, db_path: Path):
        """Initialize explorer with database path."""
        self.db_path = db_path
        self.client = None
        self.collection = None

    def connect(self):
        """Connect to ChromaDB."""
        print("\n" + "=" * 80)
        print("Connecting to ChromaDB...")
        print("=" * 80)

        if not self.db_path.exists():
            print(f"\n[ERROR] ChromaDB directory not found at {self.db_path.absolute()}")
            print("   Make sure you're running this from the 'backend' directory.")
            print("   Run 'python seed_test.py' first to create the database.")
            sys.exit(1)

        print(f"Database path: {self.db_path.absolute()}")

        try:
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            print("[OK] Connected to ChromaDB")

            # Get fraud_policies collection
            try:
                self.collection = self.client.get_collection(name="fraud_policies")
                print(f"[OK] Loaded collection: {self.collection.name}")
                print(f"     Total documents: {self.collection.count()}")
            except Exception as e:
                print(f"\n[ERROR] Collection 'fraud_policies' not found: {e}")
                print("   Run 'python seed_test.py' to populate the database.")
                sys.exit(1)

        except Exception as e:
            print(f"\n[ERROR] Failed to connect to ChromaDB: {e}")
            sys.exit(1)

    def show_menu(self):
        """Display main menu."""
        print("\n" + "=" * 80)
        print("CHROMADB EXPLORER - Main Menu")
        print("=" * 80)
        print("  1. Collection Statistics")
        print("  2. List All Documents")
        print("  3. Search by Policy ID (e.g., FP-01)")
        print("  4. Semantic Search")
        print("  5. Example Searches")
        print("  6. View Document by ID")
        print("  7. List All Policy IDs")
        print("  0. Exit")
        print("=" * 80)

    def collection_stats(self):
        """Show collection statistics."""
        print("\n" + "=" * 80)
        print("COLLECTION STATISTICS")
        print("=" * 80)

        count = self.collection.count()
        print(f"\nCollection Name: {self.collection.name}")
        print(f"Total Documents: {count}")

        if count > 0:
            # Get all documents to analyze
            result = self.collection.get(include=["metadatas"])

            if result["metadatas"]:
                # Count by policy_id
                policy_ids = {}
                actions = {}

                for meta in result["metadatas"]:
                    policy_id = meta.get("policy_id", "Unknown")
                    action = meta.get("action_recommended", "None")

                    policy_ids[policy_id] = policy_ids.get(policy_id, 0) + 1
                    actions[action] = actions.get(action, 0) + 1

                print(f"\nPolicies ({len(policy_ids)} unique):")
                for policy_id, count in sorted(policy_ids.items()):
                    print(f"  - {policy_id}: {count} section(s)")

                print(f"\nRecommended Actions:")
                for action, count in sorted(actions.items()):
                    print(f"  - {action}: {count} section(s)")

        print()

    def list_all_documents(self):
        """List all documents with details."""
        print("\n" + "=" * 80)
        print("ALL DOCUMENTS")
        print("=" * 80)

        result = self.collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        if not result["ids"]:
            print("\n[WARNING] No documents found.")
            return

        print(f"\nTotal: {len(result['ids'])} documents\n")

        for i, doc_id in enumerate(result["ids"], 1):
            metadata = result["metadatas"][i-1] if result["metadatas"] else {}
            document = result["documents"][i-1] if result["documents"] else ""
            embedding = result["embeddings"][i-1] if result["embeddings"] else None

            print(f"\n{'─' * 80}")
            print(f"[{i}] ID: {doc_id}")
            print(f"{'─' * 80}")

            # Metadata
            if metadata:
                print("\nMetadata:")
                for key, value in metadata.items():
                    print(f"  - {key}: {value}")

            # Document preview
            if document:
                lines = document.split('\n')
                first_line = lines[0] if lines else ""
                preview = '\n'.join(lines[:10])  # First 10 lines

                print(f"\nDocument ({len(document)} chars, {len(lines)} lines):")
                print(f"  Title: {first_line}")
                print(f"  Preview:")
                for line in lines[:5]:  # Show first 5 lines
                    print(f"    {line[:70]}")

            # Embedding info
            if embedding:
                print(f"\nEmbedding: {len(embedding)} dimensions")

        print("\n" + "=" * 80)

    def search_by_policy_id(self, policy_id: str):
        """Search documents by policy ID."""
        print(f"\n" + "=" * 80)
        print(f"SEARCH BY POLICY ID: {policy_id}")
        print("=" * 80)

        result = self.collection.get(
            where={"policy_id": policy_id},
            include=["documents", "metadatas"]
        )

        if not result["ids"]:
            print(f"\n[WARNING] No documents found for policy ID: {policy_id}")
            print("Available policy IDs: FP-01, FP-02, FP-03, FP-04, etc.")
            return

        print(f"\nFound {len(result['ids'])} document(s):\n")

        for i, doc_id in enumerate(result["ids"], 1):
            metadata = result["metadatas"][i-1] if result["metadatas"] else {}
            document = result["documents"][i-1] if result["documents"] else ""

            print(f"\n{'─' * 80}")
            print(f"[{i}] {doc_id}")
            print(f"{'─' * 80}")

            if metadata:
                print(f"\nSection: {metadata.get('section_name', 'N/A')}")
                print(f"File: {metadata.get('file_name', 'N/A')}")
                print(f"Action Recommended: {metadata.get('action_recommended', 'N/A')}")

            if document:
                print(f"\nFull Document:")
                print(document)

        print("\n" + "=" * 80)

    def semantic_search(self, query: str, n_results: int = 5):
        """Perform semantic search."""
        print(f"\n" + "=" * 80)
        print(f"SEMANTIC SEARCH: \"{query}\"")
        print("=" * 80)

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        if not results["ids"] or not results["ids"][0]:
            print("\n[WARNING] No results found.")
            return

        print(f"\nTop {len(results['ids'][0])} results:\n")

        for i, doc_id in enumerate(results["ids"][0], 1):
            distance = results["distances"][0][i-1] if results["distances"] else 0
            metadata = results["metadatas"][0][i-1] if results["metadatas"] else {}
            document = results["documents"][0][i-1] if results["documents"] else ""

            # Convert distance to score
            score = math.exp(-distance)

            print(f"\n{'─' * 80}")
            print(f"[{i}] Score: {score:.4f} (distance: {distance:.4f})")
            print(f"    ID: {doc_id}")
            print(f"{'─' * 80}")

            if metadata:
                print(f"\nPolicy: {metadata.get('policy_id', 'N/A')}")
                print(f"Section: {metadata.get('section_name', 'N/A')}")
                print(f"Action: {metadata.get('action_recommended', 'N/A')}")

            if document:
                # Show first paragraph
                lines = document.split('\n')
                print(f"\nPreview:")
                for line in lines[:8]:  # First 8 lines
                    if line.strip():
                        print(f"  {line[:75]}")

        print("\n" + "=" * 80)

    def example_searches(self):
        """Run example semantic searches."""
        examples = [
            ("High amount + off-hours", "transacción de monto muy elevado fuera del horario habitual"),
            ("Unknown device + foreign country", "dispositivo no reconocido desde país extranjero"),
            ("Unusual behavior", "monto superior al promedio comportamiento inusual"),
            ("International transaction", "transacción internacional país extranjero"),
        ]

        for i, (title, query) in enumerate(examples, 1):
            print(f"\n{'=' * 80}")
            print(f"EXAMPLE {i}/{len(examples)}: {title}")
            print(f"Query: \"{query}\"")
            print(f"{'=' * 80}")

            results = self.collection.query(
                query_texts=[query],
                n_results=3,
                include=["metadatas", "distances"]
            )

            if results["ids"] and results["ids"][0]:
                for j, doc_id in enumerate(results["ids"][0], 1):
                    distance = results["distances"][0][j-1] if results["distances"] else 0
                    metadata = results["metadatas"][0][j-1] if results["metadatas"] else {}
                    score = math.exp(-distance)

                    print(f"\n  [{j}] Score: {score:.4f}")
                    print(f"      Policy: {metadata.get('policy_id', 'N/A')}")
                    print(f"      Section: {metadata.get('section_name', 'N/A')}")
                    print(f"      Action: {metadata.get('action_recommended', 'N/A')}")
            else:
                print("\n  No results found.")

        print("\n" + "=" * 80)

    def view_document_by_id(self, doc_id: str):
        """View a specific document by ID."""
        print(f"\n" + "=" * 80)
        print(f"DOCUMENT: {doc_id}")
        print("=" * 80)

        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas", "embeddings"]
            )

            if not result["ids"]:
                print(f"\n[WARNING] Document not found: {doc_id}")
                return

            metadata = result["metadatas"][0] if result["metadatas"] else {}
            document = result["documents"][0] if result["documents"] else ""
            embedding = result["embeddings"][0] if result["embeddings"] else None

            print(f"\nID: {result['ids'][0]}")

            if metadata:
                print(f"\nMetadata:")
                print(json.dumps(metadata, indent=2))

            if document:
                print(f"\nDocument ({len(document)} chars):")
                print(document)

            if embedding:
                print(f"\nEmbedding: {len(embedding)} dimensions")
                print(f"First 10 values: {embedding[:10]}")

        except Exception as e:
            print(f"\n[ERROR] {e}")

        print("\n" + "=" * 80)

    def list_policy_ids(self):
        """List all unique policy IDs."""
        print("\n" + "=" * 80)
        print("ALL POLICY IDs")
        print("=" * 80)

        result = self.collection.get(include=["metadatas"])

        if result["metadatas"]:
            policy_data = {}

            for meta in result["metadatas"]:
                policy_id = meta.get("policy_id", "Unknown")
                section_name = meta.get("section_name", "N/A")
                action = meta.get("action_recommended", "N/A")

                if policy_id not in policy_data:
                    policy_data[policy_id] = {
                        "section_name": section_name,
                        "action": action,
                        "count": 0
                    }
                policy_data[policy_id]["count"] += 1

            print(f"\nFound {len(policy_data)} unique policies:\n")

            for policy_id in sorted(policy_data.keys()):
                data = policy_data[policy_id]
                print(f"  {policy_id}: {data['section_name']}")
                print(f"           Action: {data['action']}")
                print(f"           Sections: {data['count']}")
                print()

        print("=" * 80)

    def run(self):
        """Run the interactive explorer."""
        self.connect()

        while True:
            self.show_menu()
            choice = input("\nSelect option (0-7): ").strip()

            if choice == "0":
                print("\n[OK] Goodbye!\n")
                break
            elif choice == "1":
                self.collection_stats()
            elif choice == "2":
                self.list_all_documents()
            elif choice == "3":
                policy_id = input("\nEnter Policy ID (e.g., FP-01): ").strip().upper()
                if policy_id:
                    self.search_by_policy_id(policy_id)
                else:
                    print("\n[WARNING] Policy ID cannot be empty.")
            elif choice == "4":
                query = input("\nEnter search query: ").strip()
                if query:
                    n_results = input("Number of results (default 5): ").strip()
                    n_results = int(n_results) if n_results.isdigit() else 5
                    self.semantic_search(query, n_results)
                else:
                    print("\n[WARNING] Query cannot be empty.")
            elif choice == "5":
                self.example_searches()
            elif choice == "6":
                doc_id = input("\nEnter Document ID (e.g., fp-01-section-0): ").strip()
                if doc_id:
                    self.view_document_by_id(doc_id)
                else:
                    print("\n[WARNING] Document ID cannot be empty.")
            elif choice == "7":
                self.list_policy_ids()
            else:
                print("\n[WARNING] Invalid option. Please select 0-7.")

            input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    db_path = Path("./data/chroma")

    print("\n" + "=" * 80)
    print("ChromaDB Interactive Explorer")
    print("Fraud Detection Policies Collection")
    print("=" * 80)

    explorer = ChromaDBExplorer(db_path)
    explorer.run()


if __name__ == "__main__":
    main()
