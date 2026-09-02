import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jwt
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
ADMIN_HEADERS = {**AUTH_HEADERS, "X-User-Role": "admin"}
ADMIN_JWT_SECRET = "test-admin-access-secret"


def admin_access_token() -> str:
    return jwt.encode(
        {
            "user_id": "dev-user",
            "auth_provider": "local",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        ADMIN_JWT_SECRET,
        algorithm="HS256",
    )


def authorize_admin(client: TestClient) -> None:
    client.cookies.set("access_token", admin_access_token())


class FakeRepository:
    last_filters = None
    last_issue_args = None
    last_history_date = None
    last_history_limit = None
    last_history_dates_limit = None
    last_daily_args = None
    recently_crawled_sites = (
        "inven",
        "theqoo",
        "dcinside",
        "arca",
        "ppomppu",
        "fmkorea",
        "ygosu",
        "new-community",
    )
    return_empty_shorts = False

    def get_analysis_queue_metrics(self):
        return {
            "generated_at": "2026-09-01T01:00:00Z",
            "total_count": 30,
            "pending_count": 12,
            "ready_pending_count": 10,
            "deferred_pending_count": 2,
            "processing_count": 2,
            "done_count": 15,
            "failed_count": 1,
            "stale_processing_count": 0,
            "oldest_pending_at": "2026-09-01T00:45:00Z",
            "oldest_pending_age_seconds": 900,
            "recent_arrivals": 18,
            "recent_completions": 12,
        }

    def list_recently_crawled_sites(self):
        return list(type(self).recently_crawled_sites)

    def get_issue_overview(self, *, window_hours=24, limit=16, sites=()):
        type(self).last_issue_args = (window_hours, limit, sites)
        return {
            "generated_at": "2026-08-31T00:00:00Z",
            "window_hours": window_hours,
            "total_posts": 12,
            "total_categories": 2,
            "categories": [
                {
                    "category": "humor",
                    "post_count": 8,
                    "current_posts": 6,
                    "previous_posts": 2,
                    "impact_score": 42.5,
                    "share": 0.75,
                    "momentum_percent": 133.3,
                    "top_sites": [{"site": "dcinside", "post_count": 5}],
                    "top_tags": ["이슈", "유머"],
                }
            ],
        }

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
                "llm_engagement_score": 76,
                "llm_engagement_reason": "호기심과 토론 가능성이 높음",
                "analysis_status": "pending",
                "analysis_retry_count": 0,
                "analysis_error": None,
                "created_at": "2026-04-28T00:00:00Z",
                "thumbnail": None,
                "comment_count": 2,
                "like_count": 0,
                "native_comment_count": 12,
                "native_like_count": 7,
                "native_view_count": 100,
                "source_rank": 3,
                "hot_score": 9.5,
                "daily_score": 12.25,
                "metrics_crawled_at": "2026-04-28T00:02:00Z",
                "score_updated_at": "2026-04-28T00:02:00Z",
            }
        ]

    def list_daily(self, index: int, limit: int, filters=None):
        type(self).last_daily_args = (index, limit)
        if type(self).return_empty_shorts and limit == 10:
            return []
        return self.list_realtime(0, 30, filters=filters)[:limit]

    def list_daily_history_dates(self, limit: int = 30):
        type(self).last_history_dates_limit = limit
        return [date(2026, 7, 19), date(2026, 7, 18)]

    def list_daily_history(self, snapshot_date: date, limit: int = 10):
        type(self).last_history_date = snapshot_date
        type(self).last_history_limit = limit
        boards = self.list_realtime(0, 30)
        boards[0]["daily_score"] = 88.75
        return boards

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
                "llm_engagement_score": 64,
                "llm_engagement_reason": "관심을 끌 요소가 있음",
                "is_complete": True,
            }
        return {
            "board_id": board_id,
            "summary": None,
            "tags": [],
            "llm_engagement_score": None,
            "llm_engagement_reason": None,
            "is_complete": False,
        }

    def analyze_board(self, board_id: str):
        if board_id == "missing":
            return None

        return {
            "board_id": board_id,
            "summary": "generated summary",
            "tags": ["funny", "issue"],
            "llm_engagement_score": 76,
            "llm_engagement_reason": "호기심과 토론 가능성이 높음",
        }

    def get_analysis(self, board_id: str):
        if board_id == "missing":
            return None

        return {
            "board_id": board_id,
            "status": "done",
            "summary": "generated summary",
            "tags": ["funny", "issue"],
            "llm_engagement_score": 76,
            "llm_engagement_reason": "호기심과 토론 가능성이 높음",
            "retry_count": 0,
            "error": None,
            "requested_at": "2026-04-28T00:01:00Z",
            "started_at": "2026-04-28T00:01:01Z",
            "updated_at": "2026-04-28T00:01:10Z",
        }

    def extract_image_text(self, board_id: str, *, image_index: int = 0, prompt=None):
        if board_id == "missing":
            return None
        if board_id == "no-image":
            raise ValueError("Image not found")

        return {
            "board_id": board_id,
            "image_index": image_index,
            "media_path": f"media/image-{image_index}.webp",
            "text": prompt or "vision text",
        }


