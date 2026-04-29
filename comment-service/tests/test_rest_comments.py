import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.routes.comments import router as comments_router


COMMENT = {
    "id": "22222222-2222-2222-2222-222222222222",
    "board_id": "11111111-1111-1111-1111-111111111111",
    "parent_id": None,
    "content": "seed comment",
    "user_id": "dev-user",
    "user_nickname": "dev-user",
    "like_count": 0,
    "reply_count": 0,
    "is_liked": False,
    "is_deleted": False,
    "created_at": "2026-04-28T00:00:00Z",
    "updated_at": "2026-04-28T00:00:00Z",
}


class FakeRepository:
    def list_comments(self, board_id: str, page: int, limit: int, viewer_user_id: str | None = None):
        return {"board_id": board_id, "total_count": 1, "comments": [COMMENT]}

    def create_comment(self, board_id: str, parent_id: str | None, content: str, user_id: str):
        return {**COMMENT, "content": content, "user_id": user_id, "user_nickname": user_id}

    def update_comment(self, comment_id: str, content: str, user_id: str):
        return {**COMMENT, "id": comment_id, "content": content, "user_id": user_id}

    def delete_comment(self, comment_id: str, user_id: str):
        return True

    def toggle_like(self, comment_id: str, user_id: str):
        return {**COMMENT, "id": comment_id, "like_count": 1, "is_liked": True}


def build_client(monkeypatch):
    from app.routes import comments

    monkeypatch.setattr(comments, "CommentRepository", lambda: FakeRepository())
    app = FastAPI()
    app.include_router(comments_router)
    return TestClient(app)


def auth_headers():
    return {
        "X-Auth-Status": "authenticated",
        "X-User-Id": "dev-user",
        "X-Auth-Provider": "local",
    }


def test_list_comments_returns_frontend_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/api/comments?boardId=11111111-1111-1111-1111-111111111111&page=1&limit=20"
    )

    assert response.status_code == 200
    assert response.json()["boardId"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()["totalCount"] == 1
    assert response.json()["comments"][0]["Id"] == "22222222-2222-2222-2222-222222222222"
    assert response.json()["comments"][0]["createdAt"] == "2026-04-28T00:00:00Z"


def test_create_comment_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/comments",
        json={"boardId": "11111111-1111-1111-1111-111111111111", "content": "new"},
    )

    assert response.status_code == 401


def test_create_comment_returns_created_comment(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/comments",
        json={"boardId": "11111111-1111-1111-1111-111111111111", "content": "new"},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["content"] == "new"
    assert response.json()["userId"] == "dev-user"
    assert response.json()["isLiked"] is False


def test_update_delete_and_like_routes(monkeypatch):
    client = build_client(monkeypatch)

    update_response = client.patch(
        "/api/comments/22222222-2222-2222-2222-222222222222",
        json={"content": "edited"},
        headers=auth_headers(),
    )
    delete_response = client.delete(
        "/api/comments/22222222-2222-2222-2222-222222222222",
        headers=auth_headers(),
    )
    like_response = client.post(
        "/api/comments/22222222-2222-2222-2222-222222222222/like",
        headers=auth_headers(),
    )

    assert update_response.status_code == 200
    assert update_response.json()["content"] == "edited"
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
    assert like_response.status_code == 200
    assert like_response.json()["likeCount"] == 1
    assert like_response.json()["isLiked"] is True
