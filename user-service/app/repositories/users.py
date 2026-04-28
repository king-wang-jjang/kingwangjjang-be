from sqlalchemy import select

from app.auth.principal import Principal
from app.db.models import User
from app.db.postgres import Base, get_engine, get_session_factory


class UserRepository:
    def __init__(self):
        Base.metadata.create_all(bind=get_engine())

    def get_or_create_from_principal(self, principal: Principal) -> dict:
        if not principal.user_id:
            raise ValueError("principal.user_id is required")

        auth_provider = principal.auth_provider or "unknown"

        with get_session_factory()() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == principal.user_id,
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                user = User(
                    user_id=principal.user_id,
                    auth_provider=auth_provider,
                    nickname="dev-user",
                    profile_image=None,
                )
                session.add(user)
                session.commit()
                session.refresh(user)

            return {
                "id": user.id,
                "user_id": user.user_id,
                "auth_provider": user.auth_provider,
                "nickname": user.nickname,
                "profile_image": user.profile_image,
                "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
            }
