from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse


MEDIA_TYPES = {"image", "video"}
MAX_ANALYSIS_REQUEST_CHARS = 200_000
DEFAULT_ANALYSIS_MAX_INPUT_CHARS = 16_000
DEFAULT_ANALYSIS_MIN_BODY_CHARS = 20
DEFAULT_ANALYSIS_MIN_LANGUAGE_CHARS = 4
DEFAULT_ANALYSIS_VISION_MAX_IMAGES = 2
DEFAULT_ANALYSIS_VISION_MAX_IMAGE_BYTES = 10_000_000
DEFAULT_ANALYSIS_VISION_MAX_PIXELS = 40_000_000
DEFAULT_ANALYSIS_RETRYABLE_BACKOFF_SECONDS = 300
DEFAULT_ANALYSIS_VISION_PROMPT = (
    "게시글 요약에 필요한 이미지의 장면과 맥락을 간결하게 설명하고, "
    "보이는 한국어 텍스트는 원문에 가깝게 함께 추출해줘."
)
MIN_ANALYSIS_MAX_INPUT_CHARS = 1_000
TRUNCATION_MARKER = "[... content truncated ...]"
MIN_TRUNCATED_PART_CHARS = 16
MIN_TITLE_SIGNAL_FOR_PARTIAL_REMOVAL = 4
MEDIA_REFERENCE_EXTENSIONS = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".m3u8",
    ".m4v",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}


def normalize_contents(contents: object) -> list[dict[str, str]]:
    if contents is None:
        return []

    if isinstance(contents, list):
        normalized = []
        for item in contents:
            block = normalize_content_block(item)
            if block:
                normalized.append(block)
        return normalized

    if isinstance(contents, dict) and "type" not in contents:
        normalized = []
        for value in contents.values():
            block = normalize_content_block(value)
            if block:
                normalized.append(block)
        return normalized

    block = normalize_content_block(contents)
    return [block] if block else []


def normalize_content_block(value: object) -> dict[str, str] | None:
    if value is None:
        return None

    if isinstance(value, str):
        return _text_block(value)

    if not isinstance(value, dict):
        return _text_block(value)

    block_type = _clean_text(value.get("type")) or "text"
    block_type = block_type.lower()

    if block_type == "text":
        return _text_block(_first_text(value, "text", "content", "alt_text", "alt"))

    if block_type in MEDIA_TYPES:
        return _media_block(
            block_type,
            media_path=value.get("media_path") or value.get("path"),
            source_url=value.get("source_url") or value.get("url"),
            text=_first_text(value, "text", "content"),
            alt_text=value.get("alt_text") or value.get("alt"),
        )

    return _text_block(_first_text(value, "text", "content", "alt_text", "alt"))


def extract_llm_text(
    title: object,
    contents: object,
    *,
    max_chars: int | None = None,
) -> str:
    parts = []
    title_text = _clean_text(title)
    if title_text:
        parts.append(title_text)

    for block in normalize_contents(contents):
        block_type = block.get("type", "text")
        block_text = _clean_text(block.get("text")) or _clean_text(block.get("alt_text"))
        if not block_text:
            continue
        if block_type in MEDIA_TYPES:
            parts.append(f"[{block_type}] {block_text}")
        else:
            parts.append(block_text)

    return truncate_analysis_parts(parts, max_chars=max_chars)


def analysis_body_char_count(contents: object, *, title: object = None) -> int:
    """Count unique alphanumeric body signals after removing title duplicates."""
    return sum(len(signal) for signal in _analysis_body_signals(contents, title=title))


def analysis_body_language_char_count(
    contents: object,
    *,
    title: object = None,
) -> int:
    """Count alphabetic characters in unique non-title body signals."""
    return sum(
        sum(character.isalpha() for character in signal)
        for signal in _analysis_body_signals(contents, title=title)
    )


def has_sufficient_analysis_body(
    contents: object,
    *,
    title: object = None,
    min_body_chars: int | None = None,
    min_language_chars: int | None = None,
) -> bool:
    required_body_chars = (
        analysis_min_body_chars()
        if min_body_chars is None
        else max(int(min_body_chars), 0)
    )
    required_language_chars = (
        analysis_min_language_chars()
        if min_language_chars is None
        else max(int(min_language_chars), 0)
    )
    return (
        analysis_body_char_count(contents, title=title) >= required_body_chars
        and analysis_body_language_char_count(contents, title=title)
        >= required_language_chars
    )


