from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


EvaluationLabel = Literal["correct", "false_positive"]


class IssueEvaluationRequest(BaseModel):
    pr_url: HttpUrl
    issue_key: str = Field(min_length=1)
    severity: str
    category: str
    title: str
    file: str
    line: int | None = None
    label: EvaluationLabel


class EvaluationMetricsResponse(BaseModel):
    total_issues: int
    correct_issues: int
    false_positives: int
    total_expected: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None


class IssueEvaluationResponse(BaseModel):
    issue_key: str
    label: EvaluationLabel
    metrics: EvaluationMetricsResponse
