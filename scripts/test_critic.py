"""Manual test of the full Navigator -> Analyst -> Critic pipeline.

Q(b) is the quality gate for Phase 4 -- see the checklist printed at the end.

Usage:
    python scripts/test_critic.py
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
from backend.agents.critic import CriticAgent
from backend.agents.navigator import Navigator
from backend.indexer.index_repo import index_repo
from backend.models.schemas import AnalystInput, NavigatorInput

QUESTIONS = [
    "How does the chunker decide where to split a Python file?",
    "Why does the embedder use all-MiniLM-L6-v2 specifically?",
]


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY not set -- add it to .env before running this script.")

    print(f"Indexing {ROOT} ...")
    summary = index_repo(str(ROOT))
    print(f"Indexed {summary['chunks_indexed']} chunks from {summary['files_scanned']} files\n")

    groq_client = Groq(api_key=api_key)
    navigator = Navigator(repo_path=str(ROOT))
    analyst = AnalystAgent(groq_client=groq_client)
    critic = CriticAgent(groq_client=groq_client)

    for label, question in zip("ab", QUESTIONS):
        print("=" * 80)
        print(f"Q({label}): {question}\n")

        navigator_input = NavigatorInput(question=question, repo_name=summary["repo_name"], top_k=5)
        navigator_output = navigator.run(navigator_input)

        analyst_input = AnalystInput(
            question=question,
            navigator_output=navigator_output,
            repo_name=summary["repo_name"],
        )
        analyst_output = analyst.run(analyst_input)

        critic_output = critic.run(question, navigator_output, analyst_output)

        print(f"Analyst hypothesis: {analyst_output.hypothesis}")
        print(f"Analyst confidence_hint: {analyst_output.confidence_hint:.2f}\n")

        print("Critic challenges:")
        if critic_output.challenges:
            for challenge in critic_output.challenges:
                print(f"  - [{challenge.challenge_type} / {challenge.severity}] {challenge.description}")
                print(f"    checkable_by: {challenge.checkable_by}")
        else:
            print("  (none)")

        print("\nMissing files:")
        if critic_output.missing_files:
            for path in critic_output.missing_files:
                print(f"  - {path}")
        else:
            print("  (none)")

        print("\nUnchecked assumptions:")
        if critic_output.unchecked_assumptions:
            for assumption in critic_output.unchecked_assumptions:
                print(f"  - {assumption}")
        else:
            print("  (none)")

        print(f"\nConfidence adjustment: {critic_output.confidence_adjustment:+.2f}")
        print(f"Critique summary: {critic_output.critique_summary}")

        final_confidence = analyst_output.confidence_hint + critic_output.confidence_adjustment
        print(f"\nFinal adjusted confidence: {analyst_output.confidence_hint:.2f} "
              f"+ ({critic_output.confidence_adjustment:+.2f}) = {final_confidence:.2f}")
        print()

    print("=" * 80)
    print(
        "Evaluation checklist -- for each Critic output above, check:\n"
        "  [ ] Are the challenges SPECIFIC (name a file, name an assumption)?\n"
        "  [ ] Is severity correctly assigned (high = changes hypothesis)?\n"
        "  [ ] Is confidence_adjustment conservative (most answers: -0.05 to -0.20)?\n"
        "  [ ] Did the Critic avoid restating what the Analyst got right?\n"
        "  [ ] For Q(b): did it catch that 'small and fast' is description not\n"
        "      design rationale, and that no alternative models were considered?\n\n"
        "If Q(b) passes all five checks, the Critic prompt is working correctly."
    )


if __name__ == "__main__":
    main()
