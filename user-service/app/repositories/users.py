from sqlalchemy import select

from app.auth.principal import Principal
from app.db.models import User
from app.db.postgres import Base, get_engine, get_session_factory


class UserRepository:
    def __init__(self):
        Base.metadata.create_all(bind=get_engine())

    @staticmethod
    def _to_dict(user: User) -> dict:
        return {
            "id": user.id,
            "user_id": user.user_id,
            "auth_provider": user.auth_provider,
            "nickname": user.nickname,
            "profile_image": user.profile_image,
            "refresh_token": user.refresh_token,
            "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
        }

    def get_or_create_from_principal(self, principal: Principal) -> dict:
        if not principal.user_id:
            raise ValueError("principal.user_id is required")

        auth_provider = principal.auth_provider or "unknown"
        return self.get_or_create_user(
            user_id=principal.user_id,
            auth_provider=auth_provider,
            nickname="dev-user",
            profile_image=None,
        )

    def get_or_create_user(
        self,
        user_id: str,
        auth_provider: str,
        nickname: str | None = None,
        profile_image: str | None = None,
        refresh_token: str | None = None,
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
                    refresh_token=refresh_token,
                )
                session.add(user)
            else:
                if refresh_token is not None:
                    user.refresh_token = refresh_token
                if nickname is not None:
                    user.nickname = nickname
                if profile_image is not None:
                    user.profile_image = profile_image

            session.commit()
            session.refresh(user)

            return self._to_dict(user)

    def save_auth_user(self, user_info, refresh_token: str) -> dict:
        user_id = str(user_info.user_id)
        auth_provider = user_info.auth_provider or "unknown"

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
                    nickname=getattr(user_info, "nickname", None),
                    profile_image=getattr(user_info, "profile_image", None),
                    refresh_token=refresh_token,
                )
                session.add(user)
            else:
                user.refresh_token = refresh_token
                user.nickname = getattr(user_info, "nickname", None) or user.nickname
                user.profile_image = getattr(user_info, "profile_image", None) or user.profile_image

            session.commit()
            session.refresh(user)
            return self._to_dict(user)
