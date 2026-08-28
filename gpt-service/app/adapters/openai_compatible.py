from __future__ import annotations

import os
from time import perf_counter
from typing import Any, Mapping, Sequence

from .base import (
    AIAdapter,
    AdapterError,
    AdapterResponseError,
    ChatMessage,
    ChatResult,
    HealthResult,
    JsonObject,
    ResponseFormat,
    require_model,
    validate_messages,
)


class OpenAICompatibleAdapter(AIAdapter):
    """Adapter for vLLM and other OpenAI-compatible inference servers."""

    @property
    def _api_base_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return self.base_url
        return f"{self.base_url}/v1"

    async def chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        response_format: ResponseFormat | None = None,
    ) -> ChatResult:
        normalized_model = require_model(model)
        payload: JsonObject = {
            "model": normalized_model,
            # OpenAI-format content lists (including image_url data URLs) are
            # intentionally kept intact for vision-capable compatible servers.
            "messages": _to_openai_messages(validate_messages(messages)),
            "stream": False,
        }
        max_tokens = _optional_positive_int("OPENAI_COMPATIBLE_MAX_TOKENS")
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        temperature = _optional_nonnegative_float("OPENAI_COMPATIBLE_TEMPERATURE")
        if temperature is not None:
            payload["temperature"] = temperature
        if _environment_flag("OPENAI_COMPATIBLE_DISABLE_THINKING"):
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        normalized_format = _to_openai_response_format(response_format)
        if normalized_format is not None:
            payload["response_format"] = normalized_format

        data = await self._request_json(
            "POST",
            f"{self._api_base_url}/chat/completions",
            json=payload,
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise AdapterResponseError("OpenAI-compatible response did not include choices")

        first_choice = choices[0]
        message = first_choice.get("message")
        content = _message_content(message)
        if content is None:
            raise AdapterResponseError(
                "OpenAI-compatible response did not include choices[0].message.content"
            )

        raw_usage = data.get("usage")
        usage = dict(raw_usage) if isinstance(raw_usage, Mapping) else None
        return ChatResult(
            content=content,
            raw=data,
            model=data.get("model") if isinstance(data.get("model"), str) else normalized_model,
            finish_reason=(
                first_choice.get("finish_reason")
                if isinstance(first_choice.get("finish_reason"), str)
                else None
            ),
            usage=usage,
        )

    async def list_models(self) -> list[str]:
        data = await self._request_json("GET", f"{self._api_base_url}/models")
        raw_models = data.get("data")
        if not isinstance(raw_models, list):
            raise AdapterResponseError("OpenAI-compatible models response did not include data")

        models: list[str] = []
        for item in raw_models:
            if not isinstance(item, Mapping):
                continue
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip() and model_id not in models:
                models.append(model_id)
        return models

    async def health(self, model: str | None = None) -> HealthResult:
        started_at = perf_counter()
        try:
            models = await self.list_models()
            error = _missing_model_error(model, models)
            return HealthResult(
                healthy=error is None,
                latency_ms=(perf_counter() - started_at) * 1000,
                error=error,
                models=models,
            )
        except AdapterError as exc:
            return HealthResult(
                healthy=False,
                latency_ms=(perf_counter() - started_at) * 1000,
                error=str(exc),
            )


def _to_openai_response_format(response_format: ResponseFormat | None) -> JsonObject | None:
    if response_format is None:
        return None
    if isinstance(response_format, str):
        format_type = "json_object" if response_format == "json" else response_format
        return {"type": format_type}
    return dict(response_format)


def _optional_positive_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


def _environment_flag(name: str) -> bool:
    return os.getenv(name, "").strip().upper() in {"1", "TRUE", "YES", "ON"}


def _optional_nonnegative_float(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if value >= 0 else None


def _to_openai_messages(messages: list[JsonObject]) -> list[JsonObject]:
    normalized: list[JsonObject] = []
    for original in messages:
        message = dict(original)
        custom_images = message.pop("image_data_url", None)
        content = message.get("content")

        if isinstance(content, list):
            content_parts = [_normalize_content_part(part) for part in content]
        elif custom_images is not None:
            content_parts: list[Any] = []
            if isinstance(content, str) and content:
                content_parts.append({"type": "text", "text": content})
        else:
            normalized.append(message)
            continue

        if custom_images is not None:
            candidates = custom_images if isinstance(custom_images, list) else [custom_images]
            for image_data_url in candidates:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    }
                )
        message["content"] = content_parts
        normalized.append(message)
    return normalized


def _normalize_content_part(part: Any) -> Any:
    if not isinstance(part, Mapping) or part.get("type") != "image_data_url":
        return dict(part) if isinstance(part, Mapping) else part

    value = part.get("image_data_url")
    if isinstance(value, Mapping):
        value = value.get("url")
    return {"type": "image_url", "image_url": {"url": value}}


def _message_content(message: Any) -> str | None:
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if isinstance(content, str):
        normalized = content.strip()
        return normalized or None
    if not isinstance(content, list):
        return None

    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, Mapping):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())
    return "\n".join(text_parts) or None


def _missing_model_error(model: str | None, models: list[str]) -> str | None:
    if model is None:
        return None
    normalized_model = model.strip()
    if not normalized_model or normalized_model in models:
        return None
    return f"model '{normalized_model}' is not available"
