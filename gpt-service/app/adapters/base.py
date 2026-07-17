from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import httpx


JsonObject = dict[str, Any]
ChatMessage = Mapping[str, Any]
ResponseFormat = str | Mapping[str, Any]


class AdapterError(RuntimeError):
    """Base exception raised by an AI server adapter."""


class AdapterConfigurationError(AdapterError):
    """The adapter was configured with an unusable value."""


class AdapterConnectionError(AdapterError):
    """The AI server could not be reached."""


class AdapterTimeoutError(AdapterConnectionError):
    """The AI server did not respond within the configured timeout."""


class AdapterHTTPError(AdapterError):
    """The AI server returned a non-success HTTP response."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class AdapterResponseError(AdapterError):
    """The AI server returned a response that does not match its contract."""


class UnsupportedProviderError(AdapterConfigurationError):
    """No adapter is registered for the requested provider."""


@dataclass(slots=True)
class ChatResult:
    content: str
    raw: JsonObject | None = None
    model: str | None = None
    finish_reason: str | None = None
    usage: JsonObject | None = None


@dataclass(slots=True)
class HealthResult:
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None
    models: list[str] = field(default_factory=list)


class AIAdapter(ABC):
    """Common async interface for an AI inference server."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise AdapterConfigurationError("base_url must not be empty")
        if timeout_seconds <= 0:
            raise AdapterConfigurationError("timeout_seconds must be greater than zero")

        self.base_url = normalized_base_url
        self.timeout_seconds = float(timeout_seconds)
        # This value is deliberately not resolved from an environment variable here.
        # The service layer owns resolving an env-var reference and passes only its value.
        self.api_key = api_key
        self._client = client

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        response_format: ResponseFormat | None = None,
    ) -> ChatResult:
        raise NotImplementedError

    @abstractmethod
    async def health(self, model: str | None = None) -> HealthResult:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[str]:
        raise NotImplementedError

    async def aclose(self) -> None:
        # Injected clients are owned by their caller. Adapters without an
        # injected client use a short-lived client for each request, so the
        # node router can safely create an adapter per invocation.
        return None

    async def __aenter__(self) -> AIAdapter:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        json: JsonObject | None = None,
    ) -> JsonObject:
        try:
            if self._client is None:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.request(
                        method,
                        url,
                        json=json,
                        headers=self._headers,
                    )
            else:
                response = await self._client.request(
                    method,
                    url,
                    json=json,
                    headers=self._headers,
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AdapterTimeoutError(f"AI server request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise AdapterConnectionError(f"AI server request failed: {url}") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise AdapterHTTPError(
                f"AI server returned HTTP {status_code}: {url}",
                status_code=status_code,
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AdapterResponseError("AI server response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise AdapterResponseError("AI server response must be a JSON object")
        return payload


def require_model(model: str) -> str:
    normalized_model = model.strip()
    if not normalized_model:
        raise AdapterConfigurationError("model must not be empty")
    return normalized_model


def validate_messages(messages: Sequence[ChatMessage]) -> list[JsonObject]:
    if isinstance(messages, (str, bytes)) or not messages:
        raise AdapterConfigurationError("messages must contain at least one message")

    normalized: list[JsonObject] = []
    for message in messages:
        if not isinstance(message, Mapping):
            raise AdapterConfigurationError("each message must be an object")
        role = message.get("role")
        if not isinstance(role, str) or not role.strip():
            raise AdapterConfigurationError("each message must include a role")
        normalized.append(dict(message))
    return normalized
