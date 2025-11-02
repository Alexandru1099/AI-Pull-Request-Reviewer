from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.github.url_parser import ParsedPullRequestUrl, parse_github_pr_url


AccessReason = Literal["private_repo", "insufficient_permissions", "not_found"]


class PullRequestPreviewRequest(BaseModel):
    pr_url: HttpUrl

    @field_validator("pr_url")
    @classmethod
    def validate_github_pr_url(cls, value: HttpUrl) -> HttpUrl:
        # This will raise a PullRequestUrlError for invalid formats, which we’ll
        # convert in the route layer to a 400 response.
        parse_github_pr_url(str(value))
        return value


class PullRequestPreviewResponse(BaseModel):
    owner: str
    repo: str
    pull_number: int
    title: str | None = None
    state: str | None = None
    author: str | None = None
    changed_files_count: int | None = None
    access_required: bool = False
    reason: AccessReason | None = None
    message: str | None = None
    authenticated: bool = False

    @classmethod
    def from_parsed_and_preview(
        cls,
        parsed: ParsedPullRequestUrl,
        data: dict[str, object],
        *,
        authenticated: bool = False,
    ) -> "PullRequestPreviewResponse":
        return cls(
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            title=str(data.get("title") or ""),
            state=str(data.get("state") or ""),
            author=str(data.get("author") or ""),
            changed_files_count=int(data.get("changed_files_count") or 0),
            access_required=False,
            reason=None,
            message=None,
            authenticated=authenticated,
        )


class ReviewIssue(BaseModel):
    severity: str
    category: str
    title: str
    file: str
    line: int | None = None
    explanation: str
    suggestion: str
    evidence: list[str] = Field(default_factory=list)


class ReviewTokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None


class ReviewPullRequestMetadata(BaseModel):
    repository: str
    pr_number: int
    author: str
    files_changed: int
    additions: int
    deletions: int


class ReviewRetrievedFile(BaseModel):
    path: str
    similarity: float | None = None


class ReviewRetrievalMetadata(BaseModel):
    chunks_used: int = 0
    top_files: list[ReviewRetrievedFile] = Field(default_factory=list)


class ReviewAnalysisMetadata(BaseModel):
    model: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    token_usage: ReviewTokenUsage | None = None
    pr: ReviewPullRequestMetadata | None = None
    retrieval: ReviewRetrievalMetadata | None = None
    context_chunks: int = 0
    review_mode: str
    timestamp: datetime


class ReviewAnalysisResponse(BaseModel):
    summary: str
    quality_score: int
    critical_count: int
    warning_count: int
    suggestion_count: int
    issues: list[ReviewIssue]
    analysis_metadata: ReviewAnalysisMetadata | None = None
