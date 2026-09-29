import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres  # noqa: E402
from app.db.models import Board  # noqa: E402
from app.repositories.boards import BoardRepository  # noqa: E402
from app.routes.boards import router  # noqa: E402


def _board(board_id: str, status: str, created_at: datetime, **values) -> Board:
    return Board(
        id=board_id,
        category="community",
        no=1,
        site="test",
        title=board_id,
        url=f"https://example.com/{board_id}",
        contents="body with enough detail",
        analysis_status=status,
        created_at=created_at,
        **values,
    )


def test_analysis_queue_metrics_exposes_backlog_age_and_recent_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    repository = BoardRepository()

    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                _board("ready", "pending", now - timedelta(minutes=20)),
                _board(
                    "deferred",
                    "pending",
                    now - timedelta(minutes=10),
                    analysis_requested_at=now + timedelta(minutes=5),
                ),
                _board(
                    "processing",
                    "processing",
                    now - timedelta(minutes=40),
                    analysis_started_at=now - timedelta(minutes=15),
                ),
                _board(
                    "done",
                    "done",
                    now - timedelta(hours=2),
                    analysis_updated_at=now - timedelta(minutes=30),
                    gpt_answer="summary",
                    tags=["done"],
                ),
                _board(
                    "failed",
                    "failed",
                    now - timedelta(hours=3),
                    analysis_updated_at=now - timedelta(hours=2),
                ),
            ]
        )
        session.commit()

    metrics = repository.get_analysis_queue_metrics(as_of=now)

    assert metrics == {
        "generated_at": now,
        "total_count": 5,
        "pending_count": 2,
        "ready_pending_count": 1,
        "deferred_pending_count": 1,
        "processing_count": 1,
        "done_count": 1,
        "failed_count": 1,
        "stale_processing_count": 1,
        "oldest_pending_at": now - timedelta(minutes=20),
        "oldest_pending_age_seconds": 1200,
        "recent_arrivals": 3,
        "recent_completions": 1,
    }


