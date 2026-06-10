"""Main indexing pipeline: walk a repo, chunk Python files, embed, and store in ChromaDB."""

import subprocess
from pathlib import Path

from backend.db.chroma import get_client, reset_collection
from backend.indexer.chunker import chunk_python_file
from backend.indexer.embedder import embed_texts

_IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "out"}


def get_git_commit_hash(repo_path: Path) -> str:
    """Return the current git HEAD commit hash, or 'unknown' if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def find_python_files(repo_path: Path) -> list[Path]:
    """Find all .py files in repo_path, skipping common non-source directories."""
    files = []
    for path in repo_path.rglob("*.py"):
        if any(part in _IGNORE_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def index_repo(repo_path: str, persist_dir: str | None = None) -> dict:
    """Index a local repo into ChromaDB. Returns a summary dict."""
    repo_path = Path(repo_path).resolve()
    repo_name = repo_path.name
    commit_hash = get_git_commit_hash(repo_path)

    client = get_client(persist_dir)
    collection = reset_collection(client, repo_name)

    py_files = find_python_files(repo_path)

    all_texts: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    for file_path in py_files:
        rel_path = file_path.relative_to(repo_path).as_posix()
        try:
            source = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for i, chunk in enumerate(chunk_python_file(source, file_name=rel_path)):
            all_texts.append(chunk.text)
            all_metadatas.append({
                "file_path": rel_path,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "repo_name": repo_name,
                "language": "python",
                "commit_hash": commit_hash,
            })
            all_ids.append(f"{rel_path}::{chunk.name}::{chunk.start_line}-{chunk.end_line}::{i}")

    summary = {
        "repo_name": repo_name,
        "files_scanned": len(py_files),
        "chunks_indexed": len(all_texts),
        "commit_hash": commit_hash,
    }

    if not all_texts:
        return summary

    embeddings = embed_texts(all_texts)
    collection.add(
        ids=all_ids,
        embeddings=embeddings.tolist(),
        documents=all_texts,
        metadatas=all_metadatas,
    )

    return summary
