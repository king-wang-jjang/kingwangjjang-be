import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.routes.boards import router as boards_router


class FakeRepository:
    def list_realtime(self, index: int, limit: int):
        assert index == 0
        assert limit == 30
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "category": "humor",
                "no": 1,
                "site": "dcinside",
                "title": "seed title",
                "url": "https://example.com/post/1",
                "contents": [],
                "gpt_answer": None,
                "created_at": "2026-04-28T00:00:00Z",
                "thumbnail": None,
                "comment_count": 2,
                "like_count": 0,
            }
        ]

    def list_daily(self, index: int, limit: int):
        return self.list_realtime(index, limit)

    def add_like(self, board_id: str, user_id: str):
        return {"board_id": board_id, "site": "dcinside", "like_count": 1}


def build_client(monkeypatch):
    from app.routes import boards

    monkeypatch.setattr(boards, "BoardRepository", lambda: FakeRepository())
    app = FastAPI()
    app.include_router(boards_router)
    return TestClient(app)


def test_realtime_returns_rest_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/realtime")

    assert response.status_code == 200
    assert response.json()[0]["_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()[0]["likeCount"] == 0
    assert response.json()[0]["create_time"] == "2026-04-28T00:00:00Z"


def test_daily_returns_rest_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily")

    assert response.status_code == 200
    assert response.json()[0]["site"] == "dcinside"
    assert response.json()[0]["comment_count"] == 2


def test_add_like_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/11111111-1111-1111-1111-111111111111/likes")

    assert response.status_code == 401


def test_add_like_returns_like_count(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/boards/11111111-1111-1111-1111-111111111111/likes",
        headers={
            "X-Auth-Status": "authenticated",
            "X-User-Id": "dev-user",
            "X-Auth-Provider": "local",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "boardId": "11111111-1111-1111-1111-111111111111",
        "site": "dcinside",
        "likeCount": 1,
    }
