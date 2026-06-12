from __future__ import annotations

from typing import Any


MEDIA_TYPES = {"image", "video"}


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


def extract_llm_text(title: object, contents: object) -> str:
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

    return "\n".join(parts)


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


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
