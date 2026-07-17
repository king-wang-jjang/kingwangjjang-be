import json
from typing import Any


ANALYSIS_SYSTEM_PROMPT = (
    "너는 게시글 분석 및 태그 분류 전문가다. "
    "게시글을 분석하고 JSON만 반환한다. "
    '형식은 {"summary":"1000자 이내 요약","tags":["태그1","태그2"]} 이며 '
    "tags는 한국어 명사형 태그 1개에서 5개다."
)
DEFAULT_VISION_PROMPT = "이미지 안의 한국어 텍스트를 원문에 가깝게 추출해줘."


def analysis_messages(content: str) -> list[dict]:
    return [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def vision_messages(image_data_url: str, prompt: str | None = None) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or DEFAULT_VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]


def parse_analysis(content: str) -> dict[str, Any]:
    value = content.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("AI analysis response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("AI analysis response must be a JSON object")
    summary = parsed.get("summary")
    tags = parsed.get("tags")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("AI analysis response did not include summary")
    if not isinstance(tags, list):
        raise ValueError("AI analysis response did not include tags")

    normalized_tags: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        tag = tag.strip()
        if tag and tag not in normalized_tags:
            normalized_tags.append(tag)
        if len(normalized_tags) >= 5:
            break
    return {"summary": summary.strip(), "tags": normalized_tags}
