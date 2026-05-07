import logging
import os
import json

import httpx


logger = logging.getLogger("board-service")


class LLMError(RuntimeError):
    pass


class LLM:
    DEFAULT_BASE_URL = "http://100.104.51.52:11434"
    DEFAULT_MODEL = "gemma4:e4b"
    DEFAULT_TIMEOUT_SECONDS = 60.0
    FALLBACK_MESSAGE = "일시적인 오류가 발생했습니다."
    SYSTEM_PROMPT = (
        "너는 게시글 분석 및 요약 전문가다. "
        "사용자가 제공하는 게시글 내용을 정확하고 명확하게 1000자 이내로 요약한다. "
        "내용이 비어 있거나 읽을 수 없으면 '게시물의 내용을 읽을 수 없습니다.'라고 답한다."
    )
    ANALYSIS_SYSTEM_PROMPT = (
        "너는 게시글 분석 및 태그 분류 전문가다. "
        "사용자가 제공하는 게시글을 분석해서 JSON만 반환한다. "
        '반환 형식은 {"summary":"1000자 이내 요약","tags":["태그1","태그2"]} 이다. '
        "tags는 한국어 명사형 태그 1개에서 5개로 제한한다."
    )

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or self.DEFAULT_MODEL
        self.timeout_seconds = self._resolve_timeout(timeout_seconds)

    def call(self, content: str):
        try:
            return self._chat(self.SYSTEM_PROMPT, content).strip()
        except LLMError as exc:
            logger.warning("Ollama summary request failed: %s", exc)
            return self.FALLBACK_MESSAGE

    def analyze(self, content: str) -> dict:
        answer = self._chat(self.ANALYSIS_SYSTEM_PROMPT, content, response_format="json")
        return self._parse_analysis(answer)

    def _chat(self, system_prompt: str, content: str, response_format: str | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "stream": False,
        }
        if response_format:
            payload["format"] = response_format

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMError(str(exc)) from exc

        message = response_data.get("message", {})
        answer = message.get("content") if isinstance(message, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise LLMError("Ollama chat response did not include message.content")

        return answer

    def _parse_analysis(self, answer: str) -> dict:
        raw_answer = answer.strip()
        if raw_answer.startswith("```"):
            raw_answer = raw_answer.strip("`")
            if raw_answer.startswith("json"):
                raw_answer = raw_answer[4:].strip()

        try:
            parsed = json.loads(raw_answer)
        except json.JSONDecodeError as exc:
            raise LLMError("Ollama analysis response was not valid JSON") from exc

        summary = parsed.get("summary") if isinstance(parsed, dict) else None
        tags = parsed.get("tags") if isinstance(parsed, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            raise LLMError("Ollama analysis response did not include summary")

        normalized_tags = []
        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, str):
                    continue
                normalized_tag = tag.strip()
                if normalized_tag and normalized_tag not in normalized_tags:
                    normalized_tags.append(normalized_tag)
                if len(normalized_tags) >= 5:
                    break

        return {"summary": summary.strip(), "tags": normalized_tags}

    def _resolve_timeout(self, timeout_seconds: float | None) -> float:
        if timeout_seconds is not None:
            return float(timeout_seconds)

        raw_timeout = os.getenv("OLLAMA_TIMEOUT_SECONDS")
        if not raw_timeout:
            return self.DEFAULT_TIMEOUT_SECONDS

        try:
            return float(raw_timeout)
        except ValueError:
            logger.warning("Invalid OLLAMA_TIMEOUT_SECONDS; using default timeout")
            return self.DEFAULT_TIMEOUT_SECONDS
