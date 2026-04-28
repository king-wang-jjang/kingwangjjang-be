import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.routes.users import router as users_router


def build_client(principal: Principal | None = None):
    app = FastAPI()
    app.include_router(users_router)

    if principal is not None:
        app.dependency_overrides[get_optional_principal] = lambda: principal

    return TestClient(app)


def test_me_returns_null_for_anonymous_user():
    client = build_client(Principal(user_id=None, auth_provider=None, is_authenticated=False))

    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json() is None


def test_me_returns_authenticated_principal_user(monkeypatch):
    user_id = str(uuid4())

    class FakeRepository:
        def get_or_create_from_principal(self, principal):
            return {
                "id": user_id,
                "user_id": principal.user_id,
                "auth_provider": principal.auth_provider,
                "nickname": "dev-user",
                "profile_image": None,
                "created_at": "2026-04-28T00:00:00Z",
            }

    from app.routes import users

    monkeypatch.setattr(users, "UserRepository", lambda: FakeRepository())
    client = build_client(Principal(user_id="12345", auth_provider="kakao", is_authenticated=True))

    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json() == {
        "Id": user_id,
        "userId": "12345",
        "nickname": "dev-user",
        "authProvider": "kakao",
        "profileImage": None,
        "createTime": "2026-04-28T00:00:00Z",
    }
