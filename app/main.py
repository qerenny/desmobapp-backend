from __future__ import annotations

from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application", extra={"env": settings.app_env})
    yield
    logger.info("Stopping application")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)
app.include_router(api_router)
