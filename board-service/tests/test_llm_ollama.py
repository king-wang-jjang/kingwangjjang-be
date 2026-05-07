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


def test_constructor_uses_ollama_environment_defaults(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://llm.example:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "7.5")

    llm = LLM()

    assert llm.base_url == "http://llm.example:11434"
    assert llm.model == "custom-model"
    assert llm.timeout_seconds == 7.5


def test_analyze_returns_summary_and_tags_from_json_response(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return DummyResponse(
            {
                "message": {
                    "content": '{"summary":"핵심 요약","tags":["유머","이슈","유머"]}'
                }
            }
        )

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    result = LLM(base_url="http://llm.local", model="gemma4:e4b").analyze("게시글 본문")

    assert result == {"summary": "핵심 요약", "tags": ["유머", "이슈"]}
    assert calls[0]["json"]["messages"][0]["role"] == "system"
    assert "summary" in calls[0]["json"]["messages"][0]["content"]
    assert calls[0]["json"]["format"] == "json"
    assert calls[0]["json"]["messages"][1] == {"role": "user", "content": "게시글 본문"}
