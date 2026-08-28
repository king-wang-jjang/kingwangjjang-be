import os

from app.repositories.ai_nodes import AINodeRepository


def _timeout(name: str, default: float = 60.0) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().upper() not in {"0", "FALSE", "NO", "OFF"}


def _ollama_urls() -> list[str]:
    multi = os.getenv("OLLAMA_BASE_URLS", "")
    values = [value.strip().rstrip("/") for value in multi.split(",") if value.strip()]
    if not values:
        single = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
        values = [single] if single else ["http://100.104.51.52:11434"]
    return list(dict.fromkeys(values))


def legacy_node_definitions() -> list[dict]:
    definitions: list[dict] = []
    if _enabled("AI_BOOTSTRAP_OLLAMA_ENABLED"):
        ollama_model = os.getenv("OLLAMA_MODEL") or "gemma4:e4b"
        ollama_timeout = _timeout("OLLAMA_TIMEOUT_SECONDS")
        ollama_urls = _ollama_urls()
    else:
        ollama_urls = []
    for index, base_url in enumerate(ollama_urls, start=1):
        definitions.append(
            {
                "values": {
                    "name": f"legacy-ollama-{index}",
                    "provider": "ollama",
                    "base_url": base_url,
                    "enabled": True,
                    "priority": 100,
                    "weight": 1,
                    "max_concurrency": 1,
                    "timeout_seconds": ollama_timeout,
                    "health_status": "unknown",
                },
                "models": [
                    {
                        "name": ollama_model,
                        "capabilities": ["analysis", "chat"],
                        "enabled": True,
                        "is_default": True,
                    }
                ],
            }
        )

    summary_vllm_url = os.getenv("SUMMARY_VLLM_BASE_URL", "").strip().rstrip("/")
    if summary_vllm_url:
        definitions.append(
            {
                "values": {
                    "name": "summary-vllm",
                    "provider": "openai_compatible",
                    "base_url": summary_vllm_url,
                    "enabled": True,
                    "priority": 10,
                    "weight": 1,
                    "max_concurrency": _positive_int(
                        "SUMMARY_VLLM_MAX_CONCURRENCY", 2
                    ),
                    "timeout_seconds": _timeout(
                        "SUMMARY_VLLM_TIMEOUT_SECONDS", 50.0
                    ),
                    "health_status": "unknown",
                },
                "models": [
                    {
                        "name": os.getenv("SUMMARY_VLLM_MODEL")
                        or "Qwen/Qwen3.8-27B",
                        "capabilities": ["analysis", "chat"],
                        "enabled": True,
                        "is_default": True,
                    }
                ],
            }
        )

    vllm_url = os.getenv("VLLM_BASE_URL", "").strip().rstrip("/")
    if vllm_url:
        definitions.append(
            {
                "values": {
                    "name": "legacy-vllm",
                    "provider": "openai_compatible",
                    "base_url": vllm_url,
                    "enabled": True,
                    "priority": 100,
                    "weight": 1,
                    "max_concurrency": 1,
                    "timeout_seconds": _timeout("VLLM_TIMEOUT_SECONDS"),
                    "api_key_env": "VLLM_API_KEY" if os.getenv("VLLM_API_KEY") else None,
                    "health_status": "unknown",
                },
                "models": [
                    {
                        "name": os.getenv("VLLM_MODEL") or "qwen2.5-vl",
                        "capabilities": ["vision"],
                        "enabled": True,
                        "is_default": True,
                    }
                ],
            }
        )
    return definitions


def bootstrap_legacy_nodes(repository: AINodeRepository) -> int:
    """Import legacy nodes once and keep the dedicated summary node in sync."""

    definitions = legacy_node_definitions()
    created = repository.bootstrap_if_empty(definitions)
    if created:
        return created

    summary_definition = next(
        (
            definition
            for definition in definitions
            if definition["values"].get("name") == "summary-vllm"
        ),
        None,
    )
    if summary_definition is None:
        return 0
    return int(
        repository.synchronize_named_node(
            summary_definition["values"],
            summary_definition["models"],
        )
    )
