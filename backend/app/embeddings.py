from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

from sentence_transformers import SentenceTransformer


@lru_cache
def _get_model() -> SentenceTransformer:
    # Small, widely used general-purpose model.
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    """
    Compute embeddings for a list of texts.
    """
    model = _get_model()
    vectors = model.encode(
        list(texts),
        convert_to_numpy=False,
        normalize_embeddings=True,
    )
    return [list(v) for v in vectors]

