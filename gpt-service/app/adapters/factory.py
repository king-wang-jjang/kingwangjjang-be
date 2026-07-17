from __future__ import annotations

import httpx

from .base import AIAdapter, UnsupportedProviderError
from .ollama import OllamaAdapter
from .openai_compatible import OpenAICompatibleAdapter


def create_adapter(
    provider: str,
    *,
    base_url: str,
    timeout_seconds: float,
    api_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> AIAdapter:
    normalized_provider = provider.strip().lower().replace("_", "-")
    kwargs = {
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
        "api_key": api_key,
        "client": client,
    }
    if normalized_provider == "ollama":
        return OllamaAdapter(**kwargs)
    if normalized_provider in {"openai", "openai-compatible", "vllm"}:
        return OpenAICompatibleAdapter(**kwargs)
    raise UnsupportedProviderError(f"unsupported AI provider: {provider}")
