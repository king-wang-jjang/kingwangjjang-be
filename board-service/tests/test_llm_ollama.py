import sys
from pathlib import Path

import httpx


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.utils import llm as llm_module
from app.utils.llm import LLM


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_call_posts_chat_payload_to_ollama(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return DummyResponse({"message": {"content": "llm api ok"}})

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(
        base_url="http://100.104.51.52:11434/",
        model="gemma4:e4b",
        timeout_seconds=3.93,
    ).call("게시글 본문")

    assert result == "llm api ok"
    assert calls == [
        {
            "url": "http://100.104.51.52:11434/api/chat",
            "json": {
                "model": "gemma4:e4b",
                "messages": [
                    {
                        "role": "system",
                        "content": LLM.SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": "게시글 본문"},
                ],
                "stream": False,
            },
            "timeout": 3.93,
        }
    ]


def test_call_returns_fallback_when_ollama_request_fails(monkeypatch):
    def fake_post(url, json, timeout):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(base_url="http://llm.local", model="gemma4:e4b").call("private content")

    assert result == LLM.FALLBACK_MESSAGE


def test_call_rotates_across_configured_ollama_endpoints(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        return DummyResponse({"message": {"content": url}})

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    llm = LLM(base_urls=["http://llm-a.local", "http://llm-b.local"], model="gemma4:e4b")

    first = llm.call("first")
    second = llm.call("second")

    assert first == "http://llm-a.local/api/chat"
    assert second == "http://llm-b.local/api/chat"
    assert calls == ["http://llm-a.local/api/chat", "http://llm-b.local/api/chat"]


def test_call_fails_over_to_next_ollama_endpoint(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        if "llm-a" in url:
            request = httpx.Request("POST", url)
            raise httpx.ConnectError("connection failed", request=request)
        return DummyResponse({"message": {"content": "backup ok"}})

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(base_urls=["http://llm-a.local", "http://llm-b.local"], model="gemma4:e4b").call(
        "private content"
    )

    assert result == "backup ok"
    assert calls == ["http://llm-a.local/api/chat", "http://llm-b.local/api/chat"]


def test_constructor_uses_ollama_environment_defaults(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://llm.example:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "7.5")

    llm = LLM()

    assert llm.base_url == "http://llm.example:11434"
    assert llm.model == "custom-model"
    assert llm.timeout_seconds == 7.5


def test_constructor_prefers_ollama_base_urls_for_multiple_servers(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URLS", "http://llm-a:11434/, http://llm-b:11434")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://single-llm:11434")

    llm = LLM()

    assert llm.base_urls == ["http://llm-a:11434", "http://llm-b:11434"]
    assert llm.base_url == "http://llm-a:11434"


def test_analyze_returns_summary_and_tags_from_json_response(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return DummyResponse(
            {
                "message": {
                    "content": (
                        '{"summary":"핵심 요약","tags":["유머","이슈","유머"],'
                        '"llm_engagement_score":78,'
                        '"llm_engagement_reason":"  논쟁적인 소재가 토론을 유발함  "}'
                    )
                }
            }
        )

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(base_url="http://llm.local", model="gemma4:e4b").analyze("게시글 본문")

    assert result == {
        "summary": "핵심 요약",
        "tags": ["유머", "이슈"],
        "llm_engagement_score": 78,
        "llm_engagement_reason": "논쟁적인 소재가 토론을 유발함",
    }
    assert calls[0]["json"]["messages"][0]["role"] == "system"
    assert "summary" in calls[0]["json"]["messages"][0]["content"]
    assert "llm_engagement_score" in calls[0]["json"]["messages"][0]["content"]
    assert "llm_engagement_reason" in calls[0]["json"]["messages"][0]["content"]
    assert all(
        boundary in calls[0]["json"]["messages"][0]["content"]
        for boundary in ("0~19", "20~39", "40~59", "60~79", "80~100")
    )
    assert calls[0]["json"]["format"] == "json"
    assert calls[0]["json"]["messages"][1] == {"role": "user", "content": "게시글 본문"}


def test_analyze_uses_central_ai_service_when_configured(monkeypatch):
    captured = {}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return DummyResponse(
            {
                "summary": "중앙 요약",
                "tags": ["AI", "AI", "노드"],
                "llm_engagement_score": 64,
                "llm_engagement_reason": "새로운 기술 소재로 호기심을 유발함",
            }
        )

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(
        service_url="http://ai-router.local/",
        service_token="service-secret",
        timeout_seconds=12,
    ).analyze("게시글 본문")

    assert result == {
        "summary": "중앙 요약",
        "tags": ["AI", "노드"],
        "llm_engagement_score": 64,
        "llm_engagement_reason": "새로운 기술 소재로 호기심을 유발함",
    }
    assert captured == {
        "url": "http://ai-router.local/api/ai/analyze",
        "json": {"content": "게시글 본문"},
        "headers": {"X-AI-Service-Token": "service-secret"},
        "timeout": 12.0,
    }


def test_analyze_uses_neutral_score_for_legacy_or_invalid_engagement_fields(monkeypatch):
    responses = [
        {"summary": "기존 응답", "tags": ["호환"]},
        {
            "summary": "잘못된 응답",
            "tags": ["호환"],
            "llm_engagement_score": "high",
            "llm_engagement_reason": ["invalid"],
        },
    ]

    def fake_post(url, *, json, headers, timeout):
        return DummyResponse(responses.pop(0))

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    llm = LLM(service_url="http://ai-router.local")

    legacy = llm.analyze("기존 게시글")
    invalid = llm.analyze("잘못된 게시글")

    assert legacy["llm_engagement_score"] == 50
    assert legacy["llm_engagement_reason"] is None
    assert invalid["llm_engagement_score"] == 50
    assert invalid["llm_engagement_reason"] is None


def test_parse_analysis_clamps_score_and_limits_reason_length():
    high = LLM()._parse_analysis(
        '{"summary":"요약","tags":[],"llm_engagement_score":101.7,'
        f'"llm_engagement_reason":"  {"근" * 250}  "}}'
    )
    low = LLM()._parse_analysis(
        '{"summary":"요약","tags":[],"llm_engagement_score":-8,'
        '"llm_engagement_reason":"   "}'
    )

    assert high["llm_engagement_score"] == 100
    assert high["llm_engagement_reason"] == "근" * 240
    assert low["llm_engagement_score"] == 0
    assert low["llm_engagement_reason"] is None


def test_explicit_ollama_url_keeps_direct_transport_when_service_env_exists(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        return DummyResponse({"message": {"content": "direct"}})

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai-router.local")
    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(base_url="http://ollama.local").call("content")

    assert result == "direct"
    assert calls == ["http://ollama.local/api/chat"]
