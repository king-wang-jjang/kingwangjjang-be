import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.utils.crawled_content import (
    analysis_body_char_count,
    analysis_body_language_char_count,
    analysis_max_input_chars,
    analysis_min_body_chars,
    analysis_min_language_chars,
    analysis_retryable_backoff_seconds,
    analysis_vision_max_pixels,
    analysis_vision_prompt,
    extract_llm_text,
    has_sufficient_analysis_body,
)


def test_extract_llm_text_is_unchanged_when_content_fits():
    result = extract_llm_text(
        "title",
        [
            {"type": "text", "text": "first paragraph"},
            {"type": "image", "text": "visible text"},
        ],
        max_chars=1_000,
    )

    assert result == "title\nfirst paragraph\n[image] visible text"


def test_extract_llm_text_truncates_blocks_fairly_and_deterministically():
    contents = [
        {"type": "text", "text": "앞" * 200},
        {"type": "image", "text": "그림" * 120},
        {"type": "text", "text": "뒤" * 200},
    ]

    first = extract_llm_text("중요 제목", contents, max_chars=160)
    second = extract_llm_text("중요 제목", contents, max_chars=160)

    assert first == second
    assert len(first) <= 160
    assert first.startswith("중요 제목\n")
    assert "[image]" in first
    assert "앞" in first
    assert "뒤" in first
    assert first.endswith("[... content truncated ...]")


def test_analysis_body_count_excludes_whitespace_and_media_paths():
    contents = [
        {"type": "text", "text": " 본문 내용 123 "},
        {"type": "image", "media_path": "private/image.webp"},
        {"type": "image", "alt_text": " 사진 설명 "},
    ]

    assert analysis_body_char_count(contents) == len("본문내용123사진설명")
    assert analysis_body_language_char_count(contents) == len("본문내용사진설명")
    assert has_sufficient_analysis_body(
        contents,
        min_body_chars=10,
        min_language_chars=4,
    )
    assert not has_sufficient_analysis_body(
        [{"type": "text", "text": "12345678901234567890"}],
        min_body_chars=20,
        min_language_chars=4,
    )


def test_analysis_body_count_excludes_title_duplicates_and_duplicate_blocks():
    title = "제목을 그대로 복사한 게시글"
    contents = [
        {"type": "text", "text": title},
        {"type": "text", "text": title},
        {"type": "text", "text": "짧은 설명"},
        {"type": "text", "text": "짧은 설명"},
    ]

    assert analysis_body_char_count(contents, title=title) == len("짧은설명")
    assert analysis_body_language_char_count(contents, title=title) == len("짧은설명")
    assert not has_sufficient_analysis_body(
        contents,
        title=title,
        min_body_chars=20,
        min_language_chars=4,
    )


def test_analysis_body_count_excludes_media_reference_alt_and_supports_unicode():
    path_alt = "Dcinside/humor/123/important_image_description.webp"

    assert not has_sufficient_analysis_body(
        [{"type": "image", "alt_text": path_alt}],
        min_body_chars=20,
        min_language_chars=4,
    )
    assert has_sufficient_analysis_body(
        [{"type": "text", "text": "日本語の本文には背景と利用者の反応が詳しく書かれています"}],
        title="短",
        min_body_chars=20,
        min_language_chars=4,
    )
    assert has_sufficient_analysis_body(
        [{"type": "text", "text": "a detailed account explains what happened and why it matters"}],
        title="a",
        min_body_chars=20,
        min_language_chars=4,
    )


def test_analysis_limits_use_bounded_environment_values(monkeypatch):
    monkeypatch.setenv("AI_ANALYSIS_MAX_INPUT_CHARS", "-1")
    monkeypatch.setenv("AI_ANALYSIS_MIN_BODY_CHARS", "999999")
    monkeypatch.setenv("AI_ANALYSIS_MIN_LANGUAGE_CHARS", "0")
    monkeypatch.setenv("AI_ANALYSIS_VISION_MAX_PIXELS", "999999999")
    monkeypatch.setenv("AI_ANALYSIS_RETRYABLE_BACKOFF_SECONDS", "0")

    assert analysis_max_input_chars() == 1_000
    assert analysis_min_body_chars() == 10_000
    assert analysis_min_language_chars() == 1
    assert analysis_vision_max_pixels() == 100_000_000
    assert analysis_retryable_backoff_seconds() == 1

    monkeypatch.setenv("AI_ANALYSIS_MAX_INPUT_CHARS", "invalid")
    monkeypatch.setenv("AI_ANALYSIS_MIN_BODY_CHARS", "invalid")
    monkeypatch.setenv("AI_ANALYSIS_MIN_LANGUAGE_CHARS", "invalid")
    monkeypatch.setenv("AI_ANALYSIS_VISION_MAX_PIXELS", "invalid")
    monkeypatch.setenv("AI_ANALYSIS_RETRYABLE_BACKOFF_SECONDS", "invalid")

    assert analysis_max_input_chars() == 16_000
    assert analysis_min_body_chars() == 20
    assert analysis_min_language_chars() == 4
    assert analysis_vision_max_pixels() == 40_000_000
    assert analysis_retryable_backoff_seconds() == 300


def test_analysis_vision_prompt_describes_scene_and_visible_text(monkeypatch):
    monkeypatch.delenv("AI_ANALYSIS_VISION_PROMPT", raising=False)
    default_prompt = analysis_vision_prompt()

    assert "장면과 맥락" in default_prompt
    assert "텍스트" in default_prompt

    monkeypatch.setenv("AI_ANALYSIS_VISION_PROMPT", " custom prompt ")
    assert analysis_vision_prompt() == "custom prompt"
