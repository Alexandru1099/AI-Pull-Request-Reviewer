from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from starlette import status

from app.github.client import (
    GitHubApiError,
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubUnauthorizedError,
)
from app.github.url_parser import PullRequestUrlError, parse_github_pr_url
from app.schemas.review import (
    PullRequestPreviewRequest,
    PullRequestPreviewResponse,
)
from app.services.auth_cookie import get_auth_session_from_request
from app.services.github_auth_service import (
    fetch_pull_request_preview_with_optional_auth,
)

router = APIRouter()

logger = logging.getLogger("repo_aware.api.review")


@router.post(
    "/api/review/pr-preview",
    response_model=PullRequestPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview a GitHub pull request",
)
async def preview_pull_request(
    request: Request,
    payload: PullRequestPreviewRequest,
) -> PullRequestPreviewResponse:
    """
    Validate a public GitHub PR URL, fetch metadata from GitHub, and return a
    concise preview response.
    """
    try:
        parsed = parse_github_pr_url(str(payload.pr_url))
    except PullRequestUrlError as exc:
        logger.info(
            "Invalid PR URL received",
            extra={
                "pr_url": str(payload.pr_url),
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    client = GitHubClient()
    auth_session = get_auth_session_from_request(request)
    access_token = auth_session.access_token if auth_session else None

    try:
        preview_dict = await fetch_pull_request_preview_with_optional_auth(
            client=client,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pull_number,
            access_token=access_token,
        )
        return PullRequestPreviewResponse.from_parsed_and_preview(
            parsed,
            preview_dict,
            authenticated=auth_session is not None,
        )
    except GitHubNotFoundError as exc:
        logger.info(
            "Public GitHub pull request lookup did not succeed",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )

        try:
            await client.fetch_repository_metadata(
                owner=parsed.owner,
                repo=parsed.repo,
            )
        except GitHubNotFoundError:
            if auth_session is None:
                return PullRequestPreviewResponse(
                    owner=parsed.owner,
                    repo=parsed.repo,
                    pull_number=parsed.pull_number,
                    access_required=True,
                    reason="private_repo",
                    message=(
                        "This pull request may belong to a private repository. "
                        "Connect GitHub to verify access and continue."
                    ),
                    authenticated=False,
                )

            try:
                await client.fetch_repository_metadata(
                    owner=parsed.owner,
                    repo=parsed.repo,
                    access_token=access_token,
                )
                preview_dict = await client.fetch_pull_request_preview(
                    owner=parsed.owner,
                    repo=parsed.repo,
                    pull_number=parsed.pull_number,
                    access_token=access_token,
                )
                return PullRequestPreviewResponse.from_parsed_and_preview(
                    parsed,
                    preview_dict,
                    authenticated=True,
                )
            except GitHubForbiddenError:
                return PullRequestPreviewResponse(
                    owner=parsed.owner,
                    repo=parsed.repo,
                    pull_number=parsed.pull_number,
                    access_required=True,
                    reason="insufficient_permissions",
                    message=(
                        "Your GitHub account is connected, but it does not appear "
                        "to have access to this repository or pull request."
                    ),
                    authenticated=True,
                )
            except GitHubUnauthorizedError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=(
                        "Your GitHub session has expired. Reconnect GitHub and try again."
                    ),
                ) from exc
            except GitHubNotFoundError:
                return PullRequestPreviewResponse(
                    owner=parsed.owner,
                    repo=parsed.repo,
                    pull_number=parsed.pull_number,
                    access_required=False,
                    reason="not_found",
                    message=(
                        "We could not find that pull request. Check the repository "
                        "and pull request number, then try again."
                    ),
                    authenticated=True,
                )
        else:
            return PullRequestPreviewResponse(
                owner=parsed.owner,
                repo=parsed.repo,
                pull_number=parsed.pull_number,
                access_required=False,
                reason="not_found",
                message=(
                    "We could not find that pull request. Check the repository "
                    "and pull request number, then try again."
                ),
                authenticated=auth_session is not None,
            )
    except GitHubUnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Your GitHub session has expired. Reconnect GitHub and try again."
            ),
        ) from exc
    except GitHubApiError as exc:
        logger.warning(
            "GitHub API error while fetching pull request",
            extra={
                "owner": parsed.owner,
                "repo": parsed.repo,
                "pull_number": parsed.pull_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch pull request from GitHub.",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Unexpected error while fetching pull request preview",
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
