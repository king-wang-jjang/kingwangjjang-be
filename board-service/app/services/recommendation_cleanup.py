import asyncio
import logging

from app.repositories.recommendations import RecommendationRepository

logger = logging.getLogger("board-service")


async def run_recommendation_cleanup(stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            repository = await asyncio.to_thread(RecommendationRepository)
            while not stop_event.is_set() and await asyncio.to_thread(repository.cleanup_expired) == 100:
                await asyncio.sleep(0)
        except Exception:
            logger.exception("Recommendation history cleanup failed; retrying in one hour")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3600)
        except TimeoutError:
            pass
