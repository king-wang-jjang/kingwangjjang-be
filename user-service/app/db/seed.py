def seed_users(dry_run: bool = False) -> list[dict]:
    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "user_id": "dev-user",
            "auth_provider": "local",
            "nickname": "dev-user",
            "profile_image": None,
            "refresh_token": None,
        }
    ]
    if dry_run:
        return rows

    from app.db.models import User
    from app.db.postgres import Base, get_engine, get_session_factory

    Base.metadata.create_all(bind=get_engine())
    with get_session_factory()() as session:
        for row in rows:
            if session.get(User, row["id"]) is None:
                session.add(User(**row))
        session.commit()

    return rows


def main() -> int:
    rows = seed_users()
    print(f"seeded users: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
