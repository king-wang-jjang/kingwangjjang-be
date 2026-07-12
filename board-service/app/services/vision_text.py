import base64
import mimetypes
import os
from pathlib import Path

import httpx


class VisionTextError(RuntimeError):
    pass


DEFAULT_PROMPT = "이미지 안의 한국어 텍스트를 원문에 가깝게 추출해줘."
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_MODEL = "qwen2.5-vl"
DEFAULT_TIMEOUT_SECONDS = 60.0
IMAGE_MEDIA_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class VisionTextClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("VLLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("VLLM_API_KEY")
        self.model = model or os.getenv("VLLM_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = self._resolve_timeout(timeout_seconds)

    def extract_text(self, image_path: Path | str, *, prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or os.getenv("VLLM_IMAGE_PROMPT") or DEFAULT_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
                    ],
                }
            ],
            "temperature": 0,
        }

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise VisionTextError(str(exc)) from exc

        answer = _extract_message_content(data)
        if not answer:
            raise VisionTextError("vLLM response did not include message content")
        return answer

    @staticmethod
    def _resolve_timeout(timeout_seconds: float | None) -> float:
        if timeout_seconds is not None:
            return float(timeout_seconds)

        raw_timeout = os.getenv("VLLM_TIMEOUT_SECONDS")
        if not raw_timeout:
            return DEFAULT_TIMEOUT_SECONDS
        try:
            return float(raw_timeout)
        except ValueError:
            return DEFAULT_TIMEOUT_SECONDS


def resolve_media_path(media_path: str, media_root: Path | str | None = None) -> Path:
    root = Path(media_root or os.getenv("CRAWLER_MEDIA_ROOT") or ".").resolve()
    candidate = (root / media_path).resolve()

    if candidate != root and root not in candidate.parents:
        raise VisionTextError("media path is outside media root")
    if not candidate.is_file():
        raise VisionTextError("media file was not found")
    return candidate


def image_to_data_url(image_path: Path | str) -> str:
    path = Path(image_path)
    media_type = IMAGE_MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _extract_message_content(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    content = content.strip()
    return content or None
