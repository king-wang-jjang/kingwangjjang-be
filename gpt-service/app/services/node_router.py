import asyncio
import inspect
import logging
import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Generic, TypeVar

from app.adapters import AdapterConfigurationError, AdapterHTTPError, HealthResult
from app.config import Config, is_allowed_api_key_env
from app.repositories.ai_nodes import AINodeRepository, NodeCandidate


T = TypeVar("T")


class NoAvailableNodeError(RuntimeError):
    pass


class NodeRequestFailedError(NoAvailableNodeError):
    pass


class InvalidInferenceRequestError(ValueError):
    pass


logger = logging.getLogger("gpt-service")


@dataclass(frozen=True)
class InvocationResult(Generic[T]):
    value: T
    node_id: str
    node_name: str
    model: str


class AINodeRouter:
    def __init__(
        self,
        repository: AINodeRepository,
        *,
        adapter_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.repository = repository
        self._adapter_factory = adapter_factory or self._default_adapter_factory
        self._inflight: dict[str, int] = defaultdict(int)
        self._concurrency_lock = asyncio.Lock()
        self._weighted_cursor: dict[tuple, int] = defaultdict(int)

    async def invoke(
        self,
        *,
        capability: str,
        messages: list[dict],
        response_format: str | dict | None = None,
        transform: Callable[[str], T] | None = None,
    ) -> InvocationResult[T | str]:
        candidates = self._ordered_candidates(capability)
        if not candidates:
            raise NoAvailableNodeError(f"No enabled AI node supports capability '{capability}'")

        failures: list[str] = []
        request_rejections: list[str] = []
        attempted = False
        attempted_count = 0
        deadline = perf_counter() + Config.request_deadline_seconds()
        for index, candidate in enumerate(candidates):
            remaining_seconds = deadline - perf_counter()
            if remaining_seconds <= 0:
                break
            if not await self._reserve(candidate):
                continue
            attempted = True
            attempted_count += 1
            started = perf_counter()
            adapter = None
            try:
                attempts_left = max(1, len(candidates) - index)
                attempt_timeout = min(
                    candidate.timeout_seconds,
                    max(0.1, remaining_seconds / attempts_left),
                )
                adapter = self._build_adapter(candidate, timeout_seconds=attempt_timeout)
                async with asyncio.timeout(attempt_timeout):
                    result = await adapter.chat(
                        model=candidate.model,
                        messages=messages,
                        response_format=response_format,
                    )
                value = transform(result.content) if transform is not None else result.content
                latency_ms = (perf_counter() - started) * 1000
                self.repository.record_success(candidate.node_id, latency_ms)
                return InvocationResult(
                    value=value,
                    node_id=candidate.node_id,
                    node_name=candidate.node_name,
                    model=candidate.model,
                )
            except AdapterConfigurationError as exc:
                raise InvalidInferenceRequestError("Invalid AI inference request") from exc
            except AdapterHTTPError as exc:
                if exc.status_code in {400, 413, 415, 422}:
                    # A 4xx can be specific to one model/server (for example,
                    # unsupported vision content or response_format). Keep the
                    # node healthy and try another compatible candidate. Only
                    # report a client-facing 422 if every attempted node rejects
                    # the request.
                    error = self._safe_error(exc)
                    request_rejections.append(f"{candidate.node_name}: {error}")
                    logger.info(
                        "AI node rejected an inference request for %s: %s",
                        candidate.node_name,
                        error,
                    )
                    continue
                latency_ms = (perf_counter() - started) * 1000
                error = self._safe_error(exc)
                failures.append(f"{candidate.node_name}: {error}")
                self.repository.record_failure(candidate.node_id, error, latency_ms)
                logger.warning("AI node request failed for %s: %s", candidate.node_name, error)
            except Exception as exc:
                latency_ms = (perf_counter() - started) * 1000
                error = self._safe_error(exc)
                failures.append(f"{candidate.node_name}: {error}")
                self.repository.record_failure(candidate.node_id, error, latency_ms)
                logger.warning("AI node request failed for %s: %s", candidate.node_name, error)
            finally:
                await self._close_adapter(adapter)
                await self._release(candidate)

        if not attempted:
            raise NoAvailableNodeError(
                f"All AI nodes for capability '{capability}' are at max concurrency"
            )
        if attempted_count > 0 and len(request_rejections) == attempted_count:
            if attempted_count == len(candidates):
                raise InvalidInferenceRequestError("AI nodes rejected the inference request")
            raise NoAvailableNodeError(
                "AI nodes rejected the request while other candidates were unavailable"
            )
        detail = "; ".join(failures) or "all candidates failed"
        raise NodeRequestFailedError(
            f"All AI nodes failed for capability '{capability}': {detail}"
        )

    async def health_check(self, node_id: str):
        node = self.repository.get_node(node_id)
        if node is None:
            return None, None
        models = sorted(
            (model for model in node.models if model.enabled),
            key=lambda model: (not model.is_default, model.model_name, model.capability),
        )
        configured_models = sorted({model.model_name for model in models})
        started = perf_counter()
        adapter = None
        try:
            api_key = self._resolve_api_key(node.api_key_env)
            adapter = self._adapter_factory(
                node.provider,
                base_url=node.base_url,
                timeout_seconds=node.timeout_seconds,
                api_key=api_key,
            )
            health = await adapter.health(model=None)
            missing_models = sorted(set(configured_models) - set(health.models))
            if health.healthy and missing_models:
                health = HealthResult(
                    healthy=False,
                    latency_ms=health.latency_ms,
                    error=f"configured models are unavailable: {', '.join(missing_models)}",
                    models=health.models,
                )
            latency_ms = health.latency_ms
            if latency_ms is None:
                latency_ms = (perf_counter() - started) * 1000
            if health.healthy:
                self.repository.record_success(node.id, latency_ms)
            else:
                self.repository.record_failure(
                    node.id,
                    health.error or "AI node health check failed",
                    latency_ms,
                )
        except Exception as exc:
            latency_ms = (perf_counter() - started) * 1000
            error = self._safe_error(exc)
            self.repository.record_failure(node.id, error, latency_ms)
            health = None
        finally:
            await self._close_adapter(adapter)
        return self.repository.get_node(node_id), health

    async def health_check_all(self) -> list[tuple[Any, Any]]:
        node_ids = [node.id for node in self.repository.list_nodes()]
        return list(await asyncio.gather(*(self.health_check(node_id) for node_id in node_ids)))

    def _ordered_candidates(self, capability: str) -> list[NodeCandidate]:
        candidates = self.repository.list_candidates(capability)
        if not candidates:
            return []

        # Degraded nodes and unhealthy nodes whose cooldown has elapsed get one
        # recovery probe before normal healthy/unknown weighted selection.
        probes = [
            item for item in candidates if item.health_status in {"degraded", "unhealthy"}
        ]
        if probes:
            probes.sort(key=lambda item: (item.priority, item.node_name))
            primary = probes[0]
            return [primary, *(item for item in candidates if item.node_id != primary.node_id)]

        health_rank = {"healthy": 0, "unknown": 0}
        candidates.sort(
            key=lambda item: (
                health_rank.get(item.health_status, 3),
                item.priority,
                item.node_name,
            )
        )
        best_health = health_rank.get(candidates[0].health_status, 3)
        best_priority = min(
            item.priority
            for item in candidates
            if health_rank.get(item.health_status, 3) == best_health
        )
        primary_group = [
            item
            for item in candidates
            if health_rank.get(item.health_status, 3) == best_health
            and item.priority == best_priority
        ]

        pool: list[NodeCandidate] = []
        for item in primary_group:
            pool.extend([item] * max(1, min(item.weight, 100)))
        key = (
            capability,
            best_health,
            best_priority,
            tuple((item.node_id, item.weight) for item in primary_group),
        )
        index = self._weighted_cursor[key] % len(pool)
        self._weighted_cursor[key] += 1
        primary = pool[index]
        return [primary, *(item for item in candidates if item.node_id != primary.node_id)]

    async def _reserve(self, candidate: NodeCandidate) -> bool:
        async with self._concurrency_lock:
            effective_limit = (
                1
                if candidate.health_status in {"degraded", "unhealthy"}
                else candidate.max_concurrency
            )
            if self._inflight[candidate.node_id] >= effective_limit:
                return False
            self._inflight[candidate.node_id] += 1
            return True

    async def _release(self, candidate: NodeCandidate) -> None:
        async with self._concurrency_lock:
            self._inflight[candidate.node_id] = max(0, self._inflight[candidate.node_id] - 1)

    def _build_adapter(
        self,
        candidate: NodeCandidate,
        *,
        timeout_seconds: float | None = None,
    ):
        return self._adapter_factory(
            candidate.provider,
            base_url=candidate.base_url,
            timeout_seconds=timeout_seconds or candidate.timeout_seconds,
            api_key=self._resolve_api_key(candidate.api_key_env),
        )

    @staticmethod
    async def _close_adapter(adapter: Any | None) -> None:
        if adapter is None:
            return
        close = getattr(adapter, "aclose", None)
        if close is None:
            return
        try:
            result = close()
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.warning("Failed to close AI adapter client", exc_info=True)

    @staticmethod
    def _resolve_api_key(api_key_env: str | None) -> str | None:
        if api_key_env is None:
            return None
        if not is_allowed_api_key_env(api_key_env):
            raise RuntimeError(f"API key environment reference is not allowed: {api_key_env}")
        value = os.getenv(api_key_env)
        if value is None:
            raise RuntimeError(f"Referenced API key environment variable is not set: {api_key_env}")
        return value

    @staticmethod
    def _default_adapter_factory(provider: str, **kwargs):
        from app.adapters import create_adapter

        return create_adapter(provider, **kwargs)

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        value = str(exc).strip() or exc.__class__.__name__
        return value[:4000]
