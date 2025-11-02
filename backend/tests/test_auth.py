from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.main import app
from app.schemas.auth import GitHubUserProfile
from app.services import auth_cookie
from app.services import auth_session_store as auth_session_store_module
from app.services.auth_session_store import auth_session_store


def _settings():
    return SimpleNamespace(
        session_secret="a" * 32,
        secure_cookies=False,
        auth_session_ttl_seconds=3600,
        auth_state_ttl_seconds=600,
        frontend_app_url="http://localhost:3000",
        github_client_id="github-client-id",
        github_client_secret="github-client-secret",
        github_oauth_redirect_uri="http://localhost:8000/api/auth/github/callback",
        validate_auth_settings=lambda: None,
    )


def test_auth_me_unauthenticated(monkeypatch):
    monkeypatch.setattr(auth_cookie, "get_settings", _settings)

    client = TestClient(app)
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": False,
        "status": "signed_out",
        "message": "No GitHub account is currently connected.",
        "user": None,
    }


def test_auth_me_authenticated_session(monkeypatch):
    monkeypatch.setattr(auth_cookie, "get_settings", _settings)
    monkeypatch.setattr(auth_routes, "get_settings", _settings)
    monkeypatch.setattr(auth_session_store_module, "get_settings", _settings)

    session_id = auth_session_store.create(
        access_token="secret-token",
        user=GitHubUserProfile(
            id=1,
            login="octocat",
            name="The Octocat",
            avatar_url="https://avatars.example/octocat.png",
        ),
    )

    client = TestClient(app)
    client.cookies.set(
        auth_cookie.SESSION_COOKIE_NAME,
        auth_cookie.sign_cookie_value(session_id),
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "status": "authenticated",
        "message": "GitHub account connected.",
        "user": {
            "id": 1,
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://avatars.example/octocat.png",
        },
    }
    assert "access_token" not in response.text


def test_logout_clears_session(monkeypatch):
    monkeypatch.setattr(auth_cookie, "get_settings", _settings)
    monkeypatch.setattr(auth_routes, "get_settings", _settings)
    monkeypatch.setattr(auth_session_store_module, "get_settings", _settings)

    session_id = auth_session_store.create(
        access_token="secret-token",
        user=GitHubUserProfile(id=2, login="hubot"),
    )

    client = TestClient(app)
    client.cookies.set(
        auth_cookie.SESSION_COOKIE_NAME,
        auth_cookie.sign_cookie_value(session_id),
    )

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": False,
        "status": "signed_out",
        "message": "GitHub account disconnected.",
        "user": None,
    }
    assert auth_session_store.get(session_id) is None


def test_invalid_callback_state_redirects_safely(monkeypatch):
    monkeypatch.setattr(auth_cookie, "get_settings", _settings)
    monkeypatch.setattr(auth_routes, "get_settings", _settings)

    client = TestClient(app)
    client.cookies.set(
        auth_cookie.OAUTH_STATE_COOKIE_NAME,
        auth_cookie.sign_cookie_value("expected-state"),
    )

    response = client.get(
        "/api/auth/github/callback?code=test-code&state=wrong-state",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "http://localhost:3000?auth_error=github_oauth_state_mismatch"
    )


def test_expired_session_is_rejected(monkeypatch):
    settings = _settings()
    settings.auth_session_ttl_seconds = -1
    monkeypatch.setattr(auth_cookie, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_session_store_module, "get_settings", lambda: settings)

    session_id = auth_session_store.create(
        access_token="secret-token",
        user=GitHubUserProfile(id=3, login="expired-user"),
    )

    client = TestClient(app)
    client.cookies.set(
        auth_cookie.SESSION_COOKIE_NAME,
        auth_cookie.sign_cookie_value(session_id),
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
