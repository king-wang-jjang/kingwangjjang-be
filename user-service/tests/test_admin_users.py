import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.postgres import Base
from app.repositories import users as users_repository
from app.routes.admin_users import router


SECRET = "admin-users-test-secret-at-least-32-characters"
HEADERS = {
    "X-Auth-Status": "authenticated",
    "X-User-Id": "100",
    "X-Auth-Provider": "kakao",
    "X-User-Role": "admin",
}


def token(user_id="100", provider="kakao", **claims):
    return jwt.encode(
        {
            "user_id": user_id,
            "auth_provider": provider,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            **claims,
        },
        SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", " , 100, ")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(users_repository, "get_engine", lambda: engine)
    monkeypatch.setattr(users_repository, "get_session_factory", lambda: factory)
    with factory() as session:
        session.add_all([
            User(id="admin", user_id="100", auth_provider="kakao", nickname="운영자",
                 created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            User(id="member", user_id="200", auth_provider="kakao", nickname="원래 이름",
                 display_name="Reader_100%", refresh_token="never-return-this-secret",
                 created_at=datetime(2026, 2, 1, tzinfo=timezone.utc)),
            User(id="other", user_id="300", auth_provider="kakao", nickname="다른 회원",
                 created_at=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        ])
        session.commit()
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        client.headers.update(HEADERS)
        client.cookies.set("access_token", token())
        yield client, factory
    engine.dispose()


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/api/admin/users", None),
    ("GET", "/api/admin/users/member", None),
    ("PATCH", "/api/admin/users/member", {"displayName": "changed"}),
])
def test_all_admin_endpoints_reject_anonymous_and_regular_users(context, method, path, body):
    client, factory = context
    client.headers.clear()
    client.cookies.clear()
    assert client.request(method, path, json=body).status_code == 401
    client.headers.update({**HEADERS, "X-User-Id": "200", "X-User-Role": "user"})
    client.cookies.set("access_token", token("200"))
    assert client.request(method, path, json=body).status_code == 403
    with factory() as session:
        assert session.get(User, "member").display_name == "Reader_100%"


@pytest.mark.parametrize("access_token", [
    None, "invalid", token("200"), token(provider="other"),
    token(exp=datetime.now(timezone.utc) - timedelta(hours=1)),
    token(exp=None), token(type="refresh"),
])
def test_forged_admin_headers_cannot_bypass_token_verification(context, access_token):
    client, _ = context
    client.cookies.clear()
    if access_token:
        client.cookies.set("access_token", access_token)
    assert client.get("/api/admin/users").status_code == 403


def test_removed_admin_is_denied_even_with_old_trusted_headers(context, monkeypatch):
    client, _ = context
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    assert client.get("/api/admin/users").status_code == 403


def test_list_paginates_with_stable_order_and_never_exposes_secrets(context):
    client, _ = context
    first = client.get("/api/admin/users?page=1&pageSize=2").json()
    second = client.get("/api/admin/users?page=2&pageSize=2").json()
    assert first["total"] == 3
    assert first["pageSize"] == 2
    assert [user["Id"] for user in first["items"]] == ["other", "member"]
    assert [user["Id"] for user in second["items"]] == ["admin"]
    assert second["items"][0]["role"] == "admin"
    assert set(first["items"][0]) == {
        "Id", "userId", "nickname", "displayName", "authProvider",
        "profileImage", "createTime", "role",
    }
    assert "never-return-this-secret" not in str(first)
    assert client.get("/api/admin/users?page=9").json()["items"] == []


@pytest.mark.parametrize("query,ids", [
    ({"q": " reader_100% "}, ["member"]),
    ({"q": "%"}, ["member"]),
    ({"q": "원래"}, ["member"]),
    ({"q": "300"}, ["other"]),
    ({"q": "missing"}, []),
    ({"role": "admin"}, ["admin"]),
    ({"role": "user"}, ["other", "member"]),
    ({"q": "운영자", "role": "user"}, []),
])
def test_search_and_role_filters(context, query, ids):
    client, _ = context
    response = client.get("/api/admin/users", params=query)
    assert response.status_code == 200
    assert [user["Id"] for user in response.json()["items"]] == ids
    assert response.json()["total"] == len(ids)


@pytest.mark.parametrize("query", ["page=0", "pageSize=101", "pageSize=0", "role=owner", "q=" + "a" * 101])
def test_invalid_filters_are_rejected(context, query):
    client, _ = context
    assert client.get(f"/api/admin/users?{query}").status_code == 422


def test_detail_and_profile_edit_are_persisted_without_changing_identity(context):
    client, factory = context
    detail = client.get("/api/admin/users/member")
    assert detail.status_code == 200
    assert detail.json()["displayName"] == "Reader_100%"
    response = client.patch("/api/admin/users/member", json={"displayName": " 새 이름 "})
    assert response.status_code == 200
    assert response.json()["displayName"] == "새 이름"
    assert response.json()["nickname"] == "원래 이름"
    assert client.get("/api/admin/users?q=새 이름").json()["total"] == 1
    with factory() as session:
        member = session.get(User, "member")
        assert member.display_name == "새 이름"
        assert member.user_id == "200"
        assert member.refresh_token == "never-return-this-secret"
    assert client.patch("/api/admin/users/member", json={"displayName": "  "}).json()["displayName"] is None


@pytest.mark.parametrize("payload", [{}, {"displayName": "x" * 41}, {"displayName": 123}, {"displayName": "x", "role": "admin"}])
def test_invalid_edits_cannot_reset_name_or_change_role(context, payload):
    client, _ = context
    assert client.patch("/api/admin/users/member", json=payload).status_code == 422
    assert client.get("/api/admin/users/member").json()["displayName"] == "Reader_100%"


def test_unknown_member_returns_404_without_creating_an_account(context):
    client, factory = context
    assert client.get("/api/admin/users/missing").status_code == 404
    assert client.patch("/api/admin/users/missing", json={"displayName": "name"}).status_code == 404
    with factory() as session:
        assert len(session.scalars(select(User)).all()) == 3
