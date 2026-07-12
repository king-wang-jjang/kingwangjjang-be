import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import BoardRepository


class FakeVisionExtractor:
    def __init__(self):
        self.calls = []

    def extract_text(self, image_path, *, prompt=None):
        self.calls.append((Path(image_path), prompt))
        return "image text from vllm"


def test_extract_image_text_resolves_board_image_and_calls_extractor(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    media_root = tmp_path / "media"
    image_path = media_root / "Dcinside" / "humor" / "1" / "image.webp"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")

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
                    {"type": "text", "text": "body"},
                    {"type": "image", "media_path": "Dcinside/humor/1/image.webp"},
                ],
            )
        )
        session.commit()

    extractor = FakeVisionExtractor()

    result = repository.extract_image_text(
        "board-1",
        image_index=0,
        extractor=extractor,
        media_root=media_root,
        prompt="read exactly",
    )

    assert result == {
        "board_id": "board-1",
        "image_index": 0,
        "media_path": "Dcinside/humor/1/image.webp",
        "text": "image text from vllm",
    }
    assert extractor.calls == [(image_path.resolve(), "read exactly")]


def test_extract_image_text_returns_none_for_unknown_board(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()

    assert repository.extract_image_text("missing", media_root=tmp_path) is None


def test_extract_image_text_raises_when_image_index_is_missing(monkeypatch, tmp_path):
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
                contents=[{"type": "text", "text": "body"}],
            )
        )
        session.commit()

    try:
        repository.extract_image_text("board-1", image_index=0, media_root=tmp_path)
    except ValueError as exc:
        assert "Image not found" in str(exc)
    else:
        raise AssertionError("missing image should raise")
