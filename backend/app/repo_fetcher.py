from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.github.client import PullRequestFile

logger = logging.getLogger("repo_aware.repo_fetcher")


async def fetch_file_content(file: PullRequestFile) -> Optional[str]:
    """
    Backward-compatible unauthenticated content fetch for public files.
    """
    return await fetch_file_content_with_token(file, access_token=None)


async def fetch_file_content_with_token(
    file: PullRequestFile,
    access_token: str | None = None,
) -> Optional[str]:
    """
    Fetch raw file contents with optional authenticated GitHub access for
    private repositories. Returns None when content is unavailable so the
    retrieval pipeline can safely continue with partial context.
    """
    raw_url = file.get("raw_url")
    if not raw_url:
        logger.info(
            "No raw_url for file; skipping content fetch",
            extra={"path": file.get("path")},
        )
        return None

    headers = {"User-Agent": "repo-aware-pr-reviewer/0.1.0"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(raw_url, headers=headers)
    except Exception as exc:
        logger.warning(
            "Failed to fetch raw file content",
            extra={"path": file.get("path"), "raw_url": raw_url, "error": str(exc)},
        )
        return None

    if response.status_code != 200:
        logger.warning(
            "Non-200 while fetching raw file content",
            extra={
                "path": file.get("path"),
                "raw_url": raw_url,
                "status_code": response.status_code,
                "authenticated": access_token is not None,
            },
        )
        return None

    try:
        return response.text
    except Exception:
        logger.warning(
            "Failed to decode file content as text",
            extra={"path": file.get("path"), "raw_url": raw_url},
        )
        return None
