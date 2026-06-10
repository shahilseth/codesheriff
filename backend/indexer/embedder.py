"""Local embedding wrapper around HuggingFace sentence-transformers.

Uses all-MiniLM-L6-v2: small, fast, runs on CPU/Apple Silicon, no API key
or network calls needed after the first download.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts. Returns an (n, dim) float32 numpy array."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.astype(np.float32)