def build_client(monkeypatch):
    from app.routes import boards

    boards.analysis_jobs.clear()
    FakeRepository.last_filters = None
    FakeRepository.last_issue_args = None
    FakeRepository.last_history_date = None
    FakeRepository.last_history_limit = None
    FakeRepository.last_history_dates_limit = None
    FakeRepository.last_daily_args = None
    FakeRepository.recently_crawled_sites = (
        "inven",
        "theqoo",
        "dcinside",
        "arca",
        "ppomppu",
        "fmkorea",
        "ygosu",
        "new-community",
    )
    FakeRepository.return_empty_shorts = False
    monkeypatch.setenv("JWT_SECRET_KEY", ADMIN_JWT_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "dev-user")
    monkeypatch.setattr(boards, "BoardRepository", lambda: FakeRepository())
    app = FastAPI()
    app.include_router(boards_router)
    return TestClient(app)


def test_realtime_returns_rest_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/realtime")

    assert response.status_code == 200
    assert response.json()[0]["_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()[0]["site_label"] == "디시인사이드"
    assert response.json()[0]["likeCount"] == 0
    assert response.json()[0]["create_time"] == "2026-04-28T00:00:00Z"
    assert response.json()[0]["tags"] == ["funny", "issue"]
    assert response.json()[0]["analysis_status"] == "pending"
    assert response.json()[0]["llm_engagement_score"] == 76
    assert response.json()[0]["llm_engagement_reason"] == "호기심과 토론 가능성이 높음"
    assert response.json()[0]["native_comment_count"] == 12
    assert response.json()[0]["native_like_count"] == 7
    assert response.json()[0]["source_rank"] == 3
    assert response.json()[0]["hot_score"] == 9.5
    assert response.json()[0]["daily_score"] == 12.25


def test_filters_returns_sites_with_recent_successful_crawls(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/filters")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "sites": [
            {"value": "dcinside", "label": "디시인사이드"},
            {"value": "ygosu", "label": "와이고수"},
            {"value": "ppomppu", "label": "뽐뿌"},
            {"value": "theqoo", "label": "더쿠"},
            {"value": "fmkorea", "label": "에펨코리아"},
            {"value": "arca", "label": "아카라이브"},
            {"value": "inven", "label": "인벤"},
            {"value": "new-community", "label": "new-community"},
        ]
    }


def test_filters_returns_no_static_fallback_when_no_site_crawled_recently(monkeypatch):
    client = build_client(monkeypatch)
    FakeRepository.recently_crawled_sites = ()

    response = client.get("/api/boards/filters")

    assert response.status_code == 200
    assert response.json() == {"sites": []}


