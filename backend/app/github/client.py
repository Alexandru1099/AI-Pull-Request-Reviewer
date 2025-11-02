from __future__ import annotations

import logging
from typing import Any, TypedDict

import httpx

logger = logging.getLogger("repo_aware.github")


class PullRequestPreview(TypedDict, total=False):
    owner: str
    repo: str
    pull_number: int
    title: str
    state: str
    author: str
    changed_files_count: int


class PullRequestFile(TypedDict, total=False):
    path: str
    status: str
    additions: int
    deletions: int
    patch: str | None
    raw_url: str | None


class RepositoryMetadata(TypedDict, total=False):
    private: bool


class GitHubApiError(RuntimeError):
    """Generic GitHub API failure."""


class GitHubNotFoundError(GitHubApiError):
    """GitHub returned 404 for the requested resource."""


class GitHubForbiddenError(GitHubApiError):
    """GitHub returned 403 for the requested resource."""


class GitHubUnauthorizedError(GitHubApiError):
    """GitHub returned 401 for the requested resource."""


class GitHubTimeoutError(GitHubApiError):
    """GitHub request timed out."""


class GitHubClient:
    """
    Lightweight GitHub REST client for public pull requests.

    Phase 2/3 only needs unauthenticated, public PR metadata and file lists.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._base_url = "https://api.github.com"

    async def _get(self, url: str, access_token: str | None = None) -> httpx.Response:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-aware-pr-reviewer/0.1.0",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers)
            return response
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError("GitHub request timed out.") from exc

    async def fetch_pull_request_preview(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        access_token: str | None = None,
    ) -> PullRequestPreview:
        url = f"{self._base_url}/repos/{owner}/{repo}/pulls/{pull_number}"

        logger.info(
            "Fetching GitHub pull request",
            extra={
                "github_owner": owner,
                "github_repo": repo,
                "github_pull_number": pull_number,
                "github_url": url,
            },
        )

        response = await self._get(url, access_token=access_token)

        if response.status_code == 404:
            logger.warning(
                "GitHub pull request not found",
                extra={
                    "github_owner": owner,
                    "github_repo": repo,
                    "github_pull_number": pull_number,
                    "status_code": response.status_code,
                },
            )
            raise GitHubNotFoundError("Pull request not found on GitHub.")

        if response.status_code == 403:
            raise GitHubForbiddenError("GitHub access is forbidden for this pull request.")

        if response.status_code == 401:
            raise GitHubUnauthorizedError("GitHub authentication is no longer valid.")

        if response.status_code >= 400:
            logger.error(
                "GitHub API error",
                extra={
                    "github_owner": owner,
                    "github_repo": repo,
                    "github_pull_number": pull_number,
                    "status_code": response.status_code,
                },
            )
            raise GitHubApiError("GitHub API returned an error.")

        data = response.json()
        return self._map_pull_request_preview(data, owner, repo, pull_number)

    async def fetch_pull_request_files(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        access_token: str | None = None,
    ) -> list[PullRequestFile]:
        """
        Fetch the changed files for a pull request from GitHub.
        """
        url = f"{self._base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"

        logger.info(
            "Fetching GitHub pull request files",
            extra={
                "github_owner": owner,
                "github_repo": repo,
                "github_pull_number": pull_number,
                "github_url": url,
            },
        )

        response = await self._get(url, access_token=access_token)

        if response.status_code == 404:
            logger.warning(
                "GitHub pull request files not found",
                extra={
                    "github_owner": owner,
                    "github_repo": repo,
                    "github_pull_number": pull_number,
                    "status_code": response.status_code,
                },
            )
            raise GitHubNotFoundError("Pull request files not found on GitHub.")

        if response.status_code == 403:
            raise GitHubForbiddenError("GitHub access is forbidden for pull request files.")

        if response.status_code == 401:
            raise GitHubUnauthorizedError("GitHub authentication is no longer valid.")

        if response.status_code >= 400:
            logger.error(
                "GitHub API error while fetching files",
                extra={
                    "github_owner": owner,
                    "github_repo": repo,
                    "github_pull_number": pull_number,
                    "status_code": response.status_code,
                },
            )
            raise GitHubApiError("GitHub API returned an error.")

        data = response.json()
        files: list[PullRequestFile] = []
        for item in data:
            files.append(
                PullRequestFile(
                    path=item.get("filename") or "",
                    status=item.get("status") or "",
                    additions=int(item.get("additions") or 0),
                    deletions=int(item.get("deletions") or 0),
                    patch=item.get("patch"),
                    raw_url=item.get("raw_url"),
                )
            )
        return files

    async def fetch_repository_metadata(
        self,
        owner: str,
        repo: str,
        access_token: str | None = None,
    ) -> RepositoryMetadata:
        url = f"{self._base_url}/repos/{owner}/{repo}"
        response = await self._get(url, access_token=access_token)

        if response.status_code == 404:
            raise GitHubNotFoundError("Repository not found on GitHub.")

        if response.status_code == 403:
            raise GitHubForbiddenError("GitHub access is forbidden for this repository.")

        if response.status_code == 401:
            raise GitHubUnauthorizedError("GitHub authentication is no longer valid.")

        if response.status_code >= 400:
            raise GitHubApiError("GitHub API returned an error.")

        data = response.json()
        return RepositoryMetadata(private=bool(data.get("private")))

    @staticmethod
    def _map_pull_request_preview(
        data: dict[str, Any],
        owner: str,
        repo: str,
        pull_number: int,
    ) -> PullRequestPreview:
        return PullRequestPreview(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            title=data.get("title") or "",
            state=data.get("state") or "",
            author=(data.get("user") or {}).get("login") or "",
            changed_files_count=int(data.get("changed_files") or 0),
        )
