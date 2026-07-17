from fastapi import Request

from app.repositories.ai_nodes import AINodeRepository
from app.services.node_router import AINodeRouter


def get_node_repository(request: Request) -> AINodeRepository:
    return request.app.state.ai_node_repository


def get_node_router(request: Request) -> AINodeRouter:
    return request.app.state.ai_node_router
