from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from starlette import status

from app.diff_parser import parse_unified_diff
from app.github.client import (
    GitHubApiError,
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubTimeoutError,
    GitHubUnauthorizedError,
)
from app.github.url_parser import PullRequestUrlError, parse_github_pr_url
from app.schemas.diff import (
    ParseDiffRequest,
    ParsedDiffResponse,
    ParsedFileModel,
    ParsedHunkModel,
)
from app.services.github_auth_service import (
    fetch_pull_request_files_with_optional_auth,
    get_github_access_token_from_request,
)

router = APIRouter()

logger = logging.getLogger("repo_aware.api.diff")


@router.post(
    "/api/review/parse-diff",
    response_model=ParsedDiffResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse GitHub pull request diff into structured hunks",
)
async def parse_diff(request: Request, payload: ParseDiffRequest) -> ParsedDiffResponse:
    """
    Fetch the changed files for a public GitHub pull request and parse the
    unified diff into structured hunks.
    """
    try:
        parsed = parse_github_pr_url(str(payload.pr_url))
    except PullRequestUrlError as exc:
        logger.info(
            "Invalid PR URL received for parse-diff",
            extra={"pr_url": str(payload.pr_url), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    client = GitHubClient()
    access_token = get_github_access_token_from_request(request)

    try:
        files = await fetch_pull_request_files_with_optional_auth(
            client=client,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            access_token=access_token,
        )
    except GitHubNotFoundError as exc:
        logger.info(
            "GitHub pull request files not found",
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
            "GitHub API error while fetching pull request files",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch pull request files from GitHub.",
        ) from exc
    except Exception as exc:  # defensive
        logger.error(
            "Unexpected error while fetching pull request files",
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

    parsed_files: list[ParsedFileModel] = []

    for file in files:
        hunks = parse_unified_diff(file.get("patch"))
        parsed_files.append(
            ParsedFileModel(
                path=file.get("path") or "",
                status=file.get("status") or "",
                additions=int(file.get("additions") or 0),
                deletions=int(file.get("deletions") or 0),
                patch=file.get("patch"),
                parsed_hunks=[ParsedHunkModel.from_parsed(h) for h in hunks],
            )
        )

    return ParsedDiffResponse(
        owner=parsed.owner,
        repo=parsed.repo,
        pull_number=parsed.pull_number,
        files=parsed_files,
    )
