import asyncio
import contextlib
import logging
import os

from app.repositories.boards import BoardRepository


logger = logging.getLogger("board-service")

DEFAULT_ANALYSIS_WORKER_CONCURRENCY = 2
DEFAULT_ANALYSIS_MAX_RETRY_COUNT = 5


def analysis_worker_enabled() -> bool:
    return os.getenv("DISABLE_ANALYSIS_WORKER", "FALSE").upper() != "TRUE"


def analysis_worker_concurrency() -> int:
    # The dedicated summary vLLM is configured for two concurrent sequences.
    # Operators using a smaller node can still override this value.
    raw_value = os.getenv(
        "ANALYSIS_WORKER_CONCURRENCY",
        str(DEFAULT_ANALYSIS_WORKER_CONCURRENCY),
    )
    try:
        return min(max(int(raw_value), 1), 16)
    except ValueError:
        logger.warning(
            "Invalid ANALYSIS_WORKER_CONCURRENCY; using default %s",
            DEFAULT_ANALYSIS_WORKER_CONCURRENCY,
        )
        return DEFAULT_ANALYSIS_WORKER_CONCURRENCY


def analysis_max_retry_count() -> int:
    raw_value = os.getenv(
        "ANALYSIS_MAX_RETRY_COUNT",
        str(DEFAULT_ANALYSIS_MAX_RETRY_COUNT),
    )
    try:
        return min(max(int(raw_value), 1), 20)
    except ValueError:
        logger.warning(
            "Invalid ANALYSIS_MAX_RETRY_COUNT; using default %s",
            DEFAULT_ANALYSIS_MAX_RETRY_COUNT,
        )
        return DEFAULT_ANALYSIS_MAX_RETRY_COUNT


async def run_analysis_worker(stop_event: asyncio.Event) -> None:
    repository = BoardRepository()
    max_retry_count = analysis_max_retry_count()
    idle_interval_seconds = _float_env("ANALYSIS_WORKER_IDLE_INTERVAL_SECONDS", 3.0)
    active_interval_seconds = _float_env("ANALYSIS_WORKER_ACTIVE_INTERVAL_SECONDS", 0.2)

    logger.info("Board analysis worker started")
    while not stop_event.is_set():
        try:
            result = await asyncio.to_thread(
                repository.process_next_analysis_job,
                max_retry_count=max_retry_count,
            )
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
