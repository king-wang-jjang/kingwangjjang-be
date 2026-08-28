import sys
from pathlib import Path

import pytest
from PIL import Image


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import (
    VISION_FALLBACK_REJECTED_ERROR,
    VISION_FALLBACK_UNAVAILABLE_ERROR,
    BoardRepository,
)
from app.services.vision_text import VisionTextError
from app.utils.llm import LLMError


class FakeAnalyzer:
    def analyze(self, content: str):
        assert "seed title" in content
        assert "seed body" in content
        return {
            "summary": "저장된 요약",
            "tags": ["유머", "핫딜"],
            "llm_engagement_score": 84,
            "llm_engagement_reason": "호기심과 토론을 강하게 유발함",
        }


class UnexpectedAnalyzer:
    def analyze(self, content: str):
        raise AssertionError("already analyzed boards must not call the LLM")


class OrderedAnalyzer:
    def __init__(self, expected_title: str):
        self.expected_title = expected_title

    def analyze(self, content: str):
        assert self.expected_title in content
        return {"summary": f"{self.expected_title} 요약", "tags": ["순차처리"]}


def test_schema_upgrade_queues_legacy_summaries_for_engagement_backfill(
    monkeypatch, tmp_path
):
    from sqlalchemy import text

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    engine = postgres.get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE boards ("
                "id VARCHAR(36) PRIMARY KEY, "
                "gpt_answer TEXT, "
                "analysis_status VARCHAR(32) NOT NULL DEFAULT 'pending', "
                "analysis_retry_count INTEGER NOT NULL DEFAULT 0"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO boards (id, gpt_answer, analysis_status, analysis_retry_count) "
                "VALUES ('legacy', '기존 요약', 'done', 2)"
            )
        )

    BoardRepository()

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT llm_engagement_score, analysis_status, analysis_retry_count "
                "FROM boards WHERE id = 'legacy'"
            )
        ).one()
    assert row.llm_engagement_score is None
    assert row.analysis_status == BoardRepository.ANALYSIS_PENDING
    assert row.analysis_retry_count == 0


def test_analyze_board_persists_summary_and_tags(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents="seed body with enough detail",
            )
        )
        session.commit()

    result = repository.analyze_board("board-1", analyzer=FakeAnalyzer())

    assert result == {
        "board_id": "board-1",
        "summary": "저장된 요약",
        "tags": ["유머", "핫딜"],
        "llm_engagement_score": 84,
        "llm_engagement_reason": "호기심과 토론을 강하게 유발함",
    }

    with postgres.get_session_factory()() as session:
        board = session.get(Board, "board-1")
        assert board.gpt_answer == "저장된 요약"
        assert board.tags == ["유머", "핫딜"]
        assert board.llm_engagement_score == 84
        assert board.llm_engagement_reason == "호기심과 토론을 강하게 유발함"
        assert board.hot_score > 0
        assert board.daily_score > 0
        assert board.score_breakdown["algorithm_version"] == 3
        assert board.score_breakdown["llm_engagement_score"] == 84
        assert board.analysis_status == BoardRepository.ANALYSIS_DONE


def test_analyze_board_uses_crawled_text_content_without_media_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    class CapturingAnalyzer:
        captured = ""

        def analyze(self, content: str):
            self.captured = content
            assert "real crawled body with enough detail" in content
            assert "diagnostic-media" not in content
            assert "{'type'" not in content
            return {"summary": "요약", "tags": ["본문"]}

    analyzer = CapturingAnalyzer()
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents=[
                    {"type": "image", "path": "diagnostic-media", "content": None},
                    {
                        "type": "text",
                        "content": "real crawled body with enough detail",
                    },
                ],
            )
        )
        session.commit()

    repository.analyze_board("board-1", analyzer=analyzer)

    assert analyzer.captured == "seed title\nreal crawled body with enough detail"


def test_analyze_board_includes_media_text_with_block_context(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    class CapturingAnalyzer:
        captured = ""

        def analyze(self, content: str):
            self.captured = content
            assert "media/image.webp" not in content
            return {"summary": "summary", "tags": ["image"]}

    analyzer = CapturingAnalyzer()
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents=[
                    {"type": "text", "text": "first paragraph"},
                    {"type": "image", "media_path": "media/image.webp", "text": "text inside image"},
                    {"type": "video", "media_path": "media/video.mp4"},
                ],
            )
        )
        session.commit()

    repository.analyze_board("board-1", analyzer=analyzer)

    assert analyzer.captured == "seed title\nfirst paragraph\n[image] text inside image"


