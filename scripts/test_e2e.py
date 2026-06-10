"""End-to-end integration test against a running CodeSheriff FastAPI server.

Hits the live HTTP API (not Python classes directly) -- start the server
first:

    .venv/bin/uvicorn backend.main:app --reload

Then run:

    .venv/bin/python scripts/test_e2e.py
"""

import os
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("CODESHERIFF_API_URL", "http://localhost:8000")


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    # 1. Health check
    response = client.get("/health")
    response.raise_for_status()
    health = response.json()
    assert health["status"] == "ok", f"unexpected health response: {health}"
    print(f"Health: {health}")

    # 2. Index the codesheriff repo
    response = client.post(
        "/api/index",
        json={"repo_path": str(ROOT), "repo_name": "codesheriff"},
    )
    response.raise_for_status()
    index_result = response.json()
    assert index_result["status"] == "indexed", f"unexpected index response: {index_result}"
    assert index_result["chunks"] > 0, f"expected chunks > 0, got {index_result}"
    print(f"Index: {index_result}")

    # 3. Ask a question
    response = client.post(
        "/api/query",
        json={
            "question": "How does the chunker decide where to split a Python file?",
            "repo_name": "codesheriff",
            "repo_path": str(ROOT),
        },
    )
    response.raise_for_status()
    result = response.json()

    # 4. Print the response
    print("\nAnswer:")
    print(result["answer"])
    print(f"\nConfidence: {result['confidence']:.2f} ({result['confidence_label']})")
    print("\nCited files:")
    for cf in result["cited_files"]:
        print(f"  - {cf['file_path']} :: {cf['chunk_name']}")
    print("\nKnown gaps:")
    for gap in result["known_gaps"]:
        print(f"  - {gap}")
    print(f"\nTrace ID: {result['trace_id']}")

    # 5-8. Assertions
    assert 0.0 <= result["confidence"] <= 1.0, f"confidence out of range: {result['confidence']}"
    assert len(result["cited_files"]) > 0, "expected at least one cited file"
    assert len(result["known_gaps"]) > 0, "expected at least one known gap"
    uuid.UUID(result["trace_id"])  # raises if invalid

    print("\nAll assertions passed. Query the trace:")
    print(f"  SELECT full_trace FROM traces WHERE id = '{result['trace_id']}';")


if __name__ == "__main__":
    main()
