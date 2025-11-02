from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.chunker import Chunk, chunk_file_content
from app.embeddings import embed_texts
from app.github.client import PullRequestFile
from app.repo_fetcher import fetch_file_content_with_token
from app.vector_store import add_documents, create_collection, query_top_k


@dataclass(frozen=True)
class RetrievedChunk:
    path: str
    start_line: int
    end_line: int
    content: str
    score: float


async def build_index_and_retrieve(
    owner: str,
    repo: str,
    pull_number: int,
    files: List[PullRequestFile],
    top_k: int = 5,
    access_token: str | None = None,
) -> Dict[str, List[RetrievedChunk]]:
    """
    For each changed file, fetch content (if available), chunk, embed, index in
    Chroma, and query for the most relevant chunks using the file path as query.
    """
    collection_name = f"pr-{owner}-{repo}-{pull_number}-debug"
    collection = create_collection(collection_name)

    all_chunks: List[Chunk] = []

    for file in files:
        path = file.get("path") or ""
        content = await fetch_file_content_with_token(file, access_token=access_token)
        if not content:
            continue
        file_chunks = chunk_file_content(path=path, content=content)
        all_chunks.extend(file_chunks)

    if not all_chunks:
        return {}

    texts = [c.content for c in all_chunks]
    embeddings = embed_texts(texts)

    ids = [f"{c.path}:{c.start_line}-{c.end_line}" for c in all_chunks]
    metadatas: List[Dict[str, Any]] = [
        {"path": c.path, "start_line": c.start_line, "end_line": c.end_line}
        for c in all_chunks
    ]

    add_documents(
        collection,
        ids=ids,
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    results: Dict[str, List[RetrievedChunk]] = {}

    for file in files:
        path = file.get("path") or ""
        if not path:
            continue

        query_result = query_top_k(
            collection,
            query_text=path,
            n_results=top_k,
        )

        docs = query_result.get("documents") or [[]]
        metas = query_result.get("metadatas") or [[]]
        dists = query_result.get("distances") or [[]]

        retrieved: List[RetrievedChunk] = []
        for doc, meta, dist in zip(docs[0], metas[0], dists[0]):
            retrieved.append(
                RetrievedChunk(
                    path=str(meta.get("path", "")),
                    start_line=int(meta.get("start_line", 0)),
                    end_line=int(meta.get("end_line", 0)),
                    content=doc,
                    score=float(dist),
                )
            )
        results[path] = retrieved

    return results
