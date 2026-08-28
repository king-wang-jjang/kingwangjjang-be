import asyncio
import base64
import json
import sys
from pathlib import Path

import httpx


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.adapters import (  # noqa: E402
    AdapterResponseError,
    OllamaAdapter,
    OpenAICompatibleAdapter,
    create_adapter,
)


def run(coroutine):
    return asyncio.run(coroutine)


def test_ollama_chat_and_json_response_format():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "gemma4:e4b",
                "message": {"role": "assistant", "content": '{"summary":"ok"}'},
                "done_reason": "stop",
                "prompt_eval_count": 5,
                "eval_count": 2,
            },
        )

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OllamaAdapter(
                base_url="http://ollama.local/",
                timeout_seconds=3,
                client=client,
            )
            return await adapter.chat(
                "gemma4:e4b",
                [{"role": "user", "content": "analyze"}],
                response_format="json",
            )

    result = run(scenario())

    assert str(captured["request"].url) == "http://ollama.local/api/chat"
    assert "Authorization" not in captured["request"].headers
    assert captured["payload"] == {
        "model": "gemma4:e4b",
        "messages": [{"role": "user", "content": "analyze"}],
        "stream": False,
        "format": "json",
    }
    assert result.content == '{"summary":"ok"}'
    assert result.model == "gemma4:e4b"
    assert result.finish_reason == "stop"
    assert result.usage == {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}


def test_ollama_converts_openai_vision_message_to_native_images():
    captured = {}
    encoded_image = base64.b64encode(b"image bytes").decode("ascii")

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "read text"}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OllamaAdapter(
                base_url="http://ollama.local",
                timeout_seconds=3,
                client=client,
            )
            return await adapter.chat(
                "vision-model",
                [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "read this"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded_image}",
                                },
                            },
                        ],
                    }
                ],
            )

    result = run(scenario())

    assert result.content == "read text"
    assert captured["payload"]["messages"] == [
        {"role": "user", "content": "read this", "images": [encoded_image]}
    ]


def test_ollama_health_returns_models_and_checks_requested_model():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://ollama.local/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "gemma4:e4b"}, {"model": "qwen2.5-vl"}]},
        )

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OllamaAdapter(
                base_url="http://ollama.local/api",
                timeout_seconds=3,
                client=client,
            )
            available = await adapter.health("gemma4:e4b")
            missing = await adapter.health("missing-model")
            return available, missing

    available, missing = run(scenario())

    assert available.healthy is True
    assert available.models == ["gemma4:e4b", "qwen2.5-vl"]
    assert available.latency_ms is not None
    assert missing.healthy is False
    assert missing.error == "model 'missing-model' is not available"


def test_openai_chat_keeps_vision_content_and_uses_resolved_api_key():
    captured = {}
    image_data_url = "data:image/webp;base64,aW1hZ2U="

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen2.5-vl",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "extracted text"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "read"},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAICompatibleAdapter(
                base_url="http://vllm.local/v1/",
                timeout_seconds=4,
                api_key="resolved-secret",
                client=client,
            )
            return await adapter.chat(
                "qwen2.5-vl",
                messages,
                response_format="json",
            )

    result = run(scenario())

    assert str(captured["request"].url) == "http://vllm.local/v1/chat/completions"
    assert captured["request"].headers["Authorization"] == "Bearer resolved-secret"
    assert captured["payload"]["messages"] == messages
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert result.content == "extracted text"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 3}


def test_openai_models_health_and_factory_aliases():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "model-a"}, {"id": "model-b"}]})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = create_adapter(
                "vllm",
                base_url="http://vllm.local",
                timeout_seconds=2,
                client=client,
            )
            health = await adapter.health("model-b")
            return adapter, health

    adapter, health = run(scenario())

    assert isinstance(adapter, OpenAICompatibleAdapter)
    assert health.healthy is True
    assert health.models == ["model-a", "model-b"]


def test_openai_chat_applies_optional_summary_generation_controls(monkeypatch):
    captured = {}
    monkeypatch.setenv("OPENAI_COMPATIBLE_MAX_TOKENS", "512")
    monkeypatch.setenv("OPENAI_COMPATIBLE_TEMPERATURE", "0")
    monkeypatch.setenv("OPENAI_COMPATIBLE_DISABLE_THINKING", "TRUE")

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "Qwen/Qwen3.6-27B",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "summary"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAICompatibleAdapter(
                base_url="http://vllm.local/v1",
                timeout_seconds=2,
                client=client,
            )
            return await adapter.chat(
                "Qwen/Qwen3.6-27B",
                [{"role": "user", "content": "summarize"}],
            )

    result = run(scenario())

    assert result.content == "summary"
    assert captured["payload"]["max_tokens"] == 512
    assert captured["payload"]["temperature"] == 0
    assert captured["payload"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_invalid_chat_shape_raises_common_response_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAICompatibleAdapter(
                base_url="http://vllm.local",
                timeout_seconds=2,
                client=client,
            )
            await adapter.chat("model-a", [{"role": "user", "content": "hello"}])

    try:
        run(scenario())
    except AdapterResponseError as exc:
        assert "choices" in str(exc)
    else:
        raise AssertionError("malformed response should raise AdapterResponseError")
