import pytest

from app.db.bootstrap import bootstrap_legacy_nodes
from conftest import create_test_node


def test_repository_crud_and_model_capability_rows(repository):
    node = create_test_node(repository, capabilities=["analysis", "chat"])

    loaded = repository.get_node(node.id)
    assert loaded is not None
    assert {(item.model_name, item.capability) for item in loaded.models} == {
        ("model-a", "analysis"),
        ("model-a", "chat"),
    }

    updated = repository.update_node(
        node.id,
        {"name": "renamed", "weight": 3},
        [
            {
                "name": "vision-model",
                "capabilities": ["vision"],
                "enabled": True,
                "is_default": True,
            }
        ],
    )
    assert updated is not None
    assert updated.name == "renamed"
    assert updated.weight == 3
    assert [(item.model_name, item.capability) for item in updated.models] == [
        ("vision-model", "vision")
    ]
    assert repository.list_candidates("analysis") == []
    assert repository.list_candidates("vision")[0].model == "vision-model"

    assert repository.delete_node(node.id) is True
    assert repository.delete_node(node.id) is False
    assert repository.count_nodes() == 0


def test_repository_rejects_duplicate_name_and_invalid_capability(repository):
    create_test_node(repository)
    with pytest.raises(ValueError, match="already exists"):
        create_test_node(
            repository,
            name="node-a",
            base_url="http://different.local:11434",
        )

    with pytest.raises(ValueError, match="Unsupported capability"):
        repository.create_node(
            {
                "name": "bad",
                "provider": "ollama",
                "base_url": "http://bad.local",
            },
            [{"name": "m", "capabilities": ["audio"]}],
        )


def test_bootstrap_imports_legacy_nodes_once_and_never_stores_api_key(repository, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URLS", "http://ollama-a:11434/, http://ollama-b:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "legacy-chat")
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm:8000/v1")
    monkeypatch.setenv("VLLM_MODEL", "legacy-vision")
    monkeypatch.setenv("VLLM_API_KEY", "super-secret-value")

    assert bootstrap_legacy_nodes(repository) == 3
    nodes = repository.list_nodes()
    assert [node.name for node in nodes] == [
        "legacy-ollama-1",
        "legacy-ollama-2",
        "legacy-vllm",
    ]
    vllm = next(node for node in nodes if node.name == "legacy-vllm")
    assert vllm.api_key_env == "VLLM_API_KEY"
    assert "super-secret-value" not in repr(vars(vllm))

    monkeypatch.setenv("OLLAMA_BASE_URLS", "http://new-server:11434")
    assert bootstrap_legacy_nodes(repository) == 0
    assert repository.count_nodes() == 3


def test_bootstrap_uses_historical_ollama_defaults_for_missing_or_blank_env(
    repository, monkeypatch
):
    for name in ("OLLAMA_BASE_URLS", "OLLAMA_BASE_URL", "VLLM_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "")

    assert bootstrap_legacy_nodes(repository) == 1
    node = repository.list_nodes()[0]
    assert node.base_url == "http://100.104.51.52:11434"
    assert {(model.model_name, model.capability) for model in node.models} == {
        ("gemma4:e4b", "analysis"),
        ("gemma4:e4b", "chat"),
    }


def test_bootstrap_registers_summary_vllm_without_legacy_ollama(repository, monkeypatch):
    monkeypatch.setenv("AI_BOOTSTRAP_OLLAMA_ENABLED", "FALSE")
    monkeypatch.setenv("SUMMARY_VLLM_BASE_URL", "http://host.docker.internal:8000/v1/")
    monkeypatch.setenv("SUMMARY_VLLM_MODEL", "Qwen/Qwen3.6-27B")
    monkeypatch.setenv("SUMMARY_VLLM_MAX_CONCURRENCY", "2")
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)

    assert bootstrap_legacy_nodes(repository) == 1
    node = repository.list_nodes()[0]
    assert node.name == "summary-vllm"
    assert node.provider == "openai_compatible"
    assert node.base_url == "http://host.docker.internal:8000/v1"
    assert node.priority == 10
    assert node.max_concurrency == 2
    assert {(model.model_name, model.capability) for model in node.models} == {
        ("Qwen/Qwen3.6-27B", "analysis"),
        ("Qwen/Qwen3.6-27B", "chat"),
    }


def test_unhealthy_node_is_automatically_retried_after_cooldown(
    repository, monkeypatch
):
    node = create_test_node(repository)
    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "60")

    repository.record_failure(node.id, "offline")
    assert repository.get_node(node.id).health_status == "unhealthy"
    assert repository.list_candidates("chat") == []

    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "0")
    assert [candidate.node_id for candidate in repository.list_candidates("chat")] == [node.id]


def test_success_and_failure_metrics_are_recorded(repository, monkeypatch):
    node = create_test_node(repository)
    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "2")

    repository.record_failure(node.id, "timeout", 12.5)
    failed = repository.get_node(node.id)
    assert failed.health_status == "degraded"
    assert failed.consecutive_failures == 1
    assert failed.last_error == "timeout"
    assert failed.last_latency_ms == 12.5
    assert failed.last_checked_at is not None

    repository.record_success(node.id, 4.25)
    healthy = repository.get_node(node.id)
    assert healthy.health_status == "healthy"
    assert healthy.consecutive_failures == 0
    assert healthy.last_error is None
    assert healthy.last_success_at is not None
