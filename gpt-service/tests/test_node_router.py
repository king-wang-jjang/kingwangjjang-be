import asyncio

import pytest

from app.adapters import AdapterHTTPError, ChatResult, HealthResult
from app.services.node_router import (
    AINodeRouter,
    InvalidInferenceRequestError,
    NoAvailableNodeError,
    NodeRequestFailedError,
)
from conftest import create_test_node


class FakeAdapter:
    def __init__(
        self,
        *,
        content: str = "ok",
        error: Exception | None = None,
        health: HealthResult | None = None,
        tracker: list | None = None,
    ):
        self.content = content
        self.error = error
        self.health_result = health or HealthResult(True, latency_ms=2.0, models=["model-a"])
        self.tracker = tracker if tracker is not None else []

    async def chat(self, model, messages, response_format=None):
        self.tracker.append(("chat", model, messages, response_format))
        if self.error:
            raise self.error
        return ChatResult(content=self.content, model=model)

    async def health(self, model=None):
        self.tracker.append(("health", model))
        return self.health_result

    async def aclose(self):
        self.tracker.append(("closed",))


@pytest.mark.asyncio
async def test_invoke_fails_over_and_records_each_node_state(repository, monkeypatch):
    first = create_test_node(repository, name="a", base_url="http://a.local")
    second = create_test_node(repository, name="b", base_url="http://b.local")
    trackers = {"http://a.local": [], "http://b.local": []}

    def factory(_provider, *, base_url, **_kwargs):
        if base_url == "http://a.local":
            return FakeAdapter(error=RuntimeError("connection refused"), tracker=trackers[base_url])
        return FakeAdapter(content="from-b", tracker=trackers[base_url])

    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "1")
    router = AINodeRouter(repository, adapter_factory=factory)
    result = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert result.value == "from-b"
    assert result.node_id == second.id
    assert repository.get_node(first.id).health_status == "unhealthy"
    assert repository.get_node(second.id).health_status == "healthy"
    assert ("closed",) in trackers["http://a.local"]
    assert ("closed",) in trackers["http://b.local"]


@pytest.mark.asyncio
async def test_upstream_request_rejection_fails_over_without_poisoning_node(repository):
    first = create_test_node(repository, name="a", base_url="http://a.local")
    second = create_test_node(repository, name="b", base_url="http://b.local")

    def factory(_provider, *, base_url, **_kwargs):
        if base_url == "http://a.local":
            return FakeAdapter(
                error=AdapterHTTPError("unsupported response format", status_code=400)
            )
        return FakeAdapter(content="from-b")

    router = AINodeRouter(repository, adapter_factory=factory)
    result = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert result.value == "from-b"
    assert result.node_id == second.id
    unchanged = repository.get_node(first.id)
    assert unchanged.health_status == "unknown"
    assert unchanged.consecutive_failures == 0


@pytest.mark.asyncio
async def test_all_upstream_request_rejections_become_invalid_request(repository):
    create_test_node(
        repository,
        name="a",
        base_url="http://a.local",
        capabilities=["vision"],
    )
    create_test_node(
        repository,
        name="b",
        base_url="http://b.local",
        capabilities=["vision"],
    )
    router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **_kwargs: FakeAdapter(
            error=AdapterHTTPError("unsupported payload", status_code=415)
        ),
    )

    with pytest.raises(InvalidInferenceRequestError):
        await router.invoke(
            capability="vision",
            messages=[{"role": "user", "content": "hello"}],
        )


@pytest.mark.asyncio
async def test_rejection_with_unattempted_busy_candidate_is_temporarily_unavailable(repository):
    create_test_node(
        repository,
        name="a",
        base_url="http://a.local",
        priority=1,
    )
    busy = create_test_node(
        repository,
        name="b",
        base_url="http://b.local",
        priority=2,
        max_concurrency=1,
    )
    router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **_kwargs: FakeAdapter(
            error=AdapterHTTPError("unsupported payload", status_code=400)
        ),
    )
    router._inflight[busy.id] = 1

    with pytest.raises(NoAvailableNodeError):
        await router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "hello"}],
        )


@pytest.mark.asyncio
async def test_weighted_routing_continues_across_unknown_and_healthy_nodes(repository):
    create_test_node(
        repository,
        name="a",
        base_url="http://a.local",
        weight=1,
    )
    create_test_node(
        repository,
        name="b",
        base_url="http://b.local",
        weight=2,
    )

    def factory(_provider, *, base_url, **_kwargs):
        return FakeAdapter(content=base_url)

    router = AINodeRouter(repository, adapter_factory=factory)
    selected = []
    for _ in range(6):
        result = await router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "hello"}],
        )
        selected.append(result.node_name)

    assert selected == ["a", "b", "b", "a", "b", "b"]


@pytest.mark.asyncio
async def test_priority_is_applied_before_weight(repository):
    create_test_node(
        repository,
        name="preferred",
        base_url="http://preferred.local",
        priority=1,
        weight=1,
    )
    create_test_node(
        repository,
        name="secondary",
        base_url="http://secondary.local",
        priority=10,
        weight=100,
    )
    router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **kwargs: FakeAdapter(content=kwargs["base_url"]),
    )

    selected = [
        (
            await router.invoke(
                capability="chat",
                messages=[{"role": "user", "content": "hello"}],
            )
        ).node_name
        for _ in range(3)
    ]
    assert selected == ["preferred", "preferred", "preferred"]


