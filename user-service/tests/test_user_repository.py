import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.models import User, UserSession
from app.db.postgres import Base
from app.repositories import users as users_repository
from app.repositories.users import UserRepository


def build_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(users_repository, "get_session_factory", lambda: session_factory)
    return session_factory


def test_repository_initialization_adds_sessions_to_an_existing_users_database(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    auth_provider VARCHAR(64) NOT NULL,
                    nickname VARCHAR(255),
                    profile_image VARCHAR(1024),
                    refresh_token VARCHAR(2048),
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_users_provider_user_id
                        UNIQUE (auth_provider, user_id)
                )
                """
            )
        )

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(users_repository, "get_engine", lambda: engine)
    monkeypatch.setattr(users_repository, "get_session_factory", lambda: session_factory)

    UserRepository()

    inspector = inspect(engine)
    assert inspector.has_table("user_sessions")
    assert "display_name" in {column["name"] for column in inspector.get_columns("users")}
    assert {"refresh_token_hash", "expires_at"} <= {
        column["name"] for column in inspector.get_columns("user_sessions")
    }


def test_new_logins_create_independent_hashed_sessions(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    repository = object.__new__(UserRepository)
    first_expiry = datetime.now(timezone.utc) + timedelta(days=400)
    second_expiry = first_expiry + timedelta(minutes=1)

    first_user = repository.create_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        first_expiry,
        nickname="왕짱",
    )
    second_user = repository.create_refresh_session(
        "123",
        "kakao",
        "b" * 64,
        second_expiry,
    )

    with session_factory() as session:
        user = session.scalar(select(User).where(User.user_id == "123"))
        sessions = session.scalars(select(UserSession).where(UserSession.user_id == user.id)).all()

    assert user.refresh_token is None
    assert "refresh_token" not in first_user
    assert "refresh_token" not in second_user
    assert {stored.refresh_token_hash for stored in sessions} == {"a" * 64, "b" * 64}
    assert len(sessions) == 2


def test_new_login_preserves_an_unmigrated_legacy_session(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    with session_factory() as session:
        session.add(
            User(
                user_id="123",
                auth_provider="kakao",
                refresh_token="legacy-raw-token",
            )
        )
        session.commit()

    repository = object.__new__(UserRepository)
    repository.create_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        datetime.now(timezone.utc) + timedelta(days=400),
    )

    with session_factory() as session:
        user = session.scalar(select(User))
        stored = session.scalar(select(UserSession))

    assert user.refresh_token == "legacy-raw-token"
    assert stored.refresh_token_hash == "a" * 64


def test_each_browser_session_rotates_without_invalidating_the_other(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    repository = object.__new__(UserRepository)
    expiry = datetime.now(timezone.utc) + timedelta(days=400)
    repository.create_refresh_session("123", "kakao", "a" * 64, expiry)
    repository.create_refresh_session("123", "kakao", "b" * 64, expiry)

    assert repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "c" * 64,
        expiry,
        legacy_refresh_token="raw-first-token",
    )
    assert repository.rotate_refresh_session(
        "123",
        "kakao",
        "b" * 64,
        "d" * 64,
        expiry,
        legacy_refresh_token="raw-second-token",
    )

    with session_factory() as session:
        hashes = set(session.scalars(select(UserSession.refresh_token_hash)).all())

    assert hashes == {"c" * 64, "d" * 64}


def test_refresh_session_rotation_is_atomic_and_slides_expiry(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    repository = object.__new__(UserRepository)
    current_expiry = datetime.now(timezone.utc) + timedelta(days=1)
    next_expiry = datetime.now(timezone.utc) + timedelta(days=400)
    repository.create_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        current_expiry,
    )

    assert repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "b" * 64,
        next_expiry,
        legacy_refresh_token="raw-current-token",
    )
    assert not repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "c" * 64,
        next_expiry,
        legacy_refresh_token="raw-current-token",
    )

    with session_factory() as session:
        stored = session.scalar(select(UserSession))

    assert stored.refresh_token_hash == "b" * 64
    assert stored.expires_at.replace(tzinfo=timezone.utc) == next_expiry


def test_legacy_plaintext_token_is_atomically_migrated_on_first_refresh(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    with session_factory() as session:
        session.add(
            User(
                user_id="123",
                auth_provider="kakao",
                refresh_token="legacy-raw-token",
            )
        )
        session.commit()

    repository = object.__new__(UserRepository)
    next_expiry = datetime.now(timezone.utc) + timedelta(days=400)
    assert repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "b" * 64,
        next_expiry,
        legacy_refresh_token="legacy-raw-token",
    )
    assert not repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "c" * 64,
        next_expiry,
        legacy_refresh_token="legacy-raw-token",
    )

    with session_factory() as session:
        user = session.scalar(select(User))
        stored = session.scalar(select(UserSession))

    assert user.refresh_token is None
    assert stored.user_id == user.id
    assert stored.refresh_token_hash == "b" * 64
    assert "legacy-raw-token" not in stored.refresh_token_hash


def test_expired_session_cannot_be_rotated(monkeypatch):
    session_factory = build_session_factory(monkeypatch)
    repository = object.__new__(UserRepository)
    repository.create_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert not repository.rotate_refresh_session(
        "123",
        "kakao",
        "a" * 64,
        "b" * 64,
        datetime.now(timezone.utc) + timedelta(days=400),
        legacy_refresh_token="raw-current-token",
    )

    repository.create_refresh_session(
        "123",
        "kakao",
        "c" * 64,
        datetime.now(timezone.utc) + timedelta(days=400),
    )
    with session_factory() as session:
        hashes = set(session.scalars(select(UserSession.refresh_token_hash)).all())

    assert hashes == {"c" * 64}
