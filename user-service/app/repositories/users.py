from datetime import datetime, timezone

from sqlalchemy import delete, inspect, select, text, update

from app.auth.principal import Principal
from app.db.models import User, UserSession
from app.db.postgres import Base, get_engine, get_session_factory


class UserRepository:
    def __init__(self):
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        self._ensure_user_columns(engine)

    @staticmethod
    def _to_dict(user: User) -> dict:
        return {
            "id": user.id,
            "user_id": user.user_id,
            "auth_provider": user.auth_provider,
            "nickname": user.nickname,
            "display_name": user.display_name,
            "profile_image": user.profile_image,
            "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
        }

    def get_or_create_from_principal(self, principal: Principal) -> dict:
        if not principal.user_id:
            raise ValueError("principal.user_id is required")

        auth_provider = principal.auth_provider or "unknown"
        return self.get_or_create_user(
            user_id=principal.user_id,
            auth_provider=auth_provider,
        )

    def get_user(self, user_id: str, auth_provider: str) -> dict | None:
        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == str(user_id),
                    User.auth_provider == auth_provider,
                )
            )
            return self._to_dict(user) if user is not None else None

    def create_refresh_session(
        self,
        user_id: str,
        auth_provider: str,
        refresh_token_hash: str,
        expires_at: datetime,
        nickname: str | None = None,
        profile_image: str | None = None,
    ) -> dict:
        if not user_id:
            raise ValueError("user_id is required")

        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == str(user_id),
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                user = User(
                    user_id=str(user_id),
                    auth_provider=auth_provider,
                    nickname=nickname,
                    profile_image=profile_image,
                )
                session.add(user)
                session.flush()
            else:
                if nickname is not None:
                    user.nickname = nickname
                if profile_image is not None:
                    user.profile_image = profile_image

            session.execute(
                delete(UserSession).where(
                    UserSession.user_id == user.id,
                    UserSession.expires_at <= datetime.now(timezone.utc),
                )
            )
            session.add(
                UserSession(
                    user_id=user.id,
                    refresh_token_hash=refresh_token_hash,
                    expires_at=expires_at,
                )
            )
            session.commit()
            session.refresh(user)
            return self._to_dict(user)

    def rotate_refresh_session(
        self,
        user_id: str,
        auth_provider: str,
        current_refresh_token_hash: str,
        next_refresh_token_hash: str,
        next_expires_at: datetime,
        legacy_refresh_token: str,
    ) -> bool:
        now = datetime.now(timezone.utc)
        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == str(user_id),
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                return False

            result = session.execute(
                update(UserSession)
                .where(
                    UserSession.user_id == user.id,
                    UserSession.refresh_token_hash == current_refresh_token_hash,
                    UserSession.expires_at > now,
                )
                .values(
                    refresh_token_hash=next_refresh_token_hash,
                    expires_at=next_expires_at,
                    updated_at=now,
                )
            )
            if result.rowcount == 1:
                session.execute(
                    delete(UserSession).where(
                        UserSession.user_id == user.id,
                        UserSession.expires_at <= now,
                    )
                )
                session.execute(
                    update(User)
                    .where(
                        User.id == user.id,
                        User.refresh_token == legacy_refresh_token,
                    )
                    .values(refresh_token=None)
                )
                session.commit()
                return True

            legacy_result = session.execute(
                update(User)
                .where(
                    User.id == user.id,
                    User.refresh_token == legacy_refresh_token,
                )
                .values(refresh_token=None)
            )
            if legacy_result.rowcount != 1:
                session.rollback()
                return False

            session.execute(
                delete(UserSession).where(
                    UserSession.user_id == user.id,
                    UserSession.expires_at <= now,
                )
            )
            session.add(
                UserSession(
                    user_id=user.id,
                    refresh_token_hash=next_refresh_token_hash,
                    expires_at=next_expires_at,
                )
            )
            session.commit()
            return True

    def get_or_create_user(
        self,
        user_id: str,
        auth_provider: str,
        nickname: str | None = None,
        profile_image: str | None = None,
    ) -> dict:
        if not user_id:
            raise ValueError("user_id is required")

        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == str(user_id),
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                user = User(
                    user_id=str(user_id),
                    auth_provider=auth_provider,
                    nickname=nickname,
                    profile_image=profile_image,
                )
                session.add(user)
            else:
                if nickname is not None:
                    user.nickname = nickname
                if profile_image is not None:
                    user.profile_image = profile_image

            session.commit()
            session.refresh(user)

            return self._to_dict(user)

    def update_display_name_from_principal(self, principal: Principal, display_name: str | None) -> dict:
        if not principal.user_id:
            raise ValueError("principal.user_id is required")

        user_id = str(principal.user_id)
        auth_provider = principal.auth_provider or "unknown"

        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == user_id,
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                user = User(
                    user_id=user_id,
                    auth_provider=auth_provider,
                    display_name=display_name,
                )
                session.add(user)
            else:
                user.display_name = display_name

            session.commit()
            session.refresh(user)
            return self._to_dict(user)

    @staticmethod
    def _ensure_user_columns(engine) -> None:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            return

        existing_columns = {column["name"] for column in inspector.get_columns("users")}
        if "display_name" in existing_columns:
            return

        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(40)"))
