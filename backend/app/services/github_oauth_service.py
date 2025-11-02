from __future__ import annotations

import secrets
from typing import Any, Dict
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.schemas.auth import GitHubUserProfile

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
class GitHubOAuthError(RuntimeError):
    """Raised when the GitHub OAuth flow fails safely."""


def create_github_login_url(state: str) -> str:
    settings = get_settings()
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_oauth_redirect_uri,
            "scope": settings.github_oauth_scope,
            "state": state,
        }
    )
    return f"{GITHUB_AUTHORIZE_URL}?{params}"


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


async def exchange_code_for_token(code: str) -> str:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": "repo-aware-pr-reviewer/0.1.0",
            },
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
            },
        )

    if response.status_code >= 400:
        raise GitHubOAuthError("GitHub token exchange failed.")

    data = response.json()
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GitHubOAuthError("GitHub did not return an access token.")

    return access_token


async def fetch_authenticated_user(access_token: str) -> GitHubUserProfile:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "repo-aware-pr-reviewer/0.1.0",
            },
        )

    if response.status_code >= 400:
        raise GitHubOAuthError("Failed to fetch authenticated GitHub user.")

    data: Dict[str, Any] = response.json()
    return GitHubUserProfile(
        id=int(data.get("id") or 0),
        login=str(data.get("login") or ""),
        name=str(data.get("name")) if data.get("name") is not None else None,
        avatar_url=(
            str(data.get("avatar_url")) if data.get("avatar_url") is not None else None
        ),
    )
