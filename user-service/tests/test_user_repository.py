import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.models import User
from app.db.postgres import Base
from app.repositories import users as users_repository
from app.repositories.users import UserRepository


def test_refresh_token_rotation_is_atomic(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(users_repository, "get_session_factory", lambda: session_factory)

    with session_factory() as session:
        session.add(
            User(
                user_id="123",
                auth_provider="kakao",
                refresh_token="refresh-old",
            )
        )
        session.commit()

    repository = object.__new__(UserRepository)
    assert repository.rotate_refresh_token(
        "123",
        "kakao",
        "refresh-old",
        "refresh-first",
    )
    assert not repository.rotate_refresh_token(
        "123",
        "kakao",
        "refresh-old",
        "refresh-second",
    )

    with session_factory() as session:
        user = session.query(User).filter_by(user_id="123", auth_provider="kakao").one()
        assert user.refresh_token == "refresh-first"
