from __future__ import annotations

import hashlib
import hmac
from base64 import urlsafe_b64decode, urlsafe_b64encode

from fastapi import Request, Response

from app.core.config import get_settings
from app.services.auth_session_store import AuthSession, auth_session_store

SESSION_COOKIE_NAME = "repo_aware_session"
OAUTH_STATE_COOKIE_NAME = "repo_aware_oauth_state"


def set_signed_cookie(response: Response, name: str, value: str, *, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=name,
        value=sign_cookie_value(value),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def delete_signed_cookie(response: Response, name: str) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=name,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def sign_cookie_value(value: str) -> str:
    settings = get_settings()
    secret = (settings.session_secret or "").encode("utf-8")
    payload = urlsafe_b64encode(value.encode("utf-8")).decode("utf-8")
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def unsign_cookie_value(value: str | None) -> str | None:
    if not value or "." not in value:
        return None

    settings = get_settings()
    payload, provided_signature = value.rsplit(".", 1)
    expected_signature = hmac.new(
        (settings.session_secret or "").encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        return urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def get_auth_session_from_request(request: Request) -> AuthSession | None:
    session_id = unsign_cookie_value(request.cookies.get(SESSION_COOKIE_NAME))
    if not session_id:
        return None
    return auth_session_store.get(session_id)
