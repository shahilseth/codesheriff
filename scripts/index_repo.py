"""CLI entry point for indexing a repository.

Usage:
    python scripts/index_repo.py --repo-path ./some_repo
    python scripts/index_repo.py --repo-url https://github.com/user/repo
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.indexer.index_repo import index_repo
from backend.utils.repo_loader import resolve_repo_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a local or remote repo into ChromaDB.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo-path", help="Path to the local repo to index")
    group.add_argument("--repo-url", help="GitHub URL of the repo to clone and index")
    args = parser.parse_args()

    repo_path, should_cleanup = resolve_repo_path(args.repo_url, args.repo_path)

    try:
        summary = index_repo(repo_path)
    finally:
        if should_cleanup:
            shutil.rmtree(repo_path, ignore_errors=True)

    print(f"Repo:           {summary['repo_name']}")
    print(f"Commit:         {summary['commit_hash']}")
    print(f"Files scanned:  {summary['files_scanned']}")
    print(f"Chunks indexed: {summary['chunks_indexed']}")


if __name__ == "__main__":
    main()
