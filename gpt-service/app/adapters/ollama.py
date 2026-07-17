from __future__ import annotations

import base64
import binascii
from time import perf_counter
from typing import Any, Mapping, Sequence

from .base import (
    AIAdapter,
    AdapterConfigurationError,
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


class OllamaAdapter(AIAdapter):
    """Adapter for Ollama's native HTTP API."""

    @property
    def _api_base_url(self) -> str:
        if self.base_url.endswith("/api"):
            return self.base_url
        return f"{self.base_url}/api"

    async def chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        response_format: ResponseFormat | None = None,
    ) -> ChatResult:
        normalized_model = require_model(model)
        payload: JsonObject = {
            "model": normalized_model,
            "messages": _to_ollama_messages(validate_messages(messages)),
            "stream": False,
        }
        normalized_format = _to_ollama_response_format(response_format)
        if normalized_format is not None:
            payload["format"] = normalized_format

        data = await self._request_json("POST", f"{self._api_base_url}/chat", json=payload)
        message = data.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise AdapterResponseError("Ollama response did not include message.content")

        usage = _ollama_usage(data)
        return ChatResult(
            content=content.strip(),
            raw=data,
            model=data.get("model") if isinstance(data.get("model"), str) else normalized_model,
            finish_reason=data.get("done_reason") if isinstance(data.get("done_reason"), str) else None,
            usage=usage or None,
        )

    async def list_models(self) -> list[str]:
        data = await self._request_json("GET", f"{self._api_base_url}/tags")
        raw_models = data.get("models")
        if not isinstance(raw_models, list):
            raise AdapterResponseError("Ollama models response did not include a models list")

        models: list[str] = []
        for item in raw_models:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip() and name not in models:
                models.append(name)
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


def _to_ollama_response_format(response_format: ResponseFormat | None) -> Any:
    if response_format is None:
        return None
    if isinstance(response_format, str):
        return "json" if response_format == "json_object" else response_format

    value = dict(response_format)
    format_type = value.get("type")
    if format_type == "json_object":
        return "json"
    if format_type == "json_schema":
        json_schema = value.get("json_schema")
        if isinstance(json_schema, Mapping) and isinstance(json_schema.get("schema"), Mapping):
            return dict(json_schema["schema"])
    return value


def _to_ollama_messages(messages: list[JsonObject]) -> list[JsonObject]:
    normalized: list[JsonObject] = []
    for original in messages:
        message = dict(original)
        images: list[str] = []

        native_images = message.get("images")
        if isinstance(native_images, list):
            images.extend(image for image in native_images if isinstance(image, str) and image)

        custom_images = message.pop("image_data_url", None)
        if custom_images is not None:
            candidates = custom_images if isinstance(custom_images, list) else [custom_images]
            images.extend(_data_url_payload(candidate) for candidate in candidates)

        content = message.get("content")
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                part_type = part.get("type")
                if part_type in {"text", "input_text"} and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
                elif part_type in {"image_url", "input_image", "image_data_url"}:
                    image_url = _image_url_from_part(part)
                    images.append(_data_url_payload(image_url))
            message["content"] = "\n".join(part for part in text_parts if part)

        if images:
            message["images"] = images
        normalized.append(message)
    return normalized


def _image_url_from_part(part: Mapping[str, Any]) -> Any:
    value = part.get("image_url")
    if isinstance(value, Mapping):
        return value.get("url")
    if value is not None:
        return value
    return part.get("image_data_url")


def _data_url_payload(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("data:") or "," not in value:
        raise AdapterConfigurationError("Ollama vision messages require a base64 data URL")
    metadata, payload = value.split(",", 1)
    if ";base64" not in metadata.lower() or not payload:
        raise AdapterConfigurationError("Ollama vision messages require a base64 data URL")
    try:
        base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AdapterConfigurationError("image data URL contains invalid base64") from exc
    return payload


def _ollama_usage(data: Mapping[str, Any]) -> JsonObject:
    usage: JsonObject = {}
    prompt_tokens = data.get("prompt_eval_count")
    completion_tokens = data.get("eval_count")
    if isinstance(prompt_tokens, int):
        usage["prompt_tokens"] = prompt_tokens
    if isinstance(completion_tokens, int):
        usage["completion_tokens"] = completion_tokens
    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        usage["total_tokens"] = prompt_tokens + completion_tokens
    return usage


def _missing_model_error(model: str | None, models: list[str]) -> str | None:
    if model is None:
        return None
    normalized_model = model.strip()
    if not normalized_model or normalized_model in models:
        return None
    return f"model '{normalized_model}' is not available"
