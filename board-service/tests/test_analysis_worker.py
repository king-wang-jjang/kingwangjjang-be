from app.services.analysis_worker import analysis_worker_concurrency


def test_analysis_worker_defaults_to_three_parallel_workers(monkeypatch):
    monkeypatch.delenv("ANALYSIS_WORKER_CONCURRENCY", raising=False)

    assert analysis_worker_concurrency() == 3


def test_analysis_worker_concurrency_is_bounded(monkeypatch):
    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "0")
    assert analysis_worker_concurrency() == 1

    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "999")
    assert analysis_worker_concurrency() == 16


def test_analysis_worker_concurrency_falls_back_for_invalid_values(monkeypatch):
    monkeypatch.setenv("ANALYSIS_WORKER_CONCURRENCY", "many")

    assert analysis_worker_concurrency() == 3