@pytest.fixture
def repository(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'workflow.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    repo = BoardRepository()
    now = datetime.now(timezone.utc)
    with postgres.get_session_factory()() as session:
        session.add_all([
            _board("failed-1", "failed", now, analysis_retry_count=5, analysis_error="LLM timeout"),
            _board("failed-2", "failed", now - timedelta(minutes=1), analysis_retry_count=5, analysis_error="Invalid output"),
            _board("processing", "processing", now, analysis_started_at=now, analysis_retry_count=2),
            _board("done", "done", now, gpt_answer="saved summary", tags=["saved"], llm_engagement_score=50),
        ])
        session.commit()
    yield repo
    postgres.get_engine().dispose()
    postgres.get_session_factory.cache_clear()
    postgres.get_engine.cache_clear()


def test_runs_filter_paginate_and_exclude_board_bodies(repository):
    first = repository.list_analysis_runs(status="failed", limit=1)
    second = repository.list_analysis_runs(status="failed", limit=1, offset=1)
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["board_id"] == "failed-1"
    assert second["items"][0]["board_id"] == "failed-2"
    assert first["items"][0]["error"] == "LLM timeout"
    assert first["items"][0]["created_at"].endswith("Z")
    assert "contents" not in first["items"][0]
    assert repository.list_analysis_runs(query="failed-2")["total"] == 1
    assert repository.list_analysis_runs(query="test")["total"] == 4
    assert repository.list_analysis_runs(query="%_")["total"] == 0


def test_retry_requeues_once_and_preserves_active_work(repository):
    assert repository.retry_failed_analysis("failed-1") == {"board_id": "failed-1", "status": "pending"}
    result = repository.get_analysis("failed-1")
    assert result["retry_count"] == 0
    assert result["error"] is None
    assert result["started_at"] is None
    assert result["requested_at"] is not None
    with pytest.raises(ValueError):
        repository.retry_failed_analysis("failed-1")
    assert repository._claim_next_analysis_job(max_retry_count=5) == "failed-1"
    with pytest.raises(ValueError):
        repository.retry_failed_analysis("failed-1")
    assert repository.get_analysis("failed-1")["status"] == "processing"
    with pytest.raises(ValueError):
        repository.retry_failed_analysis("processing")
    assert repository.get_analysis("processing")["retry_count"] == 2
    with pytest.raises(ValueError):
        repository.retry_failed_analysis("done")
    assert repository.get_analysis("done")["summary"] == "saved summary"
    assert repository.retry_failed_analysis("missing") is None


def test_retried_run_is_processed_by_worker_and_persists_success(repository):
    class Analyzer:
        def analyze(self, text):
            return {"summary": "recovered summary", "tags": ["recovered"], "llm_engagement_score": 50}

    # Use enough source text to pass the normal content validation.
    with postgres.get_session_factory()() as session:
        session.get(Board, "failed-1").contents = "A complete article with useful information and context. " * 20
        session.commit()
    repository.retry_failed_analysis("failed-1")
    result = repository.process_next_analysis_job(analyzer=Analyzer())
    assert result["board_id"] == "failed-1"
    assert result["status"] == "done"
    saved = repository.get_analysis("failed-1")
    assert saved["summary"] == "recovered summary"
    assert saved["error"] is None
    assert repository.get_analysis_queue_metrics()["failed_count"] == 1


@pytest.fixture
def client(repository, monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "admin")
    monkeypatch.setenv("JWT_SECRET_KEY", "workflow-test-secret-with-32-characters")
    monkeypatch.setenv("DISABLE_ANALYSIS_WORKER", "FALSE")
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client


def authorize(client):
    client.cookies.set("access_token", jwt.encode(
        {"user_id": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "workflow-test-secret-with-32-characters", algorithm="HS256",
    ))
    client.headers.update({"X-Auth-Status": "authenticated", "X-User-Id": "admin", "X-User-Role": "admin"})


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/boards/ai/resources/runs"),
    ("POST", "/api/boards/ai/resources/runs/failed-1/retry"),
])
def test_workflow_routes_require_verified_admin(client, method, path):
    assert client.request(method, path).status_code == 401
    client.headers.update({"X-Auth-Status": "authenticated", "X-User-Id": "admin", "X-User-Role": "admin"})
    assert client.request(method, path).status_code == 403


def test_workflow_routes_return_status_and_reject_duplicate_retry(client):
    authorize(client)
    result = client.get("/api/boards/ai/resources/runs?status=failed&limit=1")
    assert result.status_code == 200
    assert result.headers["cache-control"] == "private, no-store"
    assert result.json()["total"] == 2
    assert result.json()["items"][0]["status"] == "failed"
    retry = client.post("/api/boards/ai/resources/runs/failed-1/retry")
    assert retry.status_code == 202
    assert retry.json()["status"] == "pending"
    assert client.post("/api/boards/ai/resources/runs/failed-1/retry").status_code == 409
    assert client.post("/api/boards/ai/resources/runs/missing/retry").status_code == 404
    assert client.get("/api/boards/ai/resources/runs?status=failed").json()["total"] == 1


def test_retry_rejects_disabled_worker_without_changing_state(client, repository, monkeypatch):
    authorize(client)
    monkeypatch.setenv("DISABLE_ANALYSIS_WORKER", "TRUE")
    assert client.post("/api/boards/ai/resources/runs/failed-1/retry").status_code == 503
    assert repository.get_analysis("failed-1")["status"] == "failed"


@pytest.mark.parametrize("query", ["status=unknown", "offset=-1", "limit=101", "q=" + "a" * 201])
def test_workflow_route_validates_filters(client, query):
    authorize(client)
    assert client.get(f"/api/boards/ai/resources/runs?{query}").status_code == 422
