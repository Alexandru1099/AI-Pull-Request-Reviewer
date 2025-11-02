from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubUserProfile(BaseModel):
    id: int
    login: str
    name: str | None = None
    avatar_url: str | None = None


class AuthSessionResponse(BaseModel):
    authenticated: bool
    status: str
    message: str | None = None
    user: GitHubUserProfile | None = None


class AuthErrorResponse(BaseModel):
    detail: str = Field(..., examples=["GitHub OAuth login failed."])
