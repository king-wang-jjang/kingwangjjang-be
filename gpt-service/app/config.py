import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_API_KEY_ENV_NAMES = {"VLLM_API_KEY", "OPENAI_API_KEY", "CHATGPT_API_KEY"}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def is_allowed_api_key_env(name: str) -> bool:
    configured = {
        item.strip()
        for item in os.getenv("AI_NODE_API_KEY_ENV_ALLOWLIST", "").split(",")
        if item.strip()
    }
    return (
        name in DEFAULT_API_KEY_ENV_NAMES
        or name.startswith("AI_NODE_API_KEY_")
        or name in configured
    )


class Config:
    """Small compatibility wrapper for existing service utilities."""

    @staticmethod
    def get_env(name: str) -> str | None:
        return os.getenv(name)

    @staticmethod
    def is_local_mode() -> bool:
        return os.getenv("SERVER_RUN_MODE", "").strip().upper() == "FALSE"

    @staticmethod
    def failure_threshold() -> int:
        return max(1, env_int("AI_NODE_FAILURE_THRESHOLD", 2))

    @staticmethod
    def retry_cooldown_seconds() -> float:
        return max(0.0, env_float("AI_NODE_RETRY_COOLDOWN_SECONDS", 30.0))

    @staticmethod
    def request_deadline_seconds() -> float:
        return max(0.1, env_float("AI_REQUEST_DEADLINE_SECONDS", 55.0))

    @staticmethod
    def database_startup_attempts() -> int:
        return max(1, env_int("AI_DATABASE_STARTUP_ATTEMPTS", 10))

    @staticmethod
    def database_startup_delay_seconds() -> float:
        return max(0.0, env_float("AI_DATABASE_STARTUP_DELAY_SECONDS", 2.0))
