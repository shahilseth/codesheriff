"""Navigator agent: retrieval specialist for CodeSheriff.

Given a natural language question, finds the most relevant code chunks
(semantic search via ChromaDB) and the most relevant git commits
(structured search via git log). Does not reason about or answer the
question -- that's the Analyst's job (Phase 3).
"""

import fnmatch
import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

from backend.db.chroma import get_client, get_collection
from backend.indexer.embedder import embed_texts
from backend.models.schemas import ChunkResult, CommitResult, NavigatorInput, NavigatorOutput
from backend.utils.git_utils import get_relevant_commits

load_dotenv()

_GROQ_MODEL = "llama-3.1-8b-instant"


class Navigator:
    """Retrieves relevant code chunks and commit history for a question."""

    def __init__(self, repo_path: str, persist_dir: Optional[str] = None):
        self.repo_path = repo_path
        self._client = get_client(persist_dir)

    def run(self, navigator_input: NavigatorInput) -> NavigatorOutput:
        # Step 1: semantic search over code chunks
        chunks = self._semantic_search(navigator_input)

        # Step 2: structured search -- recent commits touching the retrieved files
        file_paths = _dedupe(chunk.file_path for chunk in chunks)
        commits = get_relevant_commits(self.repo_path, file_paths)

        # Step 3 (optional fallback): ask a small LLM if anything obvious is missing
        extra_chunks = self._fetch_suggested_chunks(navigator_input, chunks)
        chunks = chunks + extra_chunks

        return NavigatorOutput(
            question=navigator_input.question,
            chunks=chunks,
            commits=commits,
            retrieved_file_paths=_dedupe(chunk.file_path for chunk in chunks),
        )

    def _semantic_search(self, navigator_input: NavigatorInput) -> list[ChunkResult]:
        collection = get_collection(self._client, navigator_input.repo_name)
        query_embedding = embed_texts([navigator_input.question])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=navigator_input.top_k,
        )
        return _build_chunk_results(results)

    def _fetch_suggested_chunks(
        self, navigator_input: NavigatorInput, existing_chunks: list[ChunkResult]
    ) -> list[ChunkResult]:
        patterns = self._suggest_missing_patterns(navigator_input, existing_chunks)
        if not patterns:
            return []

        collection = get_collection(self._client, navigator_input.repo_name)
        all_items = collection.get(include=["documents", "metadatas"])

        existing_paths = {chunk.file_path for chunk in existing_chunks}
        extra: list[ChunkResult] = []
        seen_paths: set[str] = set()

        for document, metadata in zip(all_items["documents"], all_items["metadatas"]):
            file_path = metadata["file_path"]
            if file_path in existing_paths or file_path in seen_paths:
                continue
            if any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns):
                seen_paths.add(file_path)
                extra.append(ChunkResult(
                    file_path=file_path,
                    chunk_name=metadata["name"],
                    chunk_type=metadata["chunk_type"],
                    content=document,
                    similarity_score=0.0,  # not ranked by similarity -- added via LLM suggestion
                    start_line=metadata["start_line"],
                    end_line=metadata["end_line"],
                ))

        return extra

    def _suggest_missing_patterns(
        self, navigator_input: NavigatorInput, chunks: list[ChunkResult]
    ) -> list[str]:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return []

        retrieved = "\n".join(
            f"{chunk.file_path} :: {chunk.chunk_type} {chunk.chunk_name}" for chunk in chunks
        )
        prompt = (
            f"Question: {navigator_input.question}\n\n"
            f"Already retrieved files/chunks:\n{retrieved}\n\n"
            "Are there any obviously missing files or modules that should be retrieved "
            "given this question? Answer with a list of file path patterns only "
            "(one per line, e.g. 'backend/db/*.py'), nothing else. "
            "If nothing is missing, respond with NONE."
        )

        try:
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
            )
            text = (response.choices[0].message.content or "").strip()
        except Exception:
            return []

        if not text or text.upper() == "NONE":
            return []

        patterns = [line.strip().strip("-* ") for line in text.splitlines()]
        return [pattern for pattern in patterns if pattern]


def _build_chunk_results(results: dict) -> list[ChunkResult]:
    ids = results.get("ids", [[]])[0]
    if not ids:
        return []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        chunks.append(ChunkResult(
            file_path=metadata["file_path"],
            chunk_name=metadata["name"],
            chunk_type=metadata["chunk_type"],
            content=document,
            # ChromaDB returns a distance (lower = more similar), not bounded to [0, 1].
            # This is a monotonic "higher = more similar" transform, not true cosine similarity.
            similarity_score=1 / (1 + distance),
            start_line=metadata["start_line"],
            end_line=metadata["end_line"],
        ))
    return chunks


def _dedupe(items) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