def test_analyze_board_returns_complete_existing_analysis_without_llm_call(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents="seed body with enough detail",
                gpt_answer="이미 저장된 요약",
                tags=["기존태그"],
                llm_engagement_score=50,
            )
        )
        session.commit()

    result = repository.analyze_board("board-1", analyzer=UnexpectedAnalyzer())

    assert result == {
        "board_id": "board-1",
        "summary": "이미 저장된 요약",
        "tags": ["기존태그"],
        "llm_engagement_score": 50,
        "llm_engagement_reason": None,
    }


def test_legacy_summary_without_engagement_score_is_reanalyzed(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents="seed body with enough detail",
                gpt_answer="기존 요약",
                tags=["기존태그"],
                llm_engagement_score=None,
                analysis_status=BoardRepository.ANALYSIS_DONE,
            )
        )
        session.commit()

    status = repository.get_analysis_status("board-1")
    result = repository.analyze_board("board-1", analyzer=FakeAnalyzer())

    assert status["is_complete"] is False
    assert result["llm_engagement_score"] == 84
    assert result["llm_engagement_reason"] == "호기심과 토론을 강하게 유발함"


def test_request_analysis_queues_board_without_calling_llm(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/post/1",
                contents="seed body",
            )
        )
        session.commit()

    result = repository.request_analysis("board-1")

    assert result["status"] == BoardRepository.ANALYSIS_PENDING
    assert result["summary"] is None
    assert result["retry_count"] == 0
    with postgres.get_session_factory()() as session:
        board = session.get(Board, "board-1")
        assert board.analysis_priority == BoardRepository.USER_REQUEST_PRIORITY
        assert board.analysis_requested_at is not None


def test_request_analysis_reopens_failed_board_with_fresh_retry_budget(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-failed",
                category="humor",
                no=2,
                site="dcinside",
                title="failed title",
                url="https://example.com/post/failed",
                contents="body with enough detail to analyze after retry",
                analysis_status=BoardRepository.ANALYSIS_FAILED,
                analysis_retry_count=2,
                analysis_error="vision node unavailable",
            )
        )
        session.commit()

    result = repository.request_analysis("board-failed")

    assert result["status"] == BoardRepository.ANALYSIS_PENDING
    assert result["retry_count"] == 0
    assert result["error"] is None


def test_process_next_analysis_job_prefers_requested_board(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="board-low",
                    category="humor",
                    no=1,
                    site="dcinside",
                    title="low title",
                    url="https://example.com/post/1",
                    contents="low body with enough detail",
                ),
                Board(
                    id="board-high",
                    category="humor",
                    no=2,
                    site="dcinside",
                    title="high title",
                    url="https://example.com/post/2",
                    contents="high body with enough detail",
                ),
            ]
        )
        session.commit()

    repository.request_analysis("board-high")
    result = repository.process_next_analysis_job(analyzer=OrderedAnalyzer("high title"))

    assert result["board_id"] == "board-high"
    assert result["status"] == BoardRepository.ANALYSIS_DONE
    with postgres.get_session_factory()() as session:
        high = session.get(Board, "board-high")
        low = session.get(Board, "board-low")
        assert high.gpt_answer == "high title 요약"
        assert high.analysis_status == BoardRepository.ANALYSIS_DONE
        assert low.gpt_answer is None
        assert low.analysis_status == BoardRepository.ANALYSIS_PENDING


def test_analyze_board_rejects_title_only_content_before_llm(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-sparse",
                category="humor",
                no=1,
                site="dcinside",
                title="제목만 있는 게시글",
                url="https://example.com/post/sparse",
                contents=[],
            )
        )
        session.commit()

    try:
        repository.analyze_board("board-sparse", analyzer=UnexpectedAnalyzer())
    except LLMError as exc:
        assert str(exc) == "Board content is too short for reliable analysis"
    else:
        raise AssertionError("title-only content must not reach the analyzer")

    failed_job = repository.process_next_analysis_job(
        analyzer=UnexpectedAnalyzer(),
        max_retry_count=1,
    )

    assert failed_job["status"] == BoardRepository.ANALYSIS_FAILED
    assert failed_job["summary"] is None
    assert failed_job["error"] == "Board content is too short for reliable analysis"


