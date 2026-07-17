import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.postgres import Base  # noqa: E402
from app.repositories.ai_nodes import AINodeRepository  # noqa: E402


@pytest.fixture
def repository() -> AINodeRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return AINodeRepository(factory, engine=engine, create_schema=False)


def create_test_node(
    repository: AINodeRepository,
    *,
    name: str = "node-a",
    base_url: str = "http://node-a.local:11434",
    provider: str = "ollama",
    capabilities: list[str] | None = None,
    model: str = "model-a",
    priority: int = 100,
    weight: int = 1,
    max_concurrency: int = 1,
    health_status: str = "unknown",
    api_key_env: str | None = None,
):
    return repository.create_node(
        {
            "name": name,
            "provider": provider,
            "base_url": base_url,
            "enabled": True,
            "priority": priority,
            "weight": weight,
            "max_concurrency": max_concurrency,
            "timeout_seconds": 5.0,
            "api_key_env": api_key_env,
            "health_status": health_status,
        },
        [
            {
                "name": model,
                "capabilities": capabilities or ["analysis", "chat"],
                "enabled": True,
                "is_default": True,
            }
        ],
    )