def analysis_max_input_chars() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_MAX_INPUT_CHARS",
        default=DEFAULT_ANALYSIS_MAX_INPUT_CHARS,
        minimum=MIN_ANALYSIS_MAX_INPUT_CHARS,
        maximum=MAX_ANALYSIS_REQUEST_CHARS,
    )


def analysis_min_body_chars() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_MIN_BODY_CHARS",
        default=DEFAULT_ANALYSIS_MIN_BODY_CHARS,
        minimum=1,
        maximum=10_000,
    )


def analysis_min_language_chars() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_MIN_LANGUAGE_CHARS",
        default=DEFAULT_ANALYSIS_MIN_LANGUAGE_CHARS,
        minimum=1,
        maximum=1_000,
    )


def analysis_vision_fallback_enabled() -> bool:
    raw_value = os.getenv("AI_ANALYSIS_VISION_FALLBACK_ENABLED")
    if raw_value is None:
        return True
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def analysis_vision_max_images() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_VISION_MAX_IMAGES",
        default=DEFAULT_ANALYSIS_VISION_MAX_IMAGES,
        minimum=0,
        maximum=4,
    )


def analysis_vision_max_image_bytes() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_VISION_MAX_IMAGE_BYTES",
        default=DEFAULT_ANALYSIS_VISION_MAX_IMAGE_BYTES,
        minimum=1,
        maximum=14_000_000,
    )


def analysis_vision_max_pixels() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_VISION_MAX_PIXELS",
        default=DEFAULT_ANALYSIS_VISION_MAX_PIXELS,
        minimum=1,
        maximum=100_000_000,
    )


def analysis_vision_prompt() -> str:
    return (
        _clean_text(os.getenv("AI_ANALYSIS_VISION_PROMPT"))
        or DEFAULT_ANALYSIS_VISION_PROMPT
    )


def analysis_retryable_backoff_seconds() -> int:
    return _bounded_env_int(
        "AI_ANALYSIS_RETRYABLE_BACKOFF_SECONDS",
        default=DEFAULT_ANALYSIS_RETRYABLE_BACKOFF_SECONDS,
        minimum=1,
        maximum=86_400,
    )


def truncate_analysis_text(content: object, *, max_chars: int) -> str:
    """Bound an already-rendered analysis prompt while retaining line structure."""
    if content is None:
        return ""
    text = str(content)
    if len(text) <= max_chars:
        return text
    return truncate_analysis_parts(text.splitlines(), max_chars=max_chars)


def truncate_analysis_parts(
    parts: list[str],
    *,
    max_chars: int | None,
) -> str:
    """Fairly retain the title and every selected content block under a char cap.

    The unbounded result is byte-for-byte compatible with the former newline join.
    When truncation is required, each retained block receives a fair character
    allowance and is clipped in the middle, preserving block prefixes such as
    ``[image]`` and useful tail context.
    """
    cleaned_parts = [
        clean_part
        for part in parts
        if (clean_part := _clean_text(part)) is not None
    ]
    rendered = "\n".join(cleaned_parts)
    if max_chars is None or len(rendered) <= max_chars:
        return rendered
    if max_chars <= 0:
        return ""

    first_part = cleaned_parts[0]
    if len(first_part) + len(TRUNCATION_MARKER) + 2 >= max_chars:
        return _clip_middle(first_part, max_chars)

    body_parts = cleaned_parts[1:]
    if not body_parts:
        return _clip_middle(first_part, max_chars)

    fixed_length = len(first_part) + len(TRUNCATION_MARKER) + 2
    body_budget = max_chars - fixed_length
    selected_parts = _select_body_parts(body_parts, body_budget)
    body_content_budget = body_budget - max(len(selected_parts) - 1, 0)
    limits = _fair_part_limits(
        [len(part) for part in selected_parts],
        max(body_content_budget, 0),
    )
    clipped_parts = [
        _clip_middle(part, limit)
        for part, limit in zip(selected_parts, limits, strict=True)
        if limit > 0
    ]

    result_parts = [first_part, *clipped_parts, TRUNCATION_MARKER]
    result = "\n".join(result_parts)
    if len(result) <= max_chars:
        return result
    return result[:max_chars]


