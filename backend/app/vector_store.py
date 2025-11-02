from __future__ import annotations

from typing import Any, Dict, Sequence

import chromadb
from chromadb.config import Settings

_client: chromadb.Client | None = None


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.Client(Settings())
    return _client


def create_collection(name: str):
    client = get_client()
    try:
        client.delete_collection(name)
    except Exception:
        # If it doesn't exist, that's fine.
        pass
    return client.create_collection(name=name)


def add_documents(
    collection,
    ids: Sequence[str],
    texts: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    metadatas: Sequence[Dict[str, Any]],
) -> None:
    collection.add(
        ids=list(ids),
        documents=list(texts),
        metadatas=list(metadatas),
        embeddings=list(embeddings),
    )


def query_top_k(
    collection,
    query_text: str,
    n_results: int = 5,
) -> Dict[str, Any]:
    return collection.query(
        query_texts=[query_text],
        n_results=n_results,
    )

