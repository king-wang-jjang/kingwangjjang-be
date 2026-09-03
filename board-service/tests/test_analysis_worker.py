from app.services.analysis_worker import (
    analysis_max_retry_count,
    analysis_worker_concurrency,
)


def test_analysis_worker_defaults_to_two_parallel_workers(monkeypatch):
    monkeypatch.delenv("ANALYSIS_WORKER_CONCURRENCY", raising=False)

    assert analysis_worker_concurrency() == 2


def test_analysis_worker_concurrency_is_bounded(monkeypatch):
    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "0")
    assert analysis_worker_concurrency() == 1

    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "999")
    assert analysis_worker_concurrency() == 16


def test_analysis_worker_concurrency_falls_back_for_invalid_values(monkeypatch):
    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "many")

    assert analysis_worker_concurrency() == 2


def test_analysis_retry_count_defaults_and_is_bounded(monkeypatch):
    monkeypatch.delenv("ANALYSIS_MAX_RETRY_COUNT", raising=False)
    assert analysis_max_retry_count() == 5

    monkeypatch.setenv("ANALYSIS_MAX_RETRY_COUNT", "0")
    assert analysis_max_retry_count() == 1

    monkeypatch.setenv("ANALYSIS_MAX_RETRY_COUNT", "999")
    assert analysis_max_retry_count() == 20

    monkeypatch.setenv("ANALYSIS_MAX_RETRY_COUNT", "many")
    assert analysis_max_retry_count() == 5
