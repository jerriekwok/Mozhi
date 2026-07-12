import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.model_runtime import ModelRuntimeError, preload_models, unload_models


logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """Warm local models at startup and release them when the API exits."""
    try:
        await run_in_threadpool(preload_models)
        logger.info("[model] Preloaded %s", settings.VISION_MODEL)
    except ModelRuntimeError as exc:
        logger.warning("[model] Preload skipped: %s", exc)

    try:
        yield
    finally:
        await run_in_threadpool(unload_models)
