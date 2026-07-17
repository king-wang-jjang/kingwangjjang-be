from .base import (
    AIAdapter,
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterError,
    AdapterHTTPError,
    AdapterResponseError,
    AdapterTimeoutError,
    ChatResult,
    HealthResult,
    UnsupportedProviderError,
)
from .factory import create_adapter
from .ollama import OllamaAdapter
from .openai_compatible import OpenAICompatibleAdapter

__all__ = [
    "AIAdapter",
    "AdapterConfigurationError",
    "AdapterConnectionError",
    "AdapterError",
    "AdapterHTTPError",
    "AdapterResponseError",
    "AdapterTimeoutError",
    "ChatResult",
    "HealthResult",
    "OllamaAdapter",
    "OpenAICompatibleAdapter",
    "UnsupportedProviderError",
    "create_adapter",
]
