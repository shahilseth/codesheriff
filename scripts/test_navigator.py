"""Manual test of the Navigator agent against the codesheriff repo.

Re-indexes the repo, then runs 3 sample questions through the Navigator and
prints retrieval results -- so retrieval quality can be judged before any
LLM-based answering (Phase 3) is built.

Usage:
    python scripts/test_navigator.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.agents.navigator import Navigator
from backend.indexer.index_repo import index_repo
from backend.models.schemas import NavigatorInput

QUESTIONS = [
    "How does the chunker split code into pieces?",
    "What is the embedding model and how is it initialized?",
    "How is the ChromaDB collection created and populated?",
]


def main() -> None:
    print(f"Indexing {ROOT} ...")
    summary = index_repo(str(ROOT))
    print(f"Indexed {summary['chunks_indexed']} chunks from {summary['files_scanned']} files\n")

    navigator = Navigator(repo_path=str(ROOT))

    for question in QUESTIONS:
        print(f"Q: {question}")

        navigator_input = NavigatorInput(question=question, repo_name=summary["repo_name"], top_k=5)
        output = navigator.run(navigator_input)

        print("  Top 3 chunks:")
        for chunk in output.chunks[:3]:
            print(
                f"    - {chunk.file_path} :: {chunk.chunk_type} '{chunk.chunk_name}' "
                f"(lines {chunk.start_line}-{chunk.end_line}) "
                f"score={chunk.similarity_score:.4f}"
            )

        print("  Commits:")
        if output.commits:
            for commit in output.commits:
                print(f"    - {commit.hash[:8]} {commit.message!r} by {commit.author} ({commit.timestamp})")
        else:
            print("    (none -- repo has no git history, or no commits matched)")

        second_pass_triggered = len(output.chunks) > navigator_input.top_k
        print(f"  LLM second-pass triggered: {second_pass_triggered}")
        print()

    print("Manual judgment: For each question above, did the correct file appear in the top-3? Y/N")


if __name__ == "__main__":
    main()
