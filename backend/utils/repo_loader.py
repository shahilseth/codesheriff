"""Resolve a repo source (local path or GitHub URL) to a local directory."""

import shutil
import tempfile
from typing import Optional

from git import GitCommandError, Repo


def resolve_repo_path(repo_url: Optional[str], repo_path: Optional[str]) -> tuple[str, bool]:
    """Resolve either a repo_url or a repo_path to a local directory.

    Returns (path, should_cleanup). should_cleanup is True when the path was
    created by cloning and the caller is responsible for deleting it.
    """
    if repo_url and repo_path:
        raise ValueError("Provide either repo_url or repo_path, not both.")
    if not repo_url and not repo_path:
        raise ValueError("Provide either repo_url or repo_path.")

    if repo_path:
        return repo_path, False

    tmp_dir = tempfile.mkdtemp(prefix="codesheriff-")
    try:
        Repo.clone_from(repo_url, tmp_dir)
    except GitCommandError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(
            f"Failed to clone repo {repo_url!r}: {e}. "
            "Check that the URL is correct and the repo is public "
            "(or that credentials are configured for private repos)."
        ) from e

    return tmp_dir, True
