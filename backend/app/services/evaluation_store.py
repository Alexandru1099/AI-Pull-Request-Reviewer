from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.schemas.evaluation import EvaluationLabel, EvaluationMetricsResponse


@dataclass
class StoredEvaluation:
    pr_url: str
    issue_key: str
    severity: str
    category: str
    title: str
    file: str
    line: int | None
    label: EvaluationLabel


class EvaluationStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._evaluations: dict[str, StoredEvaluation] = {}
        self._total_expected: int | None = None

    def record(
        self,
        *,
        pr_url: str,
        issue_key: str,
        severity: str,
        category: str,
        title: str,
        file: str,
        line: int | None,
        label: EvaluationLabel,
    ) -> EvaluationMetricsResponse:
        with self._lock:
            storage_key = f"{pr_url}::{issue_key}"
            self._evaluations[storage_key] = StoredEvaluation(
                pr_url=pr_url,
                issue_key=issue_key,
                severity=severity,
                category=category,
                title=title,
                file=file,
                line=line,
                label=label,
            )
            return self._build_metrics()

    def get_metrics(self) -> EvaluationMetricsResponse:
        with self._lock:
            return self._build_metrics()

    def _build_metrics(self) -> EvaluationMetricsResponse:
        total_issues = len(self._evaluations)
        correct_issues = sum(
            1 for evaluation in self._evaluations.values() if evaluation.label == "correct"
        )
        false_positives = sum(
            1
            for evaluation in self._evaluations.values()
            if evaluation.label == "false_positive"
        )

        precision = None
        if correct_issues + false_positives > 0:
            precision = correct_issues / (correct_issues + false_positives)

        recall = None
        if self._total_expected and self._total_expected > 0:
            recall = correct_issues / self._total_expected

        f1_score = None
        if (
            precision is not None
            and recall is not None
            and (precision + recall) > 0
        ):
            f1_score = 2 * precision * recall / (precision + recall)

        return EvaluationMetricsResponse(
            total_issues=total_issues,
            correct_issues=correct_issues,
            false_positives=false_positives,
            total_expected=self._total_expected,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
        )


evaluation_store = EvaluationStore()