def test_issue_overview_returns_visualization_data_and_applies_site_scope(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/api/boards/issues?hours=48&limit=12&sites=dcinside&sites=ppomppu"
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == (
        "public, max-age=60, stale-while-revalidate=120"
    )
    assert FakeRepository.last_issue_args == (
        48,
        12,
        ("dcinside", "ppomppu"),
    )
    assert response.json()["categories"][0] == {
        "category": "humor",
        "post_count": 8,
        "current_posts": 6,
        "previous_posts": 2,
        "impact_score": 42.5,
        "share": 0.75,
        "momentum_percent": 133.3,
        "top_sites": [
            {
                "site": "dcinside",
                "site_label": "디시인사이드",
                "post_count": 5,
            }
        ],
        "top_tags": ["이슈", "유머"],
    }


def test_issue_overview_validates_window_and_category_limit(monkeypatch):
    client = build_client(monkeypatch)

    assert client.get("/api/boards/issues?hours=5").status_code == 422
    assert client.get("/api/boards/issues?hours=169").status_code == 422
    assert client.get("/api/boards/issues?limit=3").status_code == 422
    assert client.get("/api/boards/issues?limit=25").status_code == 422


def test_daily_returns_rest_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily")

    assert response.status_code == 200
    assert response.json()[0]["site"] == "dcinside"
    assert response.json()[0]["comment_count"] == 2


def test_daily_history_dates_returns_available_dates(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily/history/dates?limit=2")

    assert response.status_code == 200
    assert response.json() == ["2026-07-19", "2026-07-18"]
    assert FakeRepository.last_history_dates_limit == 2


def test_daily_history_returns_existing_rest_shape_with_snapshot_score(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily/history?date=2026-07-19&limit=5")

    assert response.status_code == 200
    assert response.json()[0]["_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()[0]["likeCount"] == 0
    assert response.json()[0]["daily_score"] == 88.75
    assert FakeRepository.last_history_date == date(2026, 7, 19)
    assert FakeRepository.last_history_limit == 5


def test_daily_history_validates_date_and_limit(monkeypatch):
    client = build_client(monkeypatch)

    missing_date = client.get("/api/boards/daily/history")
    invalid_date = client.get("/api/boards/daily/history?date=2026-13-40")
    oversized_limit = client.get("/api/boards/daily/history?date=2026-07-19&limit=101")

    assert missing_date.status_code == 422
    assert invalid_date.status_code == 422
    assert oversized_limit.status_code == 422


def test_daily_shorts_package_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily/shorts-package")

    assert response.status_code == 401


def test_daily_shorts_package_rejects_non_admin_user(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/daily/shorts-package", headers=AUTH_HEADERS)

    assert response.status_code == 403


def test_daily_shorts_package_returns_admin_countdown_payload(monkeypatch):
    client = build_client(monkeypatch)
    authorize_admin(client)

    response = client.get("/api/boards/daily/shorts-package", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert FakeRepository.last_daily_args == (0, 10)
    assert response.json()["production"]["platform"] == "youtube_shorts"
    assert response.json()["production"]["aspectRatio"] == "9:16"
    assert response.json()["rankingMode"] == "live"
    assert response.json()["sources"][0]["url"] == "https://example.com/post/1"
    assert response.json()["scenes"][0]["type"] == "intro"


def test_daily_shorts_package_supports_saved_ranking_date(monkeypatch):
    client = build_client(monkeypatch)
    authorize_admin(client)

    response = client.get(
        "/api/boards/daily/shorts-package?date=2026-07-19",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["rankingDate"] == "2026-07-19"
    assert response.json()["rankingMode"] == "historical_ranking_current_content"
    assert response.json()["video"]["hook"].startswith("7월 19일")
    assert FakeRepository.last_history_date == date(2026, 7, 19)
    assert FakeRepository.last_history_limit == 10


def test_daily_shorts_package_returns_404_when_ranking_is_empty(monkeypatch):
    client = build_client(monkeypatch)
    authorize_admin(client)
    FakeRepository.return_empty_shorts = True

    response = client.get("/api/boards/daily/shorts-package", headers=ADMIN_HEADERS)

    assert response.status_code == 404


def test_analysis_queue_resources_requires_admin(monkeypatch):
    client = build_client(monkeypatch)

    assert client.get("/api/boards/ai/resources").status_code == 401
    assert (
        client.get("/api/boards/ai/resources", headers=AUTH_HEADERS).status_code
        == 403
    )


def test_analysis_queue_resources_reports_backlog_pressure(monkeypatch):
    monkeypatch.setenv("DISABLE_ANALYSIS_WORKER", "FALSE")
    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "2")
    client = build_client(monkeypatch)
    authorize_admin(client)

    response = client.get("/api/boards/ai/resources", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == {
        "generated_at": "2026-09-01T01:00:00Z",
        "status": "overloaded",
        "is_overloaded": True,
        "worker_enabled": True,
        "worker_concurrency": 2,
        "total_count": 30,
        "pending_count": 12,
        "ready_pending_count": 10,
        "deferred_pending_count": 2,
        "processing_count": 2,
        "done_count": 15,
        "failed_count": 1,
        "stale_processing_count": 0,
        "oldest_pending_at": "2026-09-01T00:45:00Z",
        "oldest_pending_age_seconds": 900,
        "recent_arrivals": 18,
        "recent_completions": 12,
        "estimated_clear_seconds": 3600,
    }


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
        "llmEngagementScore": 76,
        "llmEngagementReason": "호기심과 토론 가능성이 높음",
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
    assert status_response.json()["llmEngagementScore"] == 76
    assert status_response.json()["llmEngagementReason"] == "호기심과 토론 가능성이 높음"


def test_analyze_board_returns_stored_summary_without_starting_job(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/existing/ai", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["progressPercent"] == 100
    assert response.json()["estimatedSecondsRemaining"] == 0
    assert response.json()["summary"] == "stored summary"
    assert response.json()["tags"] == ["stored"]
    assert response.json()["llmEngagementScore"] == 64
    assert response.json()["llmEngagementReason"] == "관심을 끌 요소가 있음"


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


def test_extract_image_text_requires_authentication(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/boards/board-1/images/0/vision-text")

    assert response.status_code == 401


def test_extract_image_text_returns_vllm_text(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/boards/board-1/images/2/vision-text",
        json={"prompt": "read exactly"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "boardId": "board-1",
        "imageIndex": 2,
        "mediaPath": "media/image-2.webp",
        "text": "read exactly",
    }


def test_extract_image_text_returns_404_for_missing_image(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/boards/no-image/images/0/vision-text",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
