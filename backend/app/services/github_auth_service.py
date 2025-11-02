from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.github.client import (
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubUnauthorizedError,
    PullRequestFile,
    PullRequestPreview,
)
from app.services.auth_cookie import get_auth_session_from_request


@dataclass(frozen=True)
class GitHubAccessResult:
    mode: str
    used_authenticated_access: bool


def get_github_access_token_from_request(request: Request) -> str | None:
    session = get_auth_session_from_request(request)
    if not session:
        return None
    return session.access_token


async def fetch_pull_request_preview_with_optional_auth(
    *,
    client: GitHubClient,
    owner: str,
    repo: str,
    pull_number: int,
    access_token: str | None,
) -> PullRequestPreview:
    try:
        return await client.fetch_pull_request_preview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
    except GitHubNotFoundError:
        if not access_token:
            raise
        return await client.fetch_pull_request_preview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            access_token=access_token,
        )
    except GitHubForbiddenError:
        if not access_token:
            raise
        return await client.fetch_pull_request_preview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            access_token=access_token,
        )


async def fetch_pull_request_files_with_optional_auth(
    *,
    client: GitHubClient,
    owner: str,
    repo: str,
    pull_number: int,
    access_token: str | None,
) -> list[PullRequestFile]:
    try:
        return await client.fetch_pull_request_files(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
    except (GitHubNotFoundError, GitHubForbiddenError):
        if not access_token:
            raise
        return await client.fetch_pull_request_files(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            access_token=access_token,
        )
    except GitHubUnauthorizedError:
        raise


async def detect_pull_request_access_mode(
    *,
    client: GitHubClient,
    owner: str,
    repo: str,
    pull_number: int,
    access_token: str | None,
) -> GitHubAccessResult:
    try:
        await client.fetch_pull_request_preview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
        return GitHubAccessResult(
            mode="public",
            used_authenticated_access=False,
        )
    except (GitHubNotFoundError, GitHubForbiddenError):
        if not access_token:
            return GitHubAccessResult(
                mode="public",
                used_authenticated_access=False,
            )

        await client.fetch_pull_request_preview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            access_token=access_token,
        )
        return GitHubAccessResult(
            mode="authenticated_private",
            used_authenticated_access=True,
        )
