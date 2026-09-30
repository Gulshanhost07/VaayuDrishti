
from __future__ import annotations

import hashlib
from functools import lru_cache

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3 import Timeout as Urllib3Timeout
from urllib3.util import Retry

from shared.config import settings
from shared.logging import q, setup_logging

log = setup_logging("minio")

ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_TYPES = ALLOWED_IMAGE | ALLOWED_VIDEO


@lru_cache
def get_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=PoolManager(
            timeout=Urllib3Timeout(connect=5.0, read=60.0),
            retries=Retry(total=2, backoff_factor=0.2),
            maxsize=8,
        ),
    )


def ensure_bucket() -> None:
    client = get_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
        log.info(q(f"created bucket {settings.minio_bucket}"))


def put_bytes(key: str, data: bytes, content_type: str) -> str:
    from io import BytesIO

    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"unsupported media type: {content_type}")
    client = get_client()
    ensure_bucket()
    client.put_object(
        settings.minio_bucket,
        key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def exists(key: str) -> bool:
    client = get_client()
    try:
        client.stat_object(settings.minio_bucket, key)
        return True
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchBucket"):
            return False
        raise


def get_bytes(key: str) -> bytes | None:
    client = get_client()
    try:
        resp = client.get_object(settings.minio_bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchBucket"):
            return None
        raise


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def media_key(prefix: str, content_type: str, data: bytes) -> str:
    ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
    }.get(content_type, "bin")
    return f"{prefix}/{sha256(data)[:16]}.{ext}"
