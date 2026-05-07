from datetime import datetime, timezone


def seed_comments(dry_run: bool = False) -> list[dict]:
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    root_id = "22222222-2222-2222-2222-222222222222"
    rows = [
        {
            "id": root_id,
            "board_id": "11111111-1111-1111-1111-111111111111",
            "parent_id": None,
            "user_id": "dev-user",
            "user_nickname": "dev-user",
            "content": "seed comment",
            "like_count": 0,
            "reply_count": 1,
            "is_deleted": False,
            "created_at": created_at,
            "updated_at": created_at,
        },
        {
            "id": "22222222-2222-2222-2222-222222222223",
            "board_id": "11111111-1111-1111-1111-111111111111",
            "parent_id": root_id,
            "user_id": "dev-user",
            "user_nickname": "dev-user",
            "content": "seed reply",
            "like_count": 0,
            "reply_count": 0,
            "is_deleted": False,
            "created_at": created_at,
            "updated_at": created_at,
        },
    ]
    if dry_run:
        return rows

    from app.db.models import Comment
    from app.db.postgres import Base, get_engine, get_session_factory

    Base.metadata.create_all(bind=get_engine())
    with get_session_factory()() as session:
        for row in rows:
            if session.get(Comment, row["id"]) is None:
                session.add(Comment(**row))
        session.commit()

    return rows


def main() -> int:
    rows = seed_comments()
    print(f"seeded comments: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
