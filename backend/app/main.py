from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.storage import ObjectStorageError, ensure_storage_ready


configure_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s version %s",
        settings.app_name,
        settings.app_version,
    )

    try:
        await ensure_storage_ready()
        logger.info("Object storage bucket is ready.")
    except ObjectStorageError:
        logger.exception(
            "Object storage is not ready; continuing startup."
        )

    yield

    logger.info(
        "Stopping %s",
        settings.app_name,
    )


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)
