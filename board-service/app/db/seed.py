from datetime import datetime, timezone


SEED_BOARD_IDS = [
    "11111111-1111-1111-1111-111111111111",
    "11111111-1111-1111-1111-111111111112",
    "11111111-1111-1111-1111-111111111113",
]


def seed_boards(dry_run: bool = False) -> list[dict]:
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    rows = [
        {
            "id": SEED_BOARD_IDS[0],
            "source_id": "seed-1",
            "category": "humor",
            "no": 1,
            "site": "dcinside",
            "title": "seed title 1",
            "url": "https://example.com/post/1",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 2,
            "like_count": 0,
            "created_at": created_at,
        },
        {
            "id": SEED_BOARD_IDS[1],
            "source_id": "seed-2",
            "category": "issue",
            "no": 2,
            "site": "ygosu",
            "title": "seed title 2",
            "url": "https://example.com/post/2",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 0,
            "like_count": 0,
            "created_at": created_at,
        },
        {
            "id": SEED_BOARD_IDS[2],
            "source_id": "seed-3",
            "category": "free",
            "no": 3,
            "site": "ppomppu",
            "title": "seed title 3",
            "url": "https://example.com/post/3",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 0,
            "like_count": 0,
            "created_at": created_at,
        },
    ]
    if dry_run:
        return rows

    from app.db.models import Board
    from app.db.postgres import Base, get_engine, get_session_factory
    from sqlalchemy import text

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE boards ALTER COLUMN no TYPE BIGINT"))

    with get_session_factory()() as session:
        for row in rows:
            if session.get(Board, row["id"]) is None:
                session.add(Board(**row))
        session.commit()

    return rows


def main() -> int:
    rows = seed_boards()
    print(f"seeded boards: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
