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
        return {"summary": "저장된 요약", "tags": ["유머", "핫딜"]}


class UnexpectedAnalyzer:
    def analyze(self, content: str):
        raise AssertionError("already analyzed boards must not call the LLM")


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
    }

    with postgres.get_session_factory()() as session:
        board = session.get(Board, "board-1")
        assert board.gpt_answer == "저장된 요약"
        assert board.tags == ["유머", "핫딜"]


def test_analyze_board_returns_existing_summary_without_llm_call(monkeypatch, tmp_path):
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
            )
        )
        session.commit()

    result = repository.analyze_board("board-1", analyzer=UnexpectedAnalyzer())

    assert result == {
        "board_id": "board-1",
        "summary": "이미 저장된 요약",
        "tags": ["기존태그"],
    }
