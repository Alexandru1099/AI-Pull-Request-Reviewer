from __future__ import annotations

from fastapi import APIRouter
from starlette import status

from app.schemas.evaluation import (
    EvaluationMetricsResponse,
    IssueEvaluationRequest,
    IssueEvaluationResponse,
)
from app.services.evaluation_store import evaluation_store

router = APIRouter()


@router.get(
    "/api/review/evaluations/metrics",
    response_model=EvaluationMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregate issue evaluation metrics",
)
async def get_evaluation_metrics() -> EvaluationMetricsResponse:
    return evaluation_store.get_metrics()


@router.post(
    "/api/review/evaluations/issues",
    response_model=IssueEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Record an evaluation label for a review issue",
)
async def evaluate_issue(payload: IssueEvaluationRequest) -> IssueEvaluationResponse:
    metrics = evaluation_store.record(
        pr_url=str(payload.pr_url),
        issue_key=payload.issue_key,
        severity=payload.severity,
        category=payload.category,
        title=payload.title,
        file=payload.file,
        line=payload.line,
        label=payload.label,
    )
    return IssueEvaluationResponse(
        issue_key=payload.issue_key,
        label=payload.label,
        metrics=metrics,
    )
