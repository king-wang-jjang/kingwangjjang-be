import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import BoardRepository


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
                contents="seed body",
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
        assert board.score_breakdown["algorithm_version"] == 2
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
            assert "real crawled body" in content
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
                    {"type": "text", "content": "real crawled body"},
                ],
            )
        )
        session.commit()

    repository.analyze_board("board-1", analyzer=analyzer)

    assert analyzer.captured == "seed title\nreal crawled body"


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
                contents="seed body",
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
                contents="seed body",
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
                    contents="low body",
                ),
                Board(
                    id="board-high",
                    category="humor",
                    no=2,
                    site="dcinside",
                    title="high title",
                    url="https://example.com/post/2",
                    contents="high body",
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
