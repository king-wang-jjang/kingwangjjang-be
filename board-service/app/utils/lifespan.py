from contextlib import asynccontextmanager
import asyncio
import contextlib

from fastapi import FastAPI
from app.utils.loghandler import catch_exception
from app.services.analysis_worker import analysis_worker_enabled, run_analysis_worker
import sys
sys.excepthook = catch_exception
# from db import context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Provides a context manager for managing the lifespan of a FastAPI application.

    Inside the `lifespan` context manager, the `before start` and `before stop`
    comments indicate where the startup and shutdown operations should be
    implemented.
    """
    
    # fx db initialization
    # context.init()
    
    stop_event = asyncio.Event()
    worker_task = None
    if analysis_worker_enabled():
        worker_task = asyncio.create_task(run_analysis_worker(stop_event))

    # before start
    try:
        yield
    finally:
        if worker_task:
            stop_event.set()
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task
    # before stop
