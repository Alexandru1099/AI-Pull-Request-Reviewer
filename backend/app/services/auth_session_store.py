from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock

from app.core.config import get_settings
from app.schemas.auth import GitHubUserProfile


@dataclass
class AuthSession:
    access_token: str
    user: GitHubUserProfile
    created_at: float
    expires_at: float


class AuthSessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, AuthSession] = {}

    def create(self, *, access_token: str, user: GitHubUserProfile) -> str:
        session_id = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[session_id] = AuthSession(
                access_token=access_token,
                user=user,
                created_at=time.time(),
                expires_at=time.time() + get_settings().auth_session_ttl_seconds,
            )
        return session_id

    def get(self, session_id: str) -> AuthSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.expires_at <= time.time():
                self._sessions.pop(session_id, None)
                return None
            return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


auth_session_store = AuthSessionStore()
