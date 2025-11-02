from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from starlette import status

from app.core.config import get_settings
from app.diff_parser import ParsedHunk
from app.github.client import (
    GitHubApiError,
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubTimeoutError,
    GitHubUnauthorizedError,
)
from app.github.url_parser import PullRequestUrlError, parse_github_pr_url
from app.retriever import build_index_and_retrieve
from app.schemas.diff import ParseDiffRequest
from app.schemas.review import (
    ReviewAnalysisMetadata,
    ReviewPullRequestMetadata,
    ReviewAnalysisResponse,
    ReviewRetrievalMetadata,
    ReviewIssue,
    ReviewTokenUsage,
)
from app.services.ai_review_service import run_observable_llm_review
from app.services.github_auth_service import (
    detect_pull_request_access_mode,
    fetch_pull_request_files_with_optional_auth,
    fetch_pull_request_preview_with_optional_auth,
    get_github_access_token_from_request,
)

router = APIRouter()

logger = logging.getLogger("repo_aware.api.analyze")


@router.post(
    "/api/review/analyze",
    response_model=ReviewAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a pull request using the review engine",
)
async def analyze_pull_request(
    request: Request,
    payload: ParseDiffRequest,
) -> ReviewAnalysisResponse:
    """
    Analyze a pull request using either the LLM-based engine or the deterministic
    heuristic fallback, depending on configuration.
    """
    settings = get_settings()

    try:
        parsed = parse_github_pr_url(str(payload.pr_url))
    except PullRequestUrlError as exc:
        logger.info(
            "Invalid PR URL received for analyze",
            extra={"pr_url": str(payload.pr_url), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    client = GitHubClient()
    access_token = get_github_access_token_from_request(request)
    access_mode = "public"

    # 1) GitHub fetch: preview & files
    t0 = time.monotonic()
    try:
        access_result = await detect_pull_request_access_mode(
            client=client,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            access_token=access_token,
        )
        access_mode = access_result.mode
        preview = await fetch_pull_request_preview_with_optional_auth(
            client=client,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            access_token=access_token,
        )
        files = await fetch_pull_request_files_with_optional_auth(
            client=client,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            access_token=access_token,
        )
    except GitHubNotFoundError as exc:
        logger.info(
            "GitHub pull request or files not found for analysis",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GitHubUnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Your GitHub session has expired. Reconnect GitHub and try again."
            ),
        ) from exc
    except GitHubForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your GitHub account does not have access to this pull request."
            ),
        ) from exc
    except GitHubTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub took too long to respond. Please try again.",
        ) from exc
    except GitHubApiError as exc:
        logger.warning(
            "GitHub API error while fetching data for analysis",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch pull request data from GitHub.",
        ) from exc
    except Exception as exc:  # defensive
        logger.error(
            "Unexpected error while fetching data for analysis",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected error while contacting GitHub.",
        ) from exc
    t_github = time.monotonic() - t0
    logger.info(
        "GitHub fetch for analyze completed",
        extra={
            "elapsed_ms": int(t_github * 1000),
            "access_mode": access_mode,
        },
    )

    # If configured for mock mode, short-circuit to heuristics.
    if settings.use_mock_review:
        logger.info("Using mocked heuristic review engine (USE_MOCK_REVIEW=true).")
        return _run_heuristic_review(
            files,
            _build_pull_request_metadata(
                owner=parsed.owner,
                repo=parsed.repo,
                pull_number=parsed.pull_number,
                author=str(preview.get("author") or ""),
                changed_files_count=int(preview.get("changed_files_count") or 0),
            ),
        )

    # 2) Retrieval (for repository context)
    t1 = time.monotonic()
    retrieved_by_path = await build_index_and_retrieve(
        owner=parsed.owner,
        repo=parsed.repo,
        pull_number=parsed.pull_number,
        files=files,
        top_k=5,
        access_token=access_token,
    )
    t_retrieval = time.monotonic() - t1
    logger.info(
        "Retrieval for analyze completed",
        extra={
            "elapsed_ms": int(t_retrieval * 1000),
            "access_mode": access_mode,
            "private_access": access_mode == "authenticated_private",
        },
    )

    # 3) LLM-based review
    # Build simple diff summary per file for prompt input.
    changed_files: List[Dict[str, Any]] = []
    for file in files:
        changed_files.append(
            {
                "path": file.get("path") or "",
                "status": file.get("status") or "",
                "additions": int(file.get("additions") or 0),
                "deletions": int(file.get("deletions") or 0),
                "patch": file.get("patch") or "",
            }
        )

    # Compact retrieval context for prompt.
    retrieval_for_prompt: Dict[str, List[Dict[str, Any]]] = {}
    for path, chunks in retrieved_by_path.items():
        retrieval_for_prompt[path] = [
            {
                "path": c.path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content": c.content,
                "score": c.score,
            }
            for c in chunks
        ]

    title = str(preview.get("title") or "")
    description = str(preview.get("body") or "")

    t2 = time.monotonic()
    review_result = run_observable_llm_review(
        title=title,
        description=description,
        changed_files=changed_files,
        retrieved_context=retrieval_for_prompt,
        pull_request_metadata=_build_pull_request_metadata(
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            author=str(preview.get("author") or ""),
            changed_files_count=int(preview.get("changed_files_count") or 0),
            files=files,
        ),
        review_mode="repository-aware",
    )
    t_llm = time.monotonic() - t2
    logger.info(
        "LLM review completed",
        extra={
            "elapsed_ms": int(t_llm * 1000),
            "model": review_result.metadata.model,
            "prompt_tokens": review_result.metadata.prompt_tokens,
            "completion_tokens": review_result.metadata.completion_tokens,
            "total_tokens": review_result.metadata.total_tokens,
            "context_chunks": review_result.metadata.context_chunks,
            "review_mode": review_result.metadata.review_mode,
            "access_mode": access_mode,
        },
    )

    return review_result.review


