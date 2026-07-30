import base64
import mimetypes
import os
from pathlib import Path
import warnings

import httpx
from PIL import Image, UnidentifiedImageError


class VisionTextError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(message)


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
IMAGE_FORMAT_MEDIA_TYPES = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
SOURCE_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
SUPPORTED_IMAGE_FORMATS = {"GIF", "JPEG", "PNG", "WEBP"}


class VisionTextClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        service_url: str | None = None,
        service_token: str | None = None,
    ) -> None:
        resolved_service_url = service_url
        if resolved_service_url is None and base_url is None:
            resolved_service_url = os.getenv("AI_SERVICE_URL")
        self.service_url = resolved_service_url.rstrip("/") if resolved_service_url else None
        self.service_token = service_token if service_token is not None else os.getenv("AI_SERVICE_TOKEN")
        self.base_url = (base_url or os.getenv("VLLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("VLLM_API_KEY")
        self.model = model or os.getenv("VLLM_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = self._resolve_timeout(timeout_seconds)

    def extract_text(self, image_path: Path | str, *, prompt: str | None = None) -> str:
        image_data_url = image_to_data_url(image_path)
        if self.service_url:
            return self._extract_text_with_service(image_data_url, prompt=prompt)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or os.getenv("VLLM_IMAGE_PROMPT") or DEFAULT_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
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
        except httpx.HTTPStatusError as exc:
            raise _http_vision_error(exc) from exc
        except httpx.HTTPError as exc:
            raise VisionTextError(str(exc), retryable=True) from exc
        except ValueError as exc:
            raise VisionTextError(str(exc), retryable=True) from exc

        answer = _extract_message_content(data)
        if not answer:
            raise VisionTextError(
                "vLLM response did not include message content",
                retryable=True,
            )
        return answer

    def _extract_text_with_service(self, image_data_url: str, *, prompt: str | None) -> str:
        payload = {"image_data_url": image_data_url}
        if prompt:
            payload["prompt"] = prompt

        headers = {}
        if self.service_token:
            headers["X-AI-Service-Token"] = self.service_token

        try:
            response = httpx.post(
                f"{self.service_url}/api/ai/vision-text",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise _http_vision_error(exc) from exc
        except httpx.HTTPError as exc:
            raise VisionTextError(str(exc), retryable=True) from exc
        except ValueError as exc:
            raise VisionTextError(str(exc), retryable=True) from exc

        text = data.get("text") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise VisionTextError(
                "AI service vision response did not include text",
                retryable=True,
            )
        return text.strip()

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
    if media_root is not None:
        root = Path(media_root)
    else:
        configured_root = os.getenv("CRAWLER_MEDIA_ROOT")
        root = Path(configured_root or ".")
        if configured_root and not root.is_absolute():
            root = SOURCE_WORKSPACE_ROOT / root
    root = root.resolve()
    candidate = (root / media_path).resolve()

    if candidate != root and root not in candidate.parents:
        raise VisionTextError("media path is outside media root")
    if not candidate.is_file():
        raise VisionTextError("media file was not found")
    return candidate


def validate_image_file(image_path: Path | str, *, max_pixels: int) -> None:
    """Reject malformed, unsupported, or decompression-heavy crawler media."""
    path = Path(image_path)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                frame_count = int(getattr(image, "n_frames", 1) or 1)
                if image_format not in SUPPORTED_IMAGE_FORMATS:
                    raise VisionTextError("unsupported image format")
                if width <= 0 or height <= 0:
                    raise VisionTextError("invalid image dimensions")
                if width * height * frame_count > max_pixels:
                    raise VisionTextError("image pixel count exceeds the configured limit")
                image.verify()
    except VisionTextError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise VisionTextError("media file is not a valid supported image") from exc


def image_to_data_url(image_path: Path | str) -> str:
    path = Path(image_path)
    media_type = _detected_image_media_type(path)
    if media_type is None:
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


def _detected_image_media_type(path: Path) -> str | None:
    try:
        with Image.open(path) as image:
            return IMAGE_FORMAT_MEDIA_TYPES.get((image.format or "").upper())
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _http_vision_error(exc: httpx.HTTPStatusError) -> VisionTextError:
    status_code = exc.response.status_code
    retryable = (
        status_code in {408, 409, 425, 429}
        or status_code >= 500
    )
    return VisionTextError(
        str(exc),
        retryable=retryable,
        status_code=status_code,
    )