def _text_block(text: object) -> dict[str, str] | None:
    text_value = _clean_text(text)
    if text_value is None:
        return None
    return {"type": "text", "text": text_value}


def _media_block(
    block_type: str,
    *,
    media_path: object = None,
    source_url: object = None,
    text: object = None,
    alt_text: object = None,
) -> dict[str, str] | None:
    block: dict[str, str] = {"type": block_type}
    _put_clean(block, "media_path", media_path)
    _put_clean(block, "source_url", source_url)
    _put_clean(block, "text", text)
    _put_clean(block, "alt_text", alt_text)
    return block if len(block) > 1 else None


def _put_clean(target: dict[str, str], key: str, value: object) -> None:
    clean_value = _clean_text(value)
    if clean_value is not None:
        target[key] = clean_value


def _first_text(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _clean_text(source.get(key))
        if value is not None:
            return value
    return None


def _analysis_body_signals(
    contents: object,
    *,
    title: object = None,
) -> list[str]:
    title_signal = _text_signal(title)
    signals = []
    seen_signals = set()
    for block in normalize_contents(contents):
        for candidate in (block.get("text"), block.get("alt_text")):
            block_text = _clean_text(candidate)
            if block_text is None or _looks_like_media_reference(block_text):
                continue
            signal = _without_title_signal(
                _text_signal(block_text),
                title_signal,
            )
            if signal and signal not in seen_signals:
                seen_signals.add(signal)
                signals.append(signal)
    return signals


def _text_signal(value: object) -> str:
    text = _clean_text(value)
    if text is None:
        return ""
    return "".join(character for character in text if character.isalnum()).casefold()


def _without_title_signal(signal: str, title_signal: str) -> str:
    if not title_signal:
        return signal
    if signal == title_signal:
        return ""
    if len(title_signal) < MIN_TITLE_SIGNAL_FOR_PARTIAL_REMOVAL:
        return signal
    if signal.startswith(title_signal):
        return signal[len(title_signal):]
    if signal.endswith(title_signal):
        return signal[:-len(title_signal)]
    return signal


def _looks_like_media_reference(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return True
    normalized_path = parsed.path.replace("\\", "/").lower()
    return any(
        normalized_path.endswith(extension)
        for extension in MEDIA_REFERENCE_EXTENSIONS
    )


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bounded_env_int(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = os.getenv(name)
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


def _select_body_parts(parts: list[str], budget: int) -> list[str]:
    if not parts or budget <= 0:
        return []

    max_parts = max(1, (budget + 1) // (MIN_TRUNCATED_PART_CHARS + 1))
    if len(parts) <= max_parts:
        return parts

    head_count = (max_parts + 1) // 2
    tail_count = max_parts - head_count
    return parts[:head_count] + (parts[-tail_count:] if tail_count else [])


def _fair_part_limits(lengths: list[int], budget: int) -> list[int]:
    limits = [0] * len(lengths)
    active = set(range(len(lengths)))
    remaining = budget

    while active and remaining > 0:
        share, remainder = divmod(remaining, len(active))
        completed = {
            index
            for index in active
            if lengths[index] <= share
        }
        if completed:
            for index in completed:
                limits[index] = lengths[index]
                remaining -= lengths[index]
            active -= completed
            continue

        for position, index in enumerate(sorted(active)):
            limits[index] = share + (1 if position < remainder else 0)
        break

    return limits


def _clip_middle(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    if max_chars <= 0:
        return ""
    if max_chars <= 3:
        return value[:max_chars]

    marker = "…"
    available = max_chars - len(marker)
    head_length = (available * 2 + 2) // 3
    tail_length = available - head_length
    if tail_length <= 0:
        return f"{value[:head_length]}{marker}"
    return f"{value[:head_length]}{marker}{value[-tail_length:]}"
