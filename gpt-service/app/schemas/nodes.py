import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import is_allowed_api_key_env


Capability = Literal["analysis", "chat", "vision"]
Provider = Literal["ollama", "openai_compatible"]
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class NodeModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    capabilities: list[Capability] = Field(min_length=1)
    enabled: bool = True
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model name is required")
        return value

    @field_validator("capabilities")
    @classmethod
    def deduplicate_capabilities(cls, value: list[Capability]) -> list[Capability]:
        return list(dict.fromkeys(value))


class NodeModelResponse(NodeModelInput):
    pass


class _NodeFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    provider: Provider
    base_url: str = Field(min_length=1, max_length=2048)
    enabled: bool = True
    priority: int = 100
    weight: int = Field(default=1, ge=1, le=100)
    max_concurrency: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    api_key_env: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_node_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("node name is required")
        return value

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if ENV_NAME_PATTERN.fullmatch(value) is None:
            raise ValueError("api_key_env must be an environment variable name")
        if not is_allowed_api_key_env(value):
            raise ValueError(
                "api_key_env must use AI_NODE_API_KEY_*, a supported AI key name, "
                "or AI_NODE_API_KEY_ENV_ALLOWLIST"
            )
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an absolute http(s) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain credentials, query, or fragment")
        return value


class AINodeCreate(_NodeFields):
    models: list[NodeModelInput] = Field(min_length=1)


class AINodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider: Provider | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    enabled: bool | None = None
    priority: int | None = None
    weight: int | None = Field(default=None, ge=1, le=100)
    max_concurrency: int | None = Field(default=None, ge=1)
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    api_key_env: str | None = Field(default=None, min_length=1, max_length=255)
    models: list[NodeModelInput] | None = Field(default=None, min_length=1)

    _normalize_node_name = field_validator("name")(_NodeFields.normalize_node_name.__func__)
    _validate_api_key_env = field_validator("api_key_env")(_NodeFields.validate_api_key_env.__func__)
    _validate_base_url = field_validator("base_url")(_NodeFields.validate_base_url.__func__)

    @model_validator(mode="after")
    def reject_null_for_non_nullable_updates(self):
        nullable_fields = {"api_key_env"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null")
        return self


class AINodeResponse(BaseModel):
    id: str
    name: str
    provider: Provider
    base_url: str
    enabled: bool
    priority: int
    weight: int
    max_concurrency: int
    timeout_seconds: float
    api_key_env: str | None
    health_status: str
    consecutive_failures: int
    last_latency_ms: float | None
    last_error: str | None
    last_checked_at: datetime | None
    last_success_at: datetime | None
    created_at: datetime
    updated_at: datetime
    models: list[NodeModelResponse]


def model_inputs_as_dicts(models: list[NodeModelInput]) -> list[dict]:
    return [model.model_dump() for model in models]


def node_to_response(node) -> AINodeResponse:
    grouped: dict[str, dict] = {}
    for model in sorted(node.models, key=lambda item: (item.model_name, item.capability)):
        item = grouped.setdefault(
            model.model_name,
            {
                "name": model.model_name,
                "capabilities": [],
                "enabled": model.enabled,
                "is_default": model.is_default,
            },
        )
        item["capabilities"].append(model.capability)
        item["enabled"] = item["enabled"] and model.enabled
        item["is_default"] = item["is_default"] or model.is_default

    return AINodeResponse(
        id=node.id,
        name=node.name,
        provider=node.provider,
        base_url=node.base_url,
        enabled=node.enabled,
        priority=node.priority,
        weight=node.weight,
        max_concurrency=node.max_concurrency,
        timeout_seconds=node.timeout_seconds,
        api_key_env=node.api_key_env,
        health_status=node.health_status,
        consecutive_failures=node.consecutive_failures,
        last_latency_ms=node.last_latency_ms,
        last_error=node.last_error,
        last_checked_at=node.last_checked_at,
        last_success_at=node.last_success_at,
        created_at=node.created_at,
        updated_at=node.updated_at,
        models=[NodeModelResponse(**item) for item in grouped.values()],
    )
