from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.config import get_settings
from app.llm_review import run_llm_review
from app.schemas.review import (
    ReviewAnalysisMetadata,
    ReviewPullRequestMetadata,
    ReviewAnalysisResponse,
    ReviewRetrievedFile,
    ReviewRetrievalMetadata,
    ReviewTokenUsage,
)


@dataclass
class ObservableReviewResult:
    review: ReviewAnalysisResponse
    metadata: ReviewAnalysisMetadata


def _count_context_chunks(
    retrieved_context: Dict[str, List[Dict[str, Any]]],
) -> int:
    return sum(len(chunks) for chunks in retrieved_context.values())


def _distance_to_similarity(score: Any) -> float | None:
    if not isinstance(score, (int, float)):
        return None
    return round(1 / (1 + max(0.0, float(score))), 2)


def _build_retrieval_metadata(
    retrieved_context: Dict[str, List[Dict[str, Any]]],
) -> ReviewRetrievalMetadata:
    top_files_by_path: dict[str, float | None] = {}

    for chunks in retrieved_context.values():
        for chunk in chunks:
            path = str(chunk.get("path") or "")
            if not path:
                continue

            similarity = _distance_to_similarity(chunk.get("score"))
            existing = top_files_by_path.get(path)
            if existing is None or (
                similarity is not None and similarity > existing
            ):
                top_files_by_path[path] = similarity

    top_files = [
        ReviewRetrievedFile(path=path, similarity=similarity)
        for path, similarity in sorted(
            top_files_by_path.items(),
            key=lambda item: (
                item[1] is not None,
                item[1] if item[1] is not None else -1.0,
            ),
            reverse=True,
        )[:8]
    ]

    return ReviewRetrievalMetadata(
        chunks_used=_count_context_chunks(retrieved_context),
        top_files=top_files,
    )


def _calculate_estimated_cost(
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float | None:
    if prompt_tokens is None and completion_tokens is None:
        return None

    settings = get_settings()
    cost = (
        (prompt_tokens or 0) * settings.openai_prompt_token_price
        + (completion_tokens or 0) * settings.openai_completion_token_price
    )
    return round(cost, 6)


def run_observable_llm_review(
    *,
    title: str,
    description: str,
    changed_files: List[Dict[str, Any]],
    retrieved_context: Dict[str, List[Dict[str, Any]]],
    pull_request_metadata: ReviewPullRequestMetadata,
    review_mode: str = "repository-aware",
) -> ObservableReviewResult:
    started_at = datetime.now(timezone.utc)
    llm_result = run_llm_review(
        title=title,
        description=description,
        changed_files=changed_files,
        retrieved_context=retrieved_context,
    )

    metadata = ReviewAnalysisMetadata(
        model=llm_result.metadata.model,
        latency_ms=llm_result.metadata.latency_ms,
        prompt_tokens=llm_result.metadata.prompt_tokens,
        completion_tokens=llm_result.metadata.completion_tokens,
        total_tokens=llm_result.metadata.total_tokens,
        token_usage=ReviewTokenUsage(
            prompt_tokens=llm_result.metadata.prompt_tokens,
            completion_tokens=llm_result.metadata.completion_tokens,
            total_tokens=llm_result.metadata.total_tokens,
            estimated_cost=_calculate_estimated_cost(
                llm_result.metadata.prompt_tokens,
                llm_result.metadata.completion_tokens,
            ),
        ),
        pr=pull_request_metadata,
        retrieval=_build_retrieval_metadata(retrieved_context),
        context_chunks=_count_context_chunks(retrieved_context),
        review_mode=review_mode,
        timestamp=started_at,
    )

    review = llm_result.review.model_copy(update={"analysis_metadata": metadata})
    return ObservableReviewResult(review=review, metadata=metadata)
