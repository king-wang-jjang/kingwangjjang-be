from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str | None
    auth_provider: str | None
    is_authenticated: bool
