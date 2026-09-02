from fastapi.testclient import TestClient

from app.adapters import ChatResult, HealthResult
from app.main import create_app
from app.services.node_router import AINodeRouter
from conftest import create_test_node


class ContractAdapter:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.closed = False

    async def chat(self, model, messages, response_format=None):
        if self.fail:
            raise RuntimeError("private failure at http://internal-node.local")
        content = messages[-1]["content"]
        if response_format is not None and isinstance(content, str) and content != "plain chat":
            return ChatResult(
                content=(
                    '{"summary":"요약","tags":["태그","태그"],'
                    '"llm_engagement_score":73,'
                    '"llm_engagement_reason":"호기심과 토론을 유발함"}'
                )
            )
        if isinstance(content, list):
            return ChatResult(content="이미지 글자")
        return ChatResult(content="chat answer")

    async def health(self, model=None):
        return HealthResult(True, latency_ms=1.5, models=[model or "model-a"])

    async def aclose(self):
        self.closed = True


def _client(repository, *, fail: bool = False) -> TestClient:
    node_router = AINodeRouter(
        repository,
        adapter_factory=lambda _provider, **_kwargs: ContractAdapter(fail=fail),
    )
    return TestClient(create_app(repository=repository, node_router=node_router))


def test_health_is_public_and_reports_managed_node_count(repository, monkeypatch):
    create_test_node(repository)
    monkeypatch.setenv("AI_NODE_ADMIN_TOKEN", "admin-secret")
    with _client(repository) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "node_count": 1}


def test_all_node_management_routes_require_admin_token(repository, monkeypatch):
    node = create_test_node(repository)
    monkeypatch.setenv("AI_NODE_ADMIN_TOKEN", "admin-secret")

    with _client(repository) as client:
        for method, path in (
            (client.get, "/api/ai/nodes"),
            (client.get, "/api/ai/resources"),
            (client.get, f"/api/ai/nodes/{node.id}"),
            (client.post, f"/api/ai/nodes/{node.id}/health-check"),
            (client.post, "/api/ai/nodes/health-check"),
            (client.delete, f"/api/ai/nodes/{node.id}"),
        ):
            assert method(path).status_code == 401

        response = client.get(
            "/api/ai/nodes",
            headers={"X-AI-Admin-Token": "admin-secret"},
        )
    assert response.status_code == 200
    assert response.json()[0]["id"] == node.id


def test_resource_overview_reports_node_capacity_and_capabilities(repository, monkeypatch):
    node = create_test_node(
        repository,
        capabilities=["analysis", "chat", "vision"],
        max_concurrency=3,
    )
    monkeypatch.setenv("AI_NODE_ADMIN_TOKEN", "admin-secret")

    with _client(repository) as client:
        response = client.get(
            "/api/ai/resources",
            headers={"X-AI-Admin-Token": "admin-secret"},
        )

    assert response.status_code == 200
    overview = response.json()
    assert overview["status"] == "healthy"
    assert overview["is_overloaded"] is False
    assert overview["window_seconds"] == 60
    assert overview["capacity"] == {
        "configured_capacity": 3,
        "effective_capacity": 3,
        "active_requests": 0,
        "available_capacity": 3,
        "utilization_percent": 0.0,
        "peak_in_flight": 0,
    }
    assert {item["capability"] for item in overview["capabilities"]} == {
        "analysis",
        "chat",
        "vision",
    }
    assert overview["nodes"][0]["id"] == node.id
    assert overview["nodes"][0]["runtime"]["effective_capacity"] == 3
    assert overview["nodes"][0]["models"][0]["capabilities"] == [
        "analysis",
        "chat",
        "vision",
    ]


