"""CLI entry point for indexing a repository.

Usage:
    python scripts/index_repo.py --repo_path ./some_repo
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.indexer.index_repo import index_repo


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a local repo into ChromaDB.")
    parser.add_argument("--repo_path", required=True, help="Path to the local repo to index")
    args = parser.parse_args()

    summary = index_repo(args.repo_path)

    print(f"Repo:           {summary['repo_name']}")
    print(f"Commit:         {summary['commit_hash']}")
    print(f"Files scanned:  {summary['files_scanned']}")
    print(f"Chunks indexed: {summary['chunks_indexed']}")


if __name__ == "__main__":
    main()