@pytest.mark.asyncio
async def test_request_deadline_reserves_time_for_later_failover_candidates(
    repository, monkeypatch
):
    create_test_node(repository, name="a", base_url="http://a.local")
    create_test_node(repository, name="b", base_url="http://b.local")
    timeouts = []

    def factory(_provider, *, base_url, timeout_seconds, **_kwargs):
        timeouts.append(timeout_seconds)
        if base_url == "http://a.local":
            return FakeAdapter(error=RuntimeError("offline"))
        return FakeAdapter(content="fallback")

    monkeypatch.setenv("AI_REQUEST_DEADLINE_SECONDS", "1")
    router = AINodeRouter(repository, adapter_factory=factory)
    result = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert result.value == "fallback"
    assert len(timeouts) == 2
    assert 0 < timeouts[0] <= 0.5
    assert 0 < timeouts[1] <= 1.0


@pytest.mark.asyncio
async def test_max_concurrency_routes_parallel_request_to_next_node(repository):
    create_test_node(
        repository,
        name="a",
        base_url="http://a.local",
        priority=1,
        max_concurrency=1,
    )
    create_test_node(
        repository,
        name="b",
        base_url="http://b.local",
        priority=2,
        max_concurrency=1,
    )
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingAdapter(FakeAdapter):
        async def chat(self, model, messages, response_format=None):
            started.set()
            await release.wait()
            return ChatResult(content="first", model=model)

    def factory(_provider, *, base_url, **_kwargs):
        if base_url == "http://a.local":
            return BlockingAdapter()
        return FakeAdapter(content="second")

    router = AINodeRouter(repository, adapter_factory=factory)
    first_task = asyncio.create_task(
        router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "first"}],
        )
    )
    await started.wait()
    second = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "second"}],
    )
    release.set()
    first = await first_task

    assert first.node_name == "a"
    assert second.node_name == "b"


@pytest.mark.asyncio
async def test_unhealthy_node_is_probed_after_cooldown_and_recovers(repository, monkeypatch):
    node = create_test_node(repository)
    calls = 0

    def factory(_provider, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeAdapter(error=RuntimeError("offline"))
        return FakeAdapter(content="recovered")

    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "60")
    router = AINodeRouter(repository, adapter_factory=factory)

    with pytest.raises(NodeRequestFailedError):
        await router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "hello"}],
        )
    assert repository.get_node(node.id).health_status == "unhealthy"

    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "0")
    result = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "retry"}],
    )
    assert result.value == "recovered"
    assert repository.get_node(node.id).health_status == "healthy"


@pytest.mark.asyncio
async def test_cooled_down_node_gets_recovery_probe_even_with_healthy_peer(
    repository, monkeypatch
):
    recovering = create_test_node(repository, name="a", base_url="http://a.local")
    healthy = create_test_node(repository, name="b", base_url="http://b.local")
    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "60")
    repository.record_failure(recovering.id, "offline")
    repository.record_success(healthy.id, 1.0)

    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "0")
    router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **kwargs: FakeAdapter(content=kwargs["base_url"]),
    )
    result = await router.invoke(
        capability="chat",
        messages=[{"role": "user", "content": "probe"}],
    )

    assert result.node_id == recovering.id
    assert repository.get_node(recovering.id).health_status == "healthy"


@pytest.mark.asyncio
async def test_half_open_recovery_allows_only_one_concurrent_probe(repository, monkeypatch):
    node = create_test_node(repository, max_concurrency=5)
    monkeypatch.setenv("AI_NODE_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("AI_NODE_RETRY_COOLDOWN_SECONDS", "0")
    repository.record_failure(node.id, "offline")
    started = asyncio.Event()
    release = asyncio.Event()

    class ProbeAdapter(FakeAdapter):
        async def chat(self, model, messages, response_format=None):
            started.set()
            await release.wait()
            return ChatResult(content="recovered", model=model)

    router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **_kwargs: ProbeAdapter(),
    )
    first_task = asyncio.create_task(
        router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "probe"}],
        )
    )
    await started.wait()
    with pytest.raises(NoAvailableNodeError, match="max concurrency"):
        await router.invoke(
            capability="chat",
            messages=[{"role": "user", "content": "parallel probe"}],
        )
    release.set()
    result = await first_task
    assert result.value == "recovered"


@pytest.mark.asyncio
async def test_transform_failure_also_fails_over(repository):
    create_test_node(repository, name="a", base_url="http://a.local")
    create_test_node(repository, name="b", base_url="http://b.local")

    def factory(_provider, *, base_url, **_kwargs):
        return FakeAdapter(content="bad" if base_url == "http://a.local" else "42")

    router = AINodeRouter(repository, adapter_factory=factory)
    result = await router.invoke(
        capability="analysis",
        messages=[{"role": "user", "content": "hello"}],
        transform=int,
    )
    assert result.value == 42
    assert result.node_name == "b"


@pytest.mark.asyncio
async def test_explicit_health_check_updates_state_and_resolves_api_key_env(
    repository, monkeypatch
):
    node = create_test_node(repository, api_key_env="AI_NODE_API_KEY_TEST")
    captured = {}
    monkeypatch.setenv("AI_NODE_API_KEY_TEST", "resolved-value")

    def factory(_provider, **kwargs):
        captured.update(kwargs)
        return FakeAdapter(health=HealthResult(True, latency_ms=3.5, models=["model-a"]))

    router = AINodeRouter(repository, adapter_factory=factory)
    checked, health = await router.health_check(node.id)

    assert health.healthy is True
    assert checked.health_status == "healthy"
    assert checked.last_latency_ms == 3.5
    assert captured["api_key"] == "resolved-value"
    assert repository.get_node(node.id).api_key_env == "AI_NODE_API_KEY_TEST"