def test_admin_is_allowed_without_token_only_in_local_mode(repository, monkeypatch):
    create_test_node(repository)
    monkeypatch.delenv("AI_NODE_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("SERVER_RUN_MODE", "FALSE")
    with _client(repository) as client:
        assert client.get("/api/ai/nodes").status_code == 200

    monkeypatch.setenv("SERVER_RUN_MODE", "TRUE")
    with _client(repository) as client:
        response = client.get("/api/ai/nodes")
    assert response.status_code == 503

    monkeypatch.delenv("SERVER_RUN_MODE", raising=False)
    with _client(repository) as client:
        response = client.get("/api/ai/nodes")
    assert response.status_code == 503


def test_node_crud_contract_and_raw_api_key_rejection(repository, monkeypatch):
    create_test_node(repository)
    monkeypatch.setenv("AI_NODE_ADMIN_TOKEN", "admin-secret")
    headers = {"X-AI-Admin-Token": "admin-secret"}
    payload = {
        "name": "vision-node",
        "provider": "openai_compatible",
        "base_url": "http://vision.local:8000/v1/",
        "enabled": True,
        "priority": 5,
        "weight": 2,
        "max_concurrency": 4,
        "timeout_seconds": 30,
        "api_key_env": "AI_NODE_API_KEY_VISION",
        "models": [
            {
                "name": "vision-model",
                "capabilities": ["vision", "chat"],
                "is_default": True,
            }
        ],
    }

    with _client(repository) as client:
        created_response = client.post("/api/ai/nodes", json=payload, headers=headers)
        assert created_response.status_code == 201
        created = created_response.json()
        assert created["base_url"] == "http://vision.local:8000/v1"
        assert created["api_key_env"] == "AI_NODE_API_KEY_VISION"
        assert created["models"] == [
            {
                "name": "vision-model",
                "capabilities": ["chat", "vision"],
                "enabled": True,
                "is_default": True,
            }
        ]

        updated_response = client.patch(
            f"/api/ai/nodes/{created['id']}",
            json={"enabled": False, "weight": 4},
            headers=headers,
        )
        assert updated_response.status_code == 200
        assert updated_response.json()["enabled"] is False
        assert updated_response.json()["weight"] == 4

        null_update = client.patch(
            f"/api/ai/nodes/{created['id']}",
            json={"base_url": None},
            headers=headers,
        )
        assert null_update.status_code == 422

        rejected = dict(payload)
        rejected["name"] = "unsafe"
        rejected["base_url"] = "http://unsafe.local"
        rejected["api_key"] = "must-not-be-accepted"
        response = client.post("/api/ai/nodes", json=rejected, headers=headers)
        assert response.status_code == 422

        unsafe_env = dict(payload)
        unsafe_env["name"] = "unsafe-env"
        unsafe_env["base_url"] = "http://unsafe-env.local"
        unsafe_env["api_key_env"] = "DATABASE_URL"
        response = client.post("/api/ai/nodes", json=unsafe_env, headers=headers)
        assert response.status_code == 422

        deleted = client.delete(f"/api/ai/nodes/{created['id']}", headers=headers)
        assert deleted.json() == {"deleted": created["id"]}
        assert client.get(f"/api/ai/nodes/{created['id']}", headers=headers).status_code == 404


def test_inference_contracts_and_service_token(repository, monkeypatch):
    node = create_test_node(
        repository,
        capabilities=["analysis", "chat", "vision"],
        model="multi-model",
    )
    monkeypatch.setenv("AI_SERVICE_TOKEN", "service-secret")
    headers = {"X-AI-Service-Token": "service-secret"}

    with _client(repository) as client:
        assert client.post("/api/ai/analyze", json={"content": "게시글"}).status_code == 401

        analyze = client.post(
            "/api/ai/analyze",
            json={"content": "게시글"},
            headers=headers,
        )
        assert analyze.status_code == 200
        assert analyze.json() == {
            "summary": "요약",
            "tags": ["태그"],
            "llm_engagement_score": 73,
            "llm_engagement_reason": "호기심과 토론을 유발함",
            "node_id": node.id,
            "node_name": "node-a",
            "model": "multi-model",
        }

        chat = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "plain chat"}]},
            headers=headers,
        )
        assert chat.status_code == 200
        assert chat.json() == {
            "content": "chat answer",
            "node_id": node.id,
            "node_name": "node-a",
            "model": "multi-model",
        }

        vision = client.post(
            "/api/ai/vision-text",
            json={
                "image_data_url": "data:image/png;base64,aW1hZ2U=",
                "prompt": "읽어줘",
            },
            headers=headers,
        )
        assert vision.status_code == 200
        assert vision.json() == {
            "text": "이미지 글자",
            "node_id": node.id,
            "node_name": "node-a",
            "model": "multi-model",
        }


