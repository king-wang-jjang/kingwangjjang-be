import asyncio
import contextlib
import logging
import os

from app.repositories.boards import BoardRepository


logger = logging.getLogger("board-service")


def analysis_worker_enabled() -> bool:
    return os.getenv("DISABLE_ANALYSIS_WORKER", "FALSE").upper() != "TRUE"


def analysis_worker_concurrency() -> int:
    # The default AI node accepts one inference at a time. More workers cause
    # transient 503 responses to consume a board's retry budget during bursts.
    raw_value = os.getenv("ANALYSIS_WORKER_CONCURRENCY", "1")
    try:
        return min(max(int(raw_value), 1), 16)
    except ValueError:
        logger.warning("Invalid ANALYSIS_WORKER_CONCURRENCY; using default 1")
        return 1


async def run_analysis_worker(stop_event: asyncio.Event) -> None:
    repository = BoardRepository()
    idle_interval_seconds = _float_env("ANALYSIS_WORKER_IDLE_INTERVAL_SECONDS", 3.0)
    active_interval_seconds = _float_env("ANALYSIS_WORKER_ACTIVE_INTERVAL_SECONDS", 0.2)

    logger.info("Board analysis worker started")
    while not stop_event.is_set():
        try:
            result = await asyncio.to_thread(repository.process_next_analysis_job)
            wait_seconds = active_interval_seconds if result else idle_interval_seconds
        except Exception as exc:
            logger.exception("Board analysis worker iteration failed: %s", exc)
            wait_seconds = idle_interval_seconds

        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)

    logger.info("Board analysis worker stopped")


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if not raw_value:
        return default

    try:
        return max(float(raw_value), 0.0)
    except ValueError:
        logger.warning("Invalid %s; using default %s", name, default)
        return default
