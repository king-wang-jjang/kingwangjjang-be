import base64
import binascii
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import MAX_ANALYSIS_REQUEST_CHARS


MAX_TEXT_LENGTH = MAX_ANALYSIS_REQUEST_CHARS
MAX_MESSAGES = 64
MAX_IMAGE_DATA_URL_LENGTH = 20_000_000
MAX_PROMPT_LENGTH = 4_000
MAX_RESPONSE_FORMAT_LENGTH = 100_000


def _validate_base64_image_data_url(value: str) -> str:
    if not value.startswith("data:image/") or ";base64," not in value[:128]:
        raise ValueError("image URL must be a base64 image data URL")
    encoded = value.split(",", 1)[1]
    if not encoded:
        raise ValueError("image data URL payload must not be empty")
    try:
        base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image data URL contains invalid base64") from exc
    return value


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("content")
    @classmethod
    def non_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class AnalyzeResponse(BaseModel):
    summary: str
    tags: list[str]
    llm_engagement_score: int = Field(ge=0, le=100)
    llm_engagement_reason: str | None = Field(
        default=None,
        max_length=240,
    )
    node_id: str
    node_name: str
    model: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_MESSAGES)
    capability: Literal["analysis", "chat", "vision"] = "chat"
    response_format: str | dict[str, Any] | None = None

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total_text_length = 0
        total_image_length = 0
        for message in value:
            if message.get("role") not in {"system", "user", "assistant", "tool"}:
                raise ValueError("each message must have a supported role")
            if "content" not in message:
                raise ValueError("each message must include content")
            content = message["content"]
            if not isinstance(content, (str, list)):
                raise ValueError("message content must be text or a content-part list")
            if isinstance(content, str):
                total_text_length += len(content)
            if isinstance(content, list):
                if not content:
                    raise ValueError("message content-part list must not be empty")
                for part in content:
                    if not isinstance(part, dict):
                        raise ValueError("message content parts must be objects")
                    text = part.get("text")
                    if isinstance(text, str):
                        total_text_length += len(text)
                    image_url = part.get("image_url")
                    if isinstance(image_url, dict):
                        image_url = image_url.get("url")
                    if isinstance(image_url, str) and image_url.startswith("data:"):
                        total_image_length += len(image_url)
                        _validate_base64_image_data_url(image_url)
        if total_text_length > MAX_TEXT_LENGTH:
            raise ValueError("total message text is too large")
        if total_image_length > MAX_IMAGE_DATA_URL_LENGTH:
            raise ValueError("total inline image data is too large")
        return value

    @model_validator(mode="after")
    def validate_response_format_size(self):
        if self.response_format is not None:
            encoded = json.dumps(self.response_format, ensure_ascii=False)
            if len(encoded) > MAX_RESPONSE_FORMAT_LENGTH:
                raise ValueError("response_format is too large")
        return self


class ChatResponse(BaseModel):
    content: str
    node_id: str
    node_name: str
    model: str


class VisionTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_data_url: str = Field(min_length=1, max_length=MAX_IMAGE_DATA_URL_LENGTH)
    prompt: str | None = Field(default=None, max_length=MAX_PROMPT_LENGTH)

    @field_validator("image_data_url")
    @classmethod
    def validate_image_data_url(cls, value: str) -> str:
        return _validate_base64_image_data_url(value)


class VisionTextResponse(BaseModel):
    text: str
    node_id: str
    node_name: str
    model: str
