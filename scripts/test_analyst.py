"""Manual test of the full Navigator -> Analyst pipeline against the codesheriff repo.

Prints each Analyst answer in full, plus a manual scoring rubric -- this is a
prompt-quality check before the Critic layer (Phase 4) is built.

Usage:
    python scripts/test_analyst.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv()

from backend.agents.analyst import AnalystAgent
from backend.agents.navigator import Navigator
from backend.indexer.index_repo import index_repo
from backend.models.schemas import AnalystInput, NavigatorInput

QUESTIONS = [
    "How does the chunker decide where to split a Python file?",
    "Why does the embedder use all-MiniLM-L6-v2 specifically?",
    "How does the indexer store chunk metadata alongside vectors?",
]


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY not set -- add it to .env before running this script.")

    print(f"Indexing {ROOT} ...")
    summary = index_repo(str(ROOT))
    print(f"Indexed {summary['chunks_indexed']} chunks from {summary['files_scanned']} files\n")

    navigator = Navigator(repo_path=str(ROOT))
    analyst = AnalystAgent(groq_client=Groq(api_key=api_key))

    for question in QUESTIONS:
        print("=" * 80)
        print(f"Q: {question}\n")

        navigator_input = NavigatorInput(question=question, repo_name=summary["repo_name"], top_k=5)
        navigator_output = navigator.run(navigator_input)

        analyst_input = AnalystInput(
            question=question,
            navigator_output=navigator_output,
            repo_name=summary["repo_name"],
        )
        output = analyst.run(analyst_input)

        print(f"Hypothesis: {output.hypothesis}\n")
        print(f"Reasoning:\n{output.reasoning}\n")

        print("Evidence:")
        for ref in output.evidence:
            print(f"  - {ref.file_path} :: '{ref.chunk_name}' (lines {ref.lines}) -- {ref.relevance}")

        print(f"\nUncertainty: {output.uncertainty}\n")

        print("Reasoning gaps:")
        if output.reasoning_gaps:
            for gap in output.reasoning_gaps:
                print(f"  - {gap}")
        else:
            print("  (none reported)")

        print(f"\nConfidence hint: {output.confidence_hint:.2f}")
        print()

    print("=" * 80)
    print(
        "Manual evaluation rubric -- for each answer above, score:\n"
        "  R (reasoning quality): did it explain WHY, not just WHAT? [1-3]\n"
        "  E (evidence accuracy): do the cited chunks actually support the claim? [1-3]\n"
        "  G (gap honesty): did it correctly identify what was missing? [1-3]\n"
        "Record your scores before moving to Phase 4."
    )


if __name__ == "__main__":
    main()
