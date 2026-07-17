import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.config import Config
from app.db.bootstrap import bootstrap_legacy_nodes
from app.repositories.ai_nodes import AINodeRepository
from app.routes.dependencies import get_node_repository
from app.routes.inference import router as inference_router
from app.routes.nodes import router as nodes_router
from app.services.node_router import AINodeRouter


logger = logging.getLogger("gpt-service")


async def _initialize_repository() -> AINodeRepository:
    attempts = Config.database_startup_attempts()
    for attempt in range(1, attempts + 1):
        try:
            repository = AINodeRepository()
            bootstrap_legacy_nodes(repository)
            return repository
        except Exception:
            if attempt == attempts:
                raise
            logger.warning(
                "AI database is not ready (attempt %s/%s); retrying",
                attempt,
                attempts,
            )
            await asyncio.sleep(Config.database_startup_delay_seconds())
    raise RuntimeError("AI database initialization failed")


def create_app(
    *,
    repository: AINodeRepository | None = None,
    node_router: AINodeRouter | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if repository is None:
            active_repository = await _initialize_repository()
        else:
            active_repository = repository
            bootstrap_legacy_nodes(active_repository)
        app.state.ai_node_repository = active_repository
        app.state.ai_node_router = node_router or AINodeRouter(active_repository)
        yield

    application = FastAPI(
        title="Kingwangjjang AI Node Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["health"])
    def health(active_repository: AINodeRepository = Depends(get_node_repository)):
        return {"status": "ok", "node_count": active_repository.count_nodes()}

    application.include_router(nodes_router)
    application.include_router(inference_router)
    return application


app = create_app()
