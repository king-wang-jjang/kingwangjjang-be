from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Engine, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.config import Config
from app.db.models import AINode, AINodeModel
from app.db.postgres import Base, get_session_factory


SUPPORTED_PROVIDERS = {"ollama", "openai_compatible"}
SUPPORTED_CAPABILITIES = {"analysis", "chat", "vision"}


@dataclass(frozen=True)
class NodeCandidate:
    node_id: str
    node_name: str
    provider: str
    base_url: str
    model: str
    capability: str
    priority: int
    weight: int
    max_concurrency: int
    timeout_seconds: float
    api_key_env: str | None
    health_status: str
    is_default: bool


class AINodeRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        engine: Engine | None = None,
        create_schema: bool = True,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        bind = engine or self._session_factory.kw.get("bind")
        if create_schema:
            if bind is None:
                raise RuntimeError("A database engine is required")
            Base.metadata.create_all(bind=bind)

    def count_nodes(self) -> int:
        with self._session_factory() as session:
            return int(session.scalar(select(func.count(AINode.id))) or 0)

    def list_nodes(self) -> list[AINode]:
        with self._session_factory() as session:
            statement = (
                select(AINode)
                .options(selectinload(AINode.models))
                .order_by(AINode.priority, AINode.name)
            )
            return list(session.scalars(statement).all())

    def get_node(self, node_id: str) -> AINode | None:
        with self._session_factory() as session:
            return session.scalar(
                select(AINode)
                .where(AINode.id == node_id)
                .options(selectinload(AINode.models))
            )

    def synchronize_named_node(
        self,
        values: dict[str, Any],
        models: list[dict[str, Any]],
    ) -> bool:
        """Create or update one environment-managed node by its stable name."""
        self._validate_node_values(values)
        name = str(values.get("name") or "").strip()
        if not name:
            raise ValueError("node name is required")
        model_rows = self._model_rows(models)

        with self._session_factory() as session:
            node = session.scalar(
                select(AINode)
                .where(AINode.name == name)
                .options(selectinload(AINode.models))
            )
            if node is None:
                node = AINode(**values)
                node.models = [AINodeModel(**row) for row in model_rows]
                session.add(node)
                changed = True
            else:
                changed = False
                for field in (
                    "provider",
                    "base_url",
                    "enabled",
                    "priority",
                    "weight",
                    "max_concurrency",
                    "timeout_seconds",
                    "api_key_env",
                ):
                    desired = values.get(field)
                    if getattr(node, field) != desired:
                        setattr(node, field, desired)
                        changed = True

                current_models = sorted(
                    (
                        item.model_name,
                        item.capability,
                        item.enabled,
                        item.is_default,
                    )
                    for item in node.models
                )
                desired_models = sorted(
                    (
                        item["model_name"],
                        item["capability"],
                        item["enabled"],
                        item["is_default"],
                    )
                    for item in model_rows
                )
                if current_models != desired_models:
                    node.models.clear()
                    session.flush()
                    node.models = [AINodeModel(**row) for row in model_rows]
                    changed = True

                if changed:
                    node.health_status = "unknown"
                    node.consecutive_failures = 0
                    node.last_latency_ms = None
                    node.last_error = None
                    node.last_checked_at = None
                    node.updated_at = datetime.now(timezone.utc)

            if not changed:
                return False
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("AI node name or provider/base_url already exists") from exc
            return True

    def create_node(self, values: dict[str, Any], models: list[dict[str, Any]]) -> AINode:
        self._validate_node_values(values)
        model_rows = self._model_rows(models)
        with self._session_factory() as session:
            node = AINode(**values)
            node.models = [AINodeModel(**row) for row in model_rows]
            session.add(node)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("AI node name or provider/base_url already exists") from exc
            session.refresh(node)
            return self.get_node(node.id)  # type: ignore[return-value]

    def update_node(
        self,
        node_id: str,
        values: dict[str, Any],
        models: list[dict[str, Any]] | None = None,
    ) -> AINode | None:
        self._validate_node_values(values, partial=True)
        model_rows = self._model_rows(models) if models is not None else None
        with self._session_factory() as session:
            node = session.scalar(
                select(AINode)
                .where(AINode.id == node_id)
                .options(selectinload(AINode.models))
            )
            if node is None:
                return None
            for key, value in values.items():
                setattr(node, key, value)
            if model_rows is not None:
                node.models.clear()
                session.flush()
                node.models = [AINodeModel(**row) for row in model_rows]
            node.updated_at = datetime.now(timezone.utc)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("AI node name or provider/base_url already exists") from exc
        return self.get_node(node_id)

    def delete_node(self, node_id: str) -> bool:
        with self._session_factory() as session:
            node = session.get(AINode, node_id)
            if node is None:
                return False
            session.delete(node)
            session.commit()
            return True

    def list_candidates(self, capability: str) -> list[NodeCandidate]:
        if capability not in SUPPORTED_CAPABILITIES:
            raise ValueError(f"Unsupported capability: {capability}")
        retry_before = datetime.now(timezone.utc) - timedelta(
            seconds=Config.retry_cooldown_seconds()
        )
        with self._session_factory() as session:
            statement = (
                select(AINode, AINodeModel)
                .join(AINodeModel, AINodeModel.node_id == AINode.id)
                .where(
                    AINode.enabled.is_(True),
                    or_(
                        AINode.health_status != "unhealthy",
                        AINode.last_checked_at.is_(None),
                        AINode.last_checked_at <= retry_before,
                    ),
                    AINodeModel.enabled.is_(True),
                    AINodeModel.capability == capability,
                )
                .order_by(
                    AINode.priority,
                    AINode.name,
                    AINodeModel.is_default.desc(),
                    AINodeModel.model_name,
                )
            )
            rows = session.execute(statement).all()

        candidates: list[NodeCandidate] = []
        seen_nodes: set[str] = set()
        for node, model in rows:
            if node.id in seen_nodes:
                continue
            seen_nodes.add(node.id)
            candidates.append(
                NodeCandidate(
                    node_id=node.id,
                    node_name=node.name,
                    provider=node.provider,
                    base_url=node.base_url,
                    model=model.model_name,
                    capability=model.capability,
                    priority=node.priority,
                    weight=node.weight,
                    max_concurrency=node.max_concurrency,
                    timeout_seconds=node.timeout_seconds,
                    api_key_env=node.api_key_env,
                    health_status=node.health_status,
                    is_default=model.is_default,
                )
            )
        return candidates

    def record_success(self, node_id: str, latency_ms: float) -> None:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            session.execute(
                update(AINode)
                .where(AINode.id == node_id)
                .values(
                    health_status="healthy",
                    consecutive_failures=0,
                    last_latency_ms=latency_ms,
                    last_error=None,
                    last_checked_at=now,
                    last_success_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def record_failure(self, node_id: str, error: str, latency_ms: float | None = None) -> None:
        now = datetime.now(timezone.utc)
        threshold = Config.failure_threshold()
        next_failure_count = AINode.consecutive_failures + 1
        with self._session_factory() as session:
            session.execute(
                update(AINode)
                .where(AINode.id == node_id)
                .values(
                    consecutive_failures=next_failure_count,
                    health_status=case(
                        (next_failure_count >= threshold, "unhealthy"),
                        else_="degraded",
                    ),
                    last_latency_ms=latency_ms,
                    last_error=error[:4000],
                    last_checked_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def bootstrap_if_empty(self, nodes: list[dict[str, Any]]) -> int:
        if not nodes:
            return 0
        with self._session_factory() as session:
            if int(session.scalar(select(func.count(AINode.id))) or 0) != 0:
                return 0
            for definition in nodes:
                values = dict(definition["values"])
                models = self._model_rows(definition["models"])
                self._validate_node_values(values)
                node = AINode(**values)
                node.models = [AINodeModel(**row) for row in models]
                session.add(node)
            try:
                session.commit()
            except IntegrityError:
                # A second process may have completed the same one-time bootstrap.
                session.rollback()
                return 0
            return len(nodes)

    @staticmethod
    def _validate_node_values(values: dict[str, Any], partial: bool = False) -> None:
        provider = values.get("provider")
        if provider is not None and provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        if not partial and provider is None:
            raise ValueError("provider is required")
        for field in ("weight", "max_concurrency"):
            if field in values and int(values[field]) < 1:
                raise ValueError(f"{field} must be at least 1")
        if "timeout_seconds" in values and float(values["timeout_seconds"]) <= 0:
            raise ValueError("timeout_seconds must be greater than 0")

    @staticmethod
    def _model_rows(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for model in models:
            name = str(model["name"]).strip()
            if not name:
                raise ValueError("model name is required")
            capabilities = model.get("capabilities") or []
            for capability in capabilities:
                if capability not in SUPPORTED_CAPABILITIES:
                    raise ValueError(f"Unsupported capability: {capability}")
                key = (name, capability)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "model_name": name,
                        "capability": capability,
                        "enabled": bool(model.get("enabled", True)),
                        "is_default": bool(model.get("is_default", False)),
                    }
                )
        if not rows:
            raise ValueError("At least one model capability is required")
        return rows