def test_analyze_board_rejects_body_that_only_repeats_title(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    title = "본문 칸에 제목만 반복 저장된 게시글"
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-repeated-title",
                category="humor",
                no=2,
                site="dcinside",
                title=title,
                url="https://example.com/post/repeated-title",
                contents=[{"type": "text", "text": title}],
            )
        )
        session.commit()

    with pytest.raises(
        LLMError,
        match="Board content is too short for reliable analysis",
    ):
        repository.analyze_board(
            "board-repeated-title",
            analyzer=UnexpectedAnalyzer(),
        )


def test_analyze_board_uses_bounded_vision_fallback_for_image_only_post(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    monkeypatch.setenv("AI_ANALYSIS_VISION_PROMPT", "장면과 글자를 요약해줘")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    image_path = media_root / "dcinside" / "post.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2), color="white").save(image_path)

    class FakeVisionExtractor:
        calls = []

        def extract_text(self, path, *, prompt=None):
            self.calls.append((Path(path), prompt))
            return "축제 현장에 사람들이 모여 있고 간판에 행사 일정이 적혀 있다"

    class CapturingAnalyzer:
        captured = ""

        def analyze(self, content: str):
            self.captured = content
            return {
                "summary": "축제 현장 안내 이미지",
                "tags": ["축제"],
                "llm_engagement_score": 55,
            }

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-image",
                category="humor",
                no=2,
                site="dcinside",
                title="현장 사진",
                url="https://example.com/post/image",
                contents=[
                    {
                        "type": "image",
                        "media_path": "dcinside/post.png",
                    }
                ],
            )
        )
        session.commit()

    extractor = FakeVisionExtractor()
    analyzer = CapturingAnalyzer()
    result = repository.analyze_board(
        "board-image",
        analyzer=analyzer,
        vision_extractor=extractor,
        media_root=media_root,
    )

    assert result["summary"] == "축제 현장 안내 이미지"
    assert analyzer.captured == (
        "현장 사진\n"
        "[image] 축제 현장에 사람들이 모여 있고 간판에 행사 일정이 적혀 있다"
    )
    assert extractor.calls == [(image_path.resolve(), "장면과 글자를 요약해줘")]


def test_analyze_board_skips_oversized_vision_fallback_image(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    monkeypatch.setenv("AI_ANALYSIS_VISION_MAX_IMAGE_BYTES", "3")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    image_path = media_root / "large.webp"
    image_path.parent.mkdir()
    image_path.write_bytes(b"four")

    class UnexpectedVisionExtractor:
        def extract_text(self, path, *, prompt=None):
            raise AssertionError("oversized image must not be loaded or sent")

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-large-image",
                category="humor",
                no=3,
                site="dcinside",
                title="큰 이미지",
                url="https://example.com/post/large",
                contents=[{"type": "image", "media_path": "large.webp"}],
            )
        )
        session.commit()

    try:
        repository.analyze_board(
            "board-large-image",
            analyzer=UnexpectedAnalyzer(),
            vision_extractor=UnexpectedVisionExtractor(),
            media_root=media_root,
        )
    except LLMError as exc:
        assert str(exc) == "Board content is too short for reliable analysis"
    else:
        raise AssertionError("oversized image-only content must fail preflight")


