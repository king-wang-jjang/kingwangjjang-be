import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.routes.boards import router as boards_router


AUTH_HEADERS = {
    "X-Auth-Status": "authenticated",
    "X-User-Id": "dev-user",
    "X-Auth-Provider": "local",
}


class FakeRepository:
    last_filters = None

    def list_realtime(self, index: int, limit: int, filters=None):
        assert index == 0
        assert limit == 30
        type(self).last_filters = filters
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
                "tags": ["funny", "issue"],
                "analysis_status": "pending",
                "analysis_retry_count": 0,
                "analysis_error": None,
                "created_at": "2026-04-28T00:00:00Z",
                "thumbnail": None,
                "comment_count": 2,
                "like_count": 0,
            }
        ]

    def list_daily(self, index: int, limit: int, filters=None):
        return self.list_realtime(index, limit, filters=filters)

    def add_like(self, board_id: str, user_id: str):
        return {"board_id": board_id, "site": "dcinside", "like_count": 1}

    def get_analysis_status(self, board_id: str):
        if board_id == "missing":
            return None
        if board_id == "existing":
            return {
                "board_id": board_id,
                "summary": "stored summary",
                "tags": ["stored"],
                "is_complete": True,
            }
        return {
            "board_id": board_id,
            "summary": None,
            "tags": [],
            "is_complete": False,
        }

    def analyze_board(self, board_id: str):
        if board_id == "missing":
            return None

        return {
            "board_id": board_id,
            "summary": "generated summary",
            "tags": ["funny", "issue"],
        }

    def get_analysis(self, board_id: str):
        if board_id == "missing":
            return None

        return {
            "board_id": board_id,
            "status": "done",
            "summary": "generated summary",
            "tags": ["funny", "issue"],
            "retry_count": 0,
            "error": None,
            "requested_at": "2026-04-28T00:01:00Z",
            "started_at": "2026-04-28T00:01:01Z",
            "updated_at": "2026-04-28T00:01:10Z",
        }


def build_client(monkeypatch):
    from app.routes import boards

    boards.analysis_jobs.clear()
    FakeRepository.last_filters = None
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
    assert response.json()[0]["tags"] == ["funny", "issue"]
    assert response.json()[0]["analysis_status"] == "pending"


def test_daily_returns_rest_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily")

    assert response.status_code == 200
    assert response.json()[0]["site"] == "dcinside"
    assert response.json()[0]["comment_count"] == 2


def test_realtime_accepts_board_filters(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/api/boards/realtime"
        "?sites=dcinside&sites=ygosu&category=humor&tag=funny&q=seed&has_thumbnail=true"
    )

    assert response.status_code == 200
    assert FakeRepository.last_filters is not None
    assert FakeRepository.last_filters.sites == ("dcinside", "ygosu")
    assert FakeRepository.last_filters.category == "humor"
    assert FakeRepository.last_filters.tag == "funny"
    assert FakeRepository.last_filters.query == "seed"
    assert FakeRepository.last_filters.has_thumbnail is True


def test_add_like_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/11111111-1111-1111-1111-111111111111/likes")

    assert response.status_code == 401


def test_add_like_returns_like_count(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/boards/11111111-1111-1111-1111-111111111111/likes",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "boardId": "11111111-1111-1111-1111-111111111111",
        "site": "dcinside",
        "likeCount": 1,
    }


def test_get_analysis_returns_summary_and_tags(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/11111111-1111-1111-1111-111111111111/ai")

    assert response.status_code == 200
    assert response.json() == {
        "boardId": "11111111-1111-1111-1111-111111111111",
        "status": "done",
        "summary": "generated summary",
        "tags": ["funny", "issue"],
        "retryCount": 0,
        "error": None,
        "requestedAt": "2026-04-28T00:01:00Z",
        "startedAt": "2026-04-28T00:01:01Z",
        "updatedAt": "2026-04-28T00:01:10Z",
    }


def test_analyze_board_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/11111111-1111-1111-1111-111111111111/ai")

    assert response.status_code == 401


def test_analyze_board_starts_authenticated_job_and_exposes_status(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/boards/11111111-1111-1111-1111-111111111111/ai",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 202
    started_job = response.json()
    assert started_job["boardId"] == "11111111-1111-1111-1111-111111111111"
    assert started_job["status"] == "queued"
    assert started_job["progressPercent"] < 100
    assert started_job["estimatedSecondsRemaining"] is not None

    status_response = client.get(
        f"/api/boards/ai/jobs/{started_job['jobId']}",
        headers=AUTH_HEADERS,
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["progressPercent"] == 100
    assert status_response.json()["estimatedSecondsRemaining"] == 0
    assert status_response.json()["summary"] == "generated summary"
    assert status_response.json()["tags"] == ["funny", "issue"]


def test_analyze_board_returns_stored_summary_without_starting_job(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/existing/ai", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["progressPercent"] == 100
    assert response.json()["estimatedSecondsRemaining"] == 0
    assert response.json()["summary"] == "stored summary"
    assert response.json()["tags"] == ["stored"]


def test_analysis_job_status_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    start_response = client.post(
        "/api/boards/11111111-1111-1111-1111-111111111111/ai",
        headers=AUTH_HEADERS,
    )

    response = client.get(f"/api/boards/ai/jobs/{start_response.json()['jobId']}")

    assert response.status_code == 401


def test_analyze_board_returns_404_for_unknown_board(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/missing/ai", headers=AUTH_HEADERS)

    assert response.status_code == 404
