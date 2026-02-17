"""ChromaDB HTTP Server - Exposes ChromaDB for Admin UI connection.

This script starts an HTTP server that allows ChromaDB Admin UI to connect
to your fraud_policies collection.

Usage:
    python view_db.py

Then connect from ChromaDB Admin (http://localhost:3001/setup) using:
    - Connection string: http://localhost:8888
    - Tenant: default_tenant
    - Database: default_database
    - Authentication: No Auth
"""

import os
import subprocess
import sys
from pathlib import Path


def check_chroma_installed():
    """Check if ChromaDB CLI is available."""
    try:
        result = subprocess.run(
            ["chroma", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False


def start_chroma_server():
    """Start ChromaDB HTTP server using CLI."""
    db_path = Path("./data/chroma").absolute()

    if not db_path.exists():
        print(f"❌ Error: ChromaDB directory not found at {db_path}")
        print("   Make sure you're running this from the 'backend' directory.")
        print(f"\n   Run 'python seed_test.py' first to create the database.")
        sys.exit(1)

    print("=" * 80)
    print("🚀 Starting ChromaDB HTTP Server")
    print("=" * 80)
    print(f"\n📁 Database path: {db_path}")
    print(f"🌐 Server will be available at: http://localhost:8888")
    print(f"🔧 Tenant: default_tenant")
    print(f"🔧 Database: default_database")
    print("\n" + "=" * 80)
    print("📋 ChromaDB Admin UI Connection Settings:")
    print("=" * 80)
    print("  Chroma connection string: http://localhost:8888")
    print("  Tenant:                   default_tenant")
    print("  Database:                 default_database")
    print("  Authentication Type:      No Auth")
    print("=" * 80)
    print("\n🔍 API v2 Endpoints (for testing):")
    print("=" * 80)
    print("  Heartbeat:   http://localhost:8888/api/v2/heartbeat")
    print("  Collections: http://localhost:8888/api/v2/tenants/default_tenant/databases/default_database/collections")
    print("=" * 80)
    print("\n💡 If ChromaDB Admin UI shows 404, try these URLs directly in browser")
    print("   to verify the server is working correctly.")
    print("=" * 80)
    print("\n⏳ Starting server... (Press Ctrl+C to stop)")
    print("-" * 80 + "\n")

    # Check if CLI is available
    if not check_chroma_installed():
        print("⚠️  ChromaDB CLI not found in PATH.")
        print("   Attempting to run via Python module...\n")

        # Try running via Python module
        try:
            # Set environment variables for ChromaDB
            env = os.environ.copy()
            env["CHROMA_SERVER_HOST"] = "0.0.0.0"
            env["CHROMA_SERVER_HTTP_PORT"] = "8888"
            env["PERSIST_DIRECTORY"] = str(db_path)
            env["IS_PERSISTENT"] = "TRUE"
            env["ANONYMIZED_TELEMETRY"] = "FALSE"

            subprocess.run(
                [sys.executable, "-m", "chromadb.cli.cli", "run",
                 "--path", str(db_path),
                 "--host", "0.0.0.0",
                 "--port", "8888"],
                env=env,
                check=True
            )
        except KeyboardInterrupt:
            print("\n\n✅ Server stopped by user.")
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error starting server via Python module: {e}")
            print("\nTrying alternative method...")
            start_fallback_server(db_path)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nTrying alternative method...")
            start_fallback_server(db_path)
    else:
        # Use ChromaDB CLI directly
        try:
            subprocess.run(
                ["chroma", "run",
                 "--path", str(db_path),
                 "--host", "0.0.0.0",
                 "--port", "8888"],
                check=True
            )
        except KeyboardInterrupt:
            print("\n\n✅ Server stopped by user.")
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error starting server: {e}")
            sys.exit(1)


def start_fallback_server(db_path: Path):
    """Fallback: Start server using uvicorn and FastAPI-based ChromaDB server."""
    try:
        import uvicorn
        from chromadb.server.fastapi import FastAPI as ChromaFastAPI
        from chromadb.config import Settings

        print("🔄 Starting ChromaDB server using uvicorn fallback...\n")

        # Create ChromaDB settings
        settings = Settings(
            chroma_server_host="0.0.0.0",
            chroma_server_http_port=8888,
            persist_directory=str(db_path),
            is_persistent=True,
            anonymized_telemetry=False,
            allow_reset=False
        )

        # Create FastAPI app
        app = ChromaFastAPI(settings)

        # Run server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8888,
            log_level="trace"
        )

    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies for fallback server.")
        print(f"   {e}")
        print("\n💡 Solution: Install ChromaDB with server support:")
        print("   python -m pip install 'chromadb[server]'")
        print("\n   Or use the ChromaDB CLI:")
        print("   pip install chromadb-cli")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    print("\n")

    # Check for --help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    # Start the server
    start_chroma_server()


if __name__ == "__main__":
    main()