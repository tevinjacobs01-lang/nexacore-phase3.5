"""Provider-neutral private object storage for uploads and evidence."""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.file_storage import delete_file, read_file, save_file


@dataclass(frozen=True)
class StoredObject:
    key: str
    provider: str
    bucket: str | None


def _s3_client():
    import boto3
    from botocore.config import Config as BotoConfig

    missing = [
        name for name, value in {
            "STORAGE_BUCKET": settings.STORAGE_BUCKET,
            "STORAGE_REGION": settings.STORAGE_REGION,
            "STORAGE_ACCESS_KEY": settings.STORAGE_ACCESS_KEY,
            "STORAGE_SECRET_KEY": settings.STORAGE_SECRET_KEY,
        }.items() if not value
    ]
    if missing:
        raise RuntimeError(f"S3 storage is not configured: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT,
        region_name=settings.STORAGE_REGION,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
    )


def put_object(file_bytes: bytes, original_filename: str, object_key: str, content_type: str | None = None) -> StoredObject:
    if settings.STORAGE_PROVIDER == "local":
        return StoredObject(save_file(file_bytes, original_filename), "local", None)
    if settings.STORAGE_PROVIDER != "s3":
        raise RuntimeError(f"Unsupported storage provider: {settings.STORAGE_PROVIDER}")
    _s3_client().upload_fileobj(
        io.BytesIO(file_bytes),
        settings.STORAGE_BUCKET,
        object_key,
        ExtraArgs={"ContentType": content_type or "application/octet-stream"},
    )
    return StoredObject(object_key, "s3", settings.STORAGE_BUCKET)


def new_object_key(original_filename: str, prefix: str) -> str:
    extension = Path(original_filename).suffix[:20]
    return f"{prefix}/{uuid.uuid4()}{extension}"


def get_object(key: str, provider: str | None = None, bucket: str | None = None) -> bytes:
    provider = provider or settings.STORAGE_PROVIDER
    if provider == "local":
        return read_file(key)
    response = _s3_client().get_object(Bucket=bucket or settings.STORAGE_BUCKET, Key=key)
    return response["Body"].read()


def remove_object(key: str, provider: str | None = None, bucket: str | None = None) -> None:
    provider = provider or settings.STORAGE_PROVIDER
    if provider == "local":
        delete_file(key)
    else:
        _s3_client().delete_object(Bucket=bucket or settings.STORAGE_BUCKET, Key=key)