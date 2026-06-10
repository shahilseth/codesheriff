"""Git log parsing utilities for the Navigator agent."""

import subprocess

from backend.models.schemas import CommitResult

# %x1e = record separator (between commits), %x1f = field separator (within a commit header)
_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
_LOG_FORMAT = f"{_RECORD_SEP}%H{_FIELD_SEP}%s{_FIELD_SEP}%an{_FIELD_SEP}%aI"


def _run_git_log(repo_path: str, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "log", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _parse_commits(output: str) -> list[CommitResult]:
    commits = []
    for record in output.split(_RECORD_SEP):
        record = record.strip()
        if not record:
            continue

        lines = record.splitlines()
        header = lines[0].split(_FIELD_SEP)
        if len(header) != 4:
            continue

        commit_hash, message, author, timestamp = header
        files_changed = [line.strip() for line in lines[1:] if line.strip()]

        commits.append(CommitResult(
            hash=commit_hash,
            message=message,
            author=author,
            timestamp=timestamp,
            files_changed=files_changed,
        ))
    return commits


def get_relevant_commits(repo_path: str, file_paths: list[str], max_commits: int = 10) -> list[CommitResult]:
    """Return the most recent commits that touched any of the given files.

    Note: --follow only works with a single path, so for multiple files we
    rely on --format + --name-only without --follow (renames across history
    won't be tracked here).
    """
    if not file_paths:
        return []

    output = _run_git_log(
        repo_path,
        [f"-n{max_commits}", f"--format={_LOG_FORMAT}", "--name-only", "--", *file_paths],
    )
    return _parse_commits(output)


def get_file_history(repo_path: str, file_path: str) -> list[CommitResult]:
    """Return commit history for a single file, most recent first (follows renames)."""
    output = _run_git_log(
        repo_path,
        ["--follow", f"--format={_LOG_FORMAT}", "--name-only", "--", file_path],
    )
    return _parse_commits(output)
