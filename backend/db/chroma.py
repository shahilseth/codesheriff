"""ChromaDB client and collection management for CodeSheriff.

Uses a local persistent client (a folder on disk) — no separate database
server to run.
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings

# codesheriff/out/chroma -- generated data, not committed to git
_DEFAULT_PERSIST_DIR = Path(__file__).resolve().parents[2] / "out" / "chroma"


def get_client(persist_dir: str | Path | None = None) -> chromadb.ClientAPI:
    """Get a persistent ChromaDB client, creating the storage folder if needed."""
    persist_dir = Path(persist_dir) if persist_dir else _DEFAULT_PERSIST_DIR
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def reset_collection(client: chromadb.ClientAPI, repo_name: str):
    """Delete the collection for repo_name if it exists, then create a fresh one.

    Phase 1 always rebuilds from scratch; incremental updates come later.
    """
    try:
        client.delete_collection(name=repo_name)
    except Exception:
        pass  # collection didn't exist yet -- nothing to delete
    return client.get_or_create_collection(name=repo_name)


def get_collection(client: chromadb.ClientAPI, repo_name: str):
    """Get an existing collection for repo_name."""
    return client.get_collection(name=repo_name)
