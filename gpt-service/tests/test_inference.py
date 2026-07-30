import json

from app.services.inference import (
    ANALYSIS_SYSTEM_PROMPT,
    analysis_messages,
    parse_analysis,
    truncate_analysis_content,
)


def _analysis_payload(**overrides) -> str:
    payload = {
        "summary": " 핵심 요약 ",
        "tags": ["이슈", "이슈", "토론"],
        "llm_engagement_score": 72,
        "llm_engagement_reason": "  새로운 소재가 호기심과 토론을 유발함  ",
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_analysis_prompt_defines_content_only_calibration_and_harm_guardrail():
    assert "llm_engagement_score" in ANALYSIS_SYSTEM_PROMPT
    assert "llm_engagement_reason" in ANALYSIS_SYSTEM_PROMPT
    assert all(
        boundary in ANALYSIS_SYSTEM_PROMPT
        for boundary in ("0~19", "20~39", "40~59", "60~79", "80~100")
    )
    assert all(
        signal in ANALYSIS_SYSTEM_PROMPT
        for signal in ("호기심", "새로움", "감정적 강도", "논쟁성")
    )
    assert "본문만 보고" in ANALYSIS_SYSTEM_PROMPT
    assert "단순히 해로움 때문에 높은 점수를 주지 않는다" in ANALYSIS_SYSTEM_PROMPT


def test_parse_analysis_preserves_summary_tags_and_normalizes_engagement_fields():
    result = parse_analysis(f"```json\n{_analysis_payload()}\n```")

    assert result == {
        "summary": "핵심 요약",
        "tags": ["이슈", "토론"],
        "llm_engagement_score": 72,
        "llm_engagement_reason": "새로운 소재가 호기심과 토론을 유발함",
    }


def test_parse_analysis_uses_neutral_defaults_for_missing_or_invalid_fields():
    missing = parse_analysis(_analysis_payload(llm_engagement_score=None))
    invalid = parse_analysis(
        _analysis_payload(
            llm_engagement_score="very high",
            llm_engagement_reason={"reason": "invalid"},
        )
    )
    boolean = parse_analysis(_analysis_payload(llm_engagement_score=True))

    assert missing["llm_engagement_score"] == 50
    assert invalid["llm_engagement_score"] == 50
    assert invalid["llm_engagement_reason"] is None
    assert boolean["llm_engagement_score"] == 50


def test_parse_analysis_clamps_numeric_score_and_truncates_reason():
    too_high = parse_analysis(
        _analysis_payload(
            llm_engagement_score=140.4,
            llm_engagement_reason=f"  {'글' * 250}  ",
        )
    )
    too_low = parse_analysis(_analysis_payload(llm_engagement_score=-3))
    huge = parse_analysis(_analysis_payload(llm_engagement_score=10**1000))

    assert too_high["llm_engagement_score"] == 100
    assert too_low["llm_engagement_score"] == 0
    assert huge["llm_engagement_score"] == 100
    assert too_high["llm_engagement_reason"] == "글" * 240


def test_parse_analysis_returns_none_for_blank_reason():
    result = parse_analysis(_analysis_payload(llm_engagement_reason="   "))

    assert result["llm_engagement_reason"] is None


def test_analysis_messages_enforces_configured_structured_input_limit(monkeypatch):
    monkeypatch.setenv("AI_ANALYSIS_MAX_INPUT_CHARS", "1000")
    content = "\n".join(
        [
            "중요 제목",
            "앞" * 1_000,
            "[image] " + ("그림" * 1_000),
            "뒤" * 1_000,
        ]
    )

    bounded = analysis_messages(content)[1]["content"]

    assert len(bounded) <= 1_000
    assert bounded.startswith("중요 제목\n")
    assert "[image]" in bounded
    assert "앞" in bounded
    assert "뒤" in bounded
    assert bounded.endswith("[... content truncated ...]")


def test_analysis_messages_preserves_content_that_already_fits():
    content = "  제목\n본문  "

    assert analysis_messages(content)[1]["content"] == content


def test_truncate_analysis_content_handles_oversized_blank_text():
    assert truncate_analysis_content(" " * 2_000, max_chars=1_000) == ""
