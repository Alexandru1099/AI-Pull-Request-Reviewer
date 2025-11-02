from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from starlette import status

from app.core.config import get_settings
from app.schemas.auth import AuthSessionResponse
from app.services.auth_cookie import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    delete_signed_cookie,
    get_auth_session_from_request,
    set_signed_cookie,
    unsign_cookie_value,
)
from app.services.auth_session_store import auth_session_store
from app.services.github_oauth_service import (
    GitHubOAuthError,
    create_github_login_url,
    exchange_code_for_token,
    fetch_authenticated_user,
    generate_oauth_state,
)

router = APIRouter()

logger = logging.getLogger("repo_aware.api.auth")


def _frontend_error_redirect(error_code: str) -> RedirectResponse:
    settings = get_settings()
    return RedirectResponse(
        url=f"{settings.frontend_app_url}?auth_error={error_code}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


def _require_auth_config() -> None:
    settings = get_settings()
    try:
        settings.validate_auth_settings()
    except ValueError as exc:
        logger.error(
            "GitHub auth configuration is invalid",
            extra={"auth_event": "config_validation_failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub authentication is not configured correctly.",
        ) from exc


def _log_auth_event(
    event: str,
    *,
    request: Request | None = None,
    login: str | None = None,
    outcome: str | None = None,
) -> None:
    logger.info(
        "Auth event",
        extra={
            "auth_event": event,
            "path": request.url.path if request else None,
            "request_id": request.headers.get("x-request-id") if request else None,
            "github_login": login,
            "outcome": outcome,
        },
    )


@router.get(
    "/api/auth/github/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Start the GitHub OAuth login flow",
)
async def github_login() -> RedirectResponse:
    try:
        _require_auth_config()
    except HTTPException:
        return _frontend_error_redirect("github_oauth_unavailable")

    settings = get_settings()

    state = generate_oauth_state()
    response = RedirectResponse(
        url=create_github_login_url(state),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    set_signed_cookie(
        response,
        OAUTH_STATE_COOKIE_NAME,
        state,
        max_age=settings.auth_state_ttl_seconds,
    )
    return response


@router.get(
    "/api/auth/github/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Handle the GitHub OAuth callback",
)
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    try:
        _require_auth_config()
    except HTTPException:
        return _frontend_error_redirect("github_oauth_unavailable")

    settings = get_settings()

    redirect_target = settings.frontend_app_url

    if error:
        _log_auth_event(
            "github_callback",
            request=request,
            outcome="denied_by_user",
        )
        response = RedirectResponse(
            url=f"{redirect_target}?auth_error=github_oauth_denied",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
        delete_signed_cookie(response, OAUTH_STATE_COOKIE_NAME)
        return response

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    expected_state = unsign_cookie_value(expected_state)
    if not code or not state or not expected_state or state != expected_state:
        _log_auth_event(
            "github_callback",
            request=request,
            outcome="invalid_state",
        )
        response = RedirectResponse(
            url=f"{redirect_target}?auth_error=github_oauth_state_mismatch",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
        delete_signed_cookie(response, OAUTH_STATE_COOKIE_NAME)
        return response

    try:
        access_token = await exchange_code_for_token(code)
        user = await fetch_authenticated_user(access_token)
        session_id = auth_session_store.create(
            access_token=access_token,
            user=user,
        )
    except GitHubOAuthError as exc:
        logger.warning(
            "GitHub OAuth callback failed",
            extra={
                "auth_event": "github_callback",
                "path": request.url.path,
                "request_id": request.headers.get("x-request-id"),
                "outcome": "oauth_failed",
            },
        )
        response = RedirectResponse(
            url=f"{redirect_target}?auth_error=github_oauth_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
        delete_signed_cookie(response, OAUTH_STATE_COOKIE_NAME)
        return response

    response = RedirectResponse(
        url=f"{redirect_target}?auth=github_connected",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    set_signed_cookie(
        response,
        SESSION_COOKIE_NAME,
        session_id,
        max_age=settings.auth_session_ttl_seconds,
    )
    delete_signed_cookie(response, OAUTH_STATE_COOKIE_NAME)
    _log_auth_event(
        "github_callback",
        request=request,
        login=user.login,
        outcome="connected",
    )
    return response


@router.post(
    "/api/auth/logout",
    response_model=AuthSessionResponse,
    summary="Log out the current GitHub session",
)
async def logout(request: Request, response: Response) -> AuthSessionResponse:
    session = get_auth_session_from_request(request)
    if session:
        session_id = unsign_cookie_value(request.cookies.get(SESSION_COOKIE_NAME))
        if session_id:
            auth_session_store.delete(session_id)

    delete_signed_cookie(response, SESSION_COOKIE_NAME)
    _log_auth_event(
        "logout",
        request=request,
        login=session.user.login if session else None,
        outcome="signed_out",
    )
    return AuthSessionResponse(
        authenticated=False,
        status="signed_out",
        message="GitHub account disconnected.",
        user=None,
    )


@router.get(
    "/api/auth/me",
    response_model=AuthSessionResponse,
    summary="Get the current authenticated GitHub user",
)
async def get_current_user(request: Request, response: Response) -> AuthSessionResponse:
    session = get_auth_session_from_request(request)
    if not session:
        delete_signed_cookie(response, SESSION_COOKIE_NAME)
        return AuthSessionResponse(
            authenticated=False,
            status="signed_out",
            message="No GitHub account is currently connected.",
            user=None,
        )

    return AuthSessionResponse(
        authenticated=True,
        status="authenticated",
        message="GitHub account connected.",
        user=session.user,
    )
