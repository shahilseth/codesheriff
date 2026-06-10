"""Eval runner for CodeSheriff.

Runs every question in evals/ground_truth.json against a live FastAPI server
(POST /api/query), scores each response, and writes a timestamped report to
evals/eval_results/.

Usage:
    .venv/bin/uvicorn backend.main:app --reload   # in one terminal
    .venv/bin/python evals/eval_runner.py          # in another
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.json"
RESULTS_DIR = Path(__file__).resolve().parent / "eval_results"

BASE_URL = os.environ.get("CODESHERIFF_API_URL", "http://localhost:8000")
REPO_NAME = "codesheriff"


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/").lower()


def score_question(case: dict, result: dict) -> dict:
    cited_paths = {_normalize_path(cf["file_path"]) for cf in result["cited_files"]}
    expected_files = case["expected_files"]
    if expected_files:
        hits = sum(1 for f in expected_files if _normalize_path(f) in cited_paths)
        retrieval_recall = hits / len(expected_files)
    else:
        retrieval_recall = 1.0

    answer_lower = result["answer"].lower()
    expected_keywords = case["expected_keywords"]
    if expected_keywords:
        kw_hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
        keyword_coverage = kw_hits / len(expected_keywords)
    else:
        keyword_coverage = 1.0

    confidence_ok = result["confidence"] >= case["min_confidence"]

    return {
        "id": case["id"],
        "question": case["question"],
        "confidence": result["confidence"],
        "confidence_label": result["confidence_label"],
        "min_confidence": case["min_confidence"],
        "confidence_ok": confidence_ok,
        "retrieval_recall": retrieval_recall,
        "keyword_coverage": keyword_coverage,
        "cited_files": sorted(cited_paths),
        "expected_files": [f.lower() for f in expected_files],
        "trace_id": result["trace_id"],
    }


def main() -> None:
    cases = json.loads(GROUND_TRUTH_PATH.read_text())

    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    response = client.get("/health")
    response.raise_for_status()

    scored: list[dict] = []
    for case in cases:
        print(f"Running: {case['id']} -- {case['question']}")
        try:
            response = client.post(
                "/api/query",
                json={
                    "question": case["question"],
                    "repo_name": REPO_NAME,
                    "repo_path": str(ROOT),
                },
            )
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            scored.append({
                "id": case["id"],
                "question": case["question"],
                "error": str(exc),
                "confidence_ok": False,
                "retrieval_recall": 0.0,
                "keyword_coverage": 0.0,
            })
            continue

        scored.append(score_question(case, result))

    n = len(scored)
    aggregate = {
        "num_questions": n,
        "avg_retrieval_recall": sum(r["retrieval_recall"] for r in scored) / n,
        "avg_keyword_coverage": sum(r["keyword_coverage"] for r in scored) / n,
        "confidence_ok_rate": sum(1 for r in scored if r["confidence_ok"]) / n,
        "avg_confidence": sum(r.get("confidence", 0.0) for r in scored) / n,
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / f"run_{timestamp}.json"
    report_path.write_text(json.dumps({"aggregate": aggregate, "results": scored}, indent=2))

    print_summary(aggregate, scored, report_path)


def print_summary(aggregate: dict, scored: list[dict], report_path: Path) -> None:
    print("\n" + "=" * 78)
    print(f"{'id':<28} {'conf':>6} {'min':>5} {'ok':>4} {'recall':>7} {'kw_cov':>7}")
    print("-" * 78)
    for r in scored:
        if "error" in r:
            print(f"{r['id']:<28} ERROR: {r['error']}")
            continue
        print(
            f"{r['id']:<28} {r['confidence']:>6.2f} {r['min_confidence']:>5.2f} "
            f"{'yes' if r['confidence_ok'] else 'no':>4} "
            f"{r['retrieval_recall']:>7.2f} {r['keyword_coverage']:>7.2f}"
        )
    print("-" * 78)
    print(
        f"{'AGGREGATE':<28} avg_conf={aggregate['avg_confidence']:.2f} "
        f"confidence_ok_rate={aggregate['confidence_ok_rate']:.2f} "
        f"avg_recall={aggregate['avg_retrieval_recall']:.2f} "
        f"avg_kw_cov={aggregate['avg_keyword_coverage']:.2f}"
    )
    print("=" * 78)
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
