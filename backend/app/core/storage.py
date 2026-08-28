from __future__ import annotations

import asyncio
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


class ObjectStorageError(Exception):
    """Raised when object storage operations fail."""


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    parsed = urlparse(settings.s3_endpoint_url)

    if not parsed.hostname:
        raise ObjectStorageError("Invalid S3 endpoint URL.")

    return Minio(
        endpoint=f"{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}",
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=parsed.scheme == "https",
        region=settings.s3_region,
    )


def ensure_bucket_exists() -> None:
    settings = get_settings()
    client = get_minio_client()

    try:
        if not client.bucket_exists(settings.s3_bucket):
            client.make_bucket(settings.s3_bucket)
    except S3Error as exc:
        raise ObjectStorageError(
            f"Failed to ensure bucket exists: {exc}"
        ) from exc


def put_bytes(
    *,
    object_key: str,
    payload: bytes,
    content_type: str,
) -> str:
    settings = get_settings()
    client = get_minio_client()

    try:
        ensure_bucket_exists()
        client.put_object(
            bucket_name=settings.s3_bucket,
            object_name=object_key,
            data=BytesIO(payload),
            length=len(payload),
            content_type=content_type,
        )
    except S3Error as exc:
        raise ObjectStorageError(
            f"Failed to upload object: {exc}"
        ) from exc

    return object_key


def object_exists(object_key: str) -> bool:
    settings = get_settings()
    client = get_minio_client()

    try:
        client.stat_object(settings.s3_bucket, object_key)
        return True
    except S3Error:
        return False


def get_bytes(object_key: str) -> bytes:
    settings = get_settings()
    client = get_minio_client()

    try:
        response = client.get_object(settings.s3_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as exc:
        raise ObjectStorageError(
            f"Failed to download object: {exc}"
        ) from exc


async def upload_bytes(
    *,
    object_key: str,
    payload: bytes,
    content_type: str,
) -> str:
    return await asyncio.to_thread(
        put_bytes,
        object_key=object_key,
        payload=payload,
        content_type=content_type,
    )


async def download_bytes(object_key: str) -> bytes:
    return await asyncio.to_thread(get_bytes, object_key)


async def ensure_storage_ready() -> None:
    await asyncio.to_thread(ensure_bucket_exists)


def build_bottle_profile_reference_key(profile_id: str) -> str:
    return (
        f"calibration/{profile_id}/reference/"
        f"{uuid4().hex}.jpg"
    )


def build_measurement_original_key(
    *,
    measurement_id: str,
    extension: str,
) -> str:
    return (
        f"measurements/{measurement_id}/"
        f"original.{extension}"
    )


def build_measurement_canonical_key(*, measurement_id: str) -> str:
    return f"measurements/{measurement_id}/canonical.jpg"


def build_measurement_debug_key(*, measurement_id: str) -> str:
    return f"measurements/{measurement_id}/debug.jpg"