def test_service_token_is_optional_when_unset(repository, monkeypatch):
    create_test_node(repository)
    monkeypatch.delenv("AI_SERVICE_TOKEN", raising=False)
    monkeypatch.setenv("SERVER_RUN_MODE", "FALSE")
    with _client(repository) as client:
        response = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "plain chat"}]},
        )
    assert response.status_code == 200

    monkeypatch.setenv("SERVER_RUN_MODE", "TRUE")
    with _client(repository) as client:
        response = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "plain chat"}]},
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "AI service token is not configured"}

    monkeypatch.delenv("SERVER_RUN_MODE", raising=False)
    with _client(repository) as client:
        response = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "plain chat"}]},
        )
    assert response.status_code == 503


def test_upstream_failure_returns_generic_502_without_internal_details(repository, monkeypatch):
    create_test_node(repository)
    monkeypatch.delenv("AI_SERVICE_TOKEN", raising=False)
    monkeypatch.setenv("SERVER_RUN_MODE", "FALSE")
    with _client(repository, fail=True) as client:
        response = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "plain chat"}]},
        )
    assert response.status_code == 502
    assert response.json() == {"detail": "AI node request failed"}
    assert "internal-node" not in response.text


def test_invalid_client_payload_does_not_poison_node_health(repository, monkeypatch):
    node = create_test_node(repository, capabilities=["chat", "vision"])
    monkeypatch.delenv("AI_SERVICE_TOKEN", raising=False)
    monkeypatch.setenv("SERVER_RUN_MODE", "FALSE")
    with _client(repository) as client:
        invalid_chat = client.post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": 123}]},
        )
        invalid_image = client.post(
            "/api/ai/vision-text",
            json={"image_data_url": "data:image/png;base64,not-valid-base64!"},
        )
        oversized_analysis = client.post(
            "/api/ai/analyze",
            json={"content": "x" * 200_001},
        )
        too_many_messages = client.post(
            "/api/ai/chat",
            json={
                "messages": [
                    {"role": "user", "content": "x"}
                    for _ in range(65)
                ]
            },
        )

    assert invalid_chat.status_code == 422
    assert invalid_image.status_code == 422
    assert oversized_analysis.status_code == 422
    assert too_many_messages.status_code == 422
    unchanged = repository.get_node(node.id)
    assert unchanged.health_status == "unknown"
    assert unchanged.consecutive_failures == 0


def test_individual_and_bulk_health_check_routes(repository, monkeypatch):
    first = create_test_node(repository, name="a", base_url="http://a.local")
    second = create_test_node(repository, name="b", base_url="http://b.local")
    monkeypatch.setenv("AI_NODE_ADMIN_TOKEN", "admin-secret")
    headers = {"X-AI-Admin-Token": "admin-secret"}

    with _client(repository) as client:
        individual = client.post(f"/api/ai/nodes/{first.id}/health-check", headers=headers)
        assert individual.status_code == 200
        assert individual.json()["health_status"] == "healthy"

        bulk = client.post("/api/ai/nodes/health-check", headers=headers)
        assert bulk.status_code == 200
        assert {item["id"] for item in bulk.json()} == {first.id, second.id}
        assert {item["health_status"] for item in bulk.json()} == {"healthy"}
