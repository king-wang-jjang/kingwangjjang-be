import os
import secrets

from fastapi import HTTPException, Request, status

from app.config import Config


def _matches(provided: str | None, expected: str) -> bool:
    return provided is not None and secrets.compare_digest(provided, expected)


def require_ai_admin(request: Request) -> None:
    expected = os.getenv("AI_NODE_ADMIN_TOKEN")
    if not expected:
        if Config.is_local_mode():
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI node admin token is not configured",
        )
    if not _matches(request.headers.get("X-AI-Admin-Token"), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AI node admin token",
        )


def require_ai_service(request: Request) -> None:
    expected = os.getenv("AI_SERVICE_TOKEN")
    if not expected:
        if Config.is_local_mode():
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service token is not configured",
        )
    if not _matches(request.headers.get("X-AI-Service-Token"), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AI service token",
        )
