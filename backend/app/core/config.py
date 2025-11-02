from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Repo-Aware AI Pull Request Reviewer"
    environment: str = Field("development", alias="APP_ENV")
    backend_port: int = Field(8000, alias="BACKEND_PORT")
    log_level: str = Field("info", alias="BACKEND_LOG_LEVEL")
    allow_origins_raw: str = Field(
        default="http://localhost:3000",
        alias="BACKEND_ALLOW_ORIGINS",
    )
    use_mock_review: bool = Field(True, alias="USE_MOCK_REVIEW")
    llm_model: str = Field("gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_prompt_token_price: float = Field(
        0.00000015,
        alias="OPENAI_PROMPT_TOKEN_PRICE",
    )
    openai_completion_token_price: float = Field(
        0.0000006,
        alias="OPENAI_COMPLETION_TOKEN_PRICE",
    )
    github_client_id: str | None = Field(None, alias="GITHUB_CLIENT_ID")
    github_client_secret: str | None = Field(None, alias="GITHUB_CLIENT_SECRET")
    github_oauth_redirect_uri: str | None = Field(
        None,
        alias="GITHUB_OAUTH_REDIRECT_URI",
    )
    github_oauth_scope: str = Field("read:user repo", alias="GITHUB_OAUTH_SCOPE")
    session_secret: str | None = Field(None, alias="SESSION_SECRET")
    auth_session_ttl_seconds: int = Field(
        60 * 60 * 24 * 7,
        alias="AUTH_SESSION_TTL_SECONDS",
    )
    auth_state_ttl_seconds: int = Field(
        60 * 10,
        alias="AUTH_STATE_TTL_SECONDS",
    )

    @property
    def allow_origins(self) -> List[str]:
        return [item.strip() for item in self.allow_origins_raw.split(",") if item.strip()]

    @property
    def frontend_app_url(self) -> str:
        return self.allow_origins[0] if self.allow_origins else "http://localhost:3000"

    @property
    def secure_cookies(self) -> bool:
        return self.environment.lower() == "production"

    def validate_auth_settings(self) -> None:
        missing = [
            name
            for name, value in (
                ("GITHUB_CLIENT_ID", self.github_client_id),
                ("GITHUB_CLIENT_SECRET", self.github_client_secret),
                ("GITHUB_OAUTH_REDIRECT_URI", self.github_oauth_redirect_uri),
                ("SESSION_SECRET", self.session_secret),
            )
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing required GitHub OAuth environment variables: "
                + ", ".join(missing)
            )

        if self.session_secret is not None and len(self.session_secret) < 32:
            raise ValueError("SESSION_SECRET must be at least 32 characters long.")

        if self.auth_session_ttl_seconds <= 0:
            raise ValueError("AUTH_SESSION_TTL_SECONDS must be greater than 0.")

        if self.auth_state_ttl_seconds <= 0:
            raise ValueError("AUTH_STATE_TTL_SECONDS must be greater than 0.")

        if not self.github_oauth_scope.strip():
            raise ValueError("GITHUB_OAUTH_SCOPE must not be empty.")

        parsed_redirect = urlparse(self.github_oauth_redirect_uri or "")
        if parsed_redirect.scheme not in {"http", "https"} or not parsed_redirect.netloc:
            raise ValueError("GITHUB_OAUTH_REDIRECT_URI must be a valid absolute URL.")

    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
