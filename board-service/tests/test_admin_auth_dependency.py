from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import require_admin, require_principal
from app.auth.principal import Principal


JWT_SECRET = "test-admin-access-secret"
ADMIN_USER_ID = "admin-user"
ADMIN_HEADERS = {
    "X-Auth-Status": "authenticated",
    "X-User-Id": ADMIN_USER_ID,
    "X-Auth-Provider": "kakao",
    "X-User-Role": "admin",
}


def build_client() -> TestClient:
    app = FastAPI()

    @app.get("/principal")
    def principal_endpoint(principal: Principal = Depends(require_principal)):
        return {"userId": principal.user_id}

    @app.get("/admin")
    def admin_endpoint(principal: Principal = Depends(require_admin)):
        return {"userId": principal.user_id, "role": principal.role}

    return TestClient(app)


def access_token(user_id: str, *, secret: str = JWT_SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(
        {
            "user_id": user_id,
            "auth_provider": "kakao",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        secret,
        algorithm=algorithm,
    )


def configure_admin(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", f" , {ADMIN_USER_ID}, ")


def get_with_access_token(path: str, token: str, *, headers: dict[str, str]):
    client = build_client()
    client.cookies.set("access_token", token)
    return client.get(path, headers=headers)


def test_require_principal_keeps_existing_trusted_header_behavior():
    response = build_client().get("/principal", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"userId": ADMIN_USER_ID}


def test_require_admin_rejects_spoofed_headers_without_access_token(monkeypatch):
    configure_admin(monkeypatch)

    response = build_client().get("/admin", headers=ADMIN_HEADERS)

    assert response.status_code == 403


def test_require_admin_accepts_matching_allowlisted_hs256_access_token(monkeypatch):
    configure_admin(monkeypatch)

    response = get_with_access_token(
        "/admin",
        access_token(ADMIN_USER_ID),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"userId": ADMIN_USER_ID, "role": "admin"}


def test_require_admin_rejects_token_for_different_user(monkeypatch):
    configure_admin(monkeypatch)

    response = get_with_access_token(
        "/admin",
        access_token("different-user"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 403


def test_require_admin_rejects_user_outside_allowlist(monkeypatch):
    configure_admin(monkeypatch)
    headers = {**ADMIN_HEADERS, "X-User-Id": "not-allowlisted"}

    response = get_with_access_token(
        "/admin",
        access_token("not-allowlisted"),
        headers=headers,
    )

    assert response.status_code == 403


def test_require_admin_rejects_token_signed_with_wrong_secret(monkeypatch):
    configure_admin(monkeypatch)

    response = get_with_access_token(
        "/admin",
        access_token(ADMIN_USER_ID, secret="wrong-secret"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 403


def test_require_admin_rejects_non_hs256_access_token(monkeypatch):
    configure_admin(monkeypatch)

    response = get_with_access_token(
        "/admin",
        access_token(ADMIN_USER_ID, algorithm="HS384"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 403