def _run_heuristic_review(
    files: list[dict[str, Any]],
    pull_request_metadata: ReviewPullRequestMetadata,
) -> ReviewAnalysisResponse:
    from app.diff_parser import parse_unified_diff

    issues: list[ReviewIssue] = []

    for file in files:
        path = file.get("path") or ""
        patch = file.get("patch")
        hunks = parse_unified_diff(patch)
        issues.extend(_run_heuristics_over_file(path, hunks))

    sev_counter = Counter(issue.severity for issue in issues)
    critical_count = sev_counter.get("critical", 0)
    warning_count = sev_counter.get("warning", 0)
    suggestion_count = sev_counter.get("suggestion", 0)

    score = 100
    score -= critical_count * 25
    score -= warning_count * 10
    score -= suggestion_count * 3
    score = max(0, min(100, score))

    if issues:
        summary = (
            f"Static heuristics found {critical_count} critical, "
            f"{warning_count} warnings, and {suggestion_count} suggestions."
        )
    else:
        summary = "Static heuristics did not detect any obvious issues in this diff."

    return ReviewAnalysisResponse(
        summary=summary,
        quality_score=score,
        critical_count=critical_count,
        warning_count=warning_count,
        suggestion_count=suggestion_count,
        issues=issues,
        analysis_metadata=ReviewAnalysisMetadata(
            model=None,
            latency_ms=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            token_usage=ReviewTokenUsage(
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                estimated_cost=None,
            ),
            pr=pull_request_metadata,
            retrieval=ReviewRetrievalMetadata(
                chunks_used=0,
                top_files=[],
            ),
            context_chunks=0,
            review_mode="mock-heuristic",
            timestamp=datetime.now(timezone.utc),
        ),
    )


def _build_pull_request_metadata(
    *,
    owner: str,
    repo: str,
    pull_number: int,
    author: str,
    changed_files_count: int,
    files: list[dict[str, Any]] | None = None,
) -> ReviewPullRequestMetadata:
    additions = 0
    deletions = 0

    for file in files or []:
        additions += int(file.get("additions") or 0)
        deletions += int(file.get("deletions") or 0)

    return ReviewPullRequestMetadata(
        repository=f"{owner}/{repo}",
        pr_number=pull_number,
        author=author,
        files_changed=changed_files_count,
        additions=additions,
        deletions=deletions,
    )


def _run_heuristics_over_file(path: str, hunks: list[ParsedHunk]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []

    for hunk in hunks:
        new_line = hunk.new_start
        for line in hunk.lines:
            if line.type in ("context", "added"):
                effective_line = new_line
                new_line += 1
            else:
                effective_line = None

            if line.type != "added":
                continue

            content = line.content

            if "eval(" in content:
                issues.append(
                    ReviewIssue(
                        severity="critical",
                        category="dangerous-api",
                        title="Use of eval detected",
                        file=path,
                        line=effective_line,
                        explanation=(
                            "This change introduces usage of eval(), which can execute "
                            "arbitrary code and is usually considered unsafe."
                        ),
                        suggestion=(
                            "Avoid eval() and prefer explicit, typed APIs or a safe "
                            "parser for the required behavior."
                        ),
                        evidence=[content],
                    )
                )
            if ".map(" in content or "map(" in content:
                issues.append(
                    ReviewIssue(
                        severity="suggestion",
                        category="api-usage",
                        title="Array map usage",
                        file=path,
                        line=effective_line,
                        explanation=(
                            "This change uses map(). Ensure the source array is "
                            "always defined and not null or undefined."
                        ),
                        suggestion=(
                            "Guard the array before calling map(), e.g. "
                            "`(items ?? []).map(...)`, or add runtime/type checks."
                        ),
                        evidence=[content],
                    )
                )
            if "SELECT " in content and "+" in content:
                issues.append(
                    ReviewIssue(
                        severity="warning",
                        category="sql-safety",
                        title="String-built SQL query",
                        file=path,
                        line=effective_line,
                        explanation=(
                            "This change appears to build a SQL query using string "
                            "concatenation, which can lead to SQL injection risks."
                        ),
                        suggestion=(
                            "Use parameterized queries or a query builder instead of "
                            "concatenating SQL strings."
                        ),
                        evidence=[content],
                    )
                )

    return issues
