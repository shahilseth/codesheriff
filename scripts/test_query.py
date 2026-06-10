"""Index the codesheriff repo itself, then run sample semantic queries against ChromaDB.

This is a manual check that retrieval works, before any LLM reasoning is added.

Usage:
    python scripts/test_query.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db.chroma import get_client, get_collection
from backend.indexer.embedder import embed_texts
from backend.indexer.index_repo import index_repo

QUESTIONS = [
    "How does the code split a Python file into function and class chunks?",
    "How are code chunks turned into embedding vectors?",
    "How does the pipeline reset and store data in ChromaDB?",
]


def main() -> None:
    print(f"Indexing {ROOT} ...")
    summary = index_repo(str(ROOT))
    print(
        f"Indexed {summary['chunks_indexed']} chunks "
        f"from {summary['files_scanned']} files (commit {summary['commit_hash']})\n"
    )

    client = get_client()
    collection = get_collection(client, summary["repo_name"])

    for question in QUESTIONS:
        print(f"Q: {question}")
        query_embedding = embed_texts([question])[0].tolist()
        results = collection.query(query_embeddings=[query_embedding], n_results=3)

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for rank, (chunk_id, metadata, distance) in enumerate(zip(ids, metadatas, distances), start=1):
            print(
                f"  {rank}. {metadata['file_path']} :: {metadata['chunk_type']} "
                f"'{metadata['name']}' (lines {metadata['start_line']}-{metadata['end_line']}) "
                f"distance={distance:.4f}"
            )
        print()


if __name__ == "__main__":
    main()