def test_analyze_board_preserves_temporary_vision_failure_reason(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    image_path = media_root / "post.png"
    media_root.mkdir()
    Image.new("RGB", (2, 2), color="white").save(image_path)

    class FailingVisionExtractor:
        def extract_text(self, path, *, prompt=None):
            raise VisionTextError("vision node timed out", retryable=True)

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-vision-unavailable",
                category="humor",
                no=5,
                site="dcinside",
                title="이미지 게시글",
                url="https://example.com/post/vision-unavailable",
                contents=[{"type": "image", "media_path": "post.png"}],
            )
        )
        session.commit()

    with pytest.raises(
        LLMError,
        match="Vision fallback is temporarily unavailable",
    ) as exc_info:
        repository.analyze_board(
            "board-vision-unavailable",
            analyzer=UnexpectedAnalyzer(),
            vision_extractor=FailingVisionExtractor(),
            media_root=media_root,
        )

    assert str(exc_info.value) == VISION_FALLBACK_UNAVAILABLE_ERROR

    retry_result = repository.process_next_analysis_job(
        analyzer=UnexpectedAnalyzer(),
        max_retry_count=1,
        vision_extractor=FailingVisionExtractor(),
        media_root=media_root,
    )

    assert retry_result["status"] == BoardRepository.ANALYSIS_PENDING
    assert retry_result["retry_count"] == 0
    assert retry_result["error"] == VISION_FALLBACK_UNAVAILABLE_ERROR
    assert retry_result["requested_at"] is not None
    assert repository.process_next_analysis_job(
        analyzer=UnexpectedAnalyzer(),
        max_retry_count=1,
        vision_extractor=FailingVisionExtractor(),
        media_root=media_root,
    ) is None


def test_partial_vision_result_does_not_hide_retryable_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    media_root.mkdir()
    for name in ("first.png", "second.png"):
        Image.new("RGB", (2, 2), color="white").save(media_root / name)

    class PartialVisionExtractor:
        calls = 0

        def extract_text(self, path, *, prompt=None):
            self.calls += 1
            if self.calls == 1:
                return "짧은 설명"
            raise VisionTextError("vision node timed out", retryable=True)

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-partial-vision",
                category="humor",
                no=6,
                site="dcinside",
                title="사진",
                url="https://example.com/post/partial-vision",
                contents=[
                    {"type": "image", "media_path": "first.png"},
                    {"type": "image", "media_path": "second.png"},
                ],
            )
        )
        session.commit()

    with pytest.raises(
        LLMError,
        match="Vision fallback is temporarily unavailable",
    ):
        repository.analyze_board(
            "board-partial-vision",
            analyzer=UnexpectedAnalyzer(),
            vision_extractor=PartialVisionExtractor(),
            media_root=media_root,
        )


def test_permanent_vision_rejection_uses_terminal_retry_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    image_path = media_root / "post.png"
    media_root.mkdir()
    Image.new("RGB", (2, 2), color="white").save(image_path)

    class RejectedVisionExtractor:
        def extract_text(self, path, *, prompt=None):
            raise VisionTextError(
                "unauthorized",
                retryable=False,
                status_code=401,
            )

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-vision-rejected",
                category="humor",
                no=7,
                site="dcinside",
                title="이미지 게시글",
                url="https://example.com/post/vision-rejected",
                contents=[{"type": "image", "media_path": "post.png"}],
            )
        )
        session.commit()

    result = repository.process_next_analysis_job(
        analyzer=UnexpectedAnalyzer(),
        max_retry_count=1,
        vision_extractor=RejectedVisionExtractor(),
        media_root=media_root,
    )

    assert result["status"] == BoardRepository.ANALYSIS_FAILED
    assert result["error"] == VISION_FALLBACK_REJECTED_ERROR


def test_analyze_board_caps_structured_input_before_analyzer(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    monkeypatch.setenv("AI_ANALYSIS_MAX_INPUT_CHARS", "1000")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    class CapturingAnalyzer:
        captured = ""

        def analyze(self, content: str):
            self.captured = content
            return {"summary": "요약", "tags": ["긴글"]}

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-long",
                category="humor",
                no=4,
                site="dcinside",
                title="중요 제목",
                url="https://example.com/post/long",
                contents=[
                    {"type": "text", "text": "앞" * 1_000},
                    {"type": "image", "text": "그림" * 1_000},
                    {"type": "text", "text": "뒤" * 1_000},
                ],
            )
        )
        session.commit()

    analyzer = CapturingAnalyzer()
    repository.analyze_board("board-long", analyzer=analyzer)

    assert len(analyzer.captured) <= 1_000
    assert analyzer.captured.startswith("중요 제목\n")
    assert "[image]" in analyzer.captured
    assert "앞" in analyzer.captured
    assert "뒤" in analyzer.captured
    assert analyzer.captured.endswith("[... content truncated ...]")
