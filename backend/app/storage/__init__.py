"""Storage interface: local-dev implementation behind S3 config seam."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    size_bytes: int
    content_type: str


class StorageBackend(Protocol):
    def save(self, *, key: str, data: bytes, content_type: str) -> StoredObject: ...
    def read(self, *, key: str) -> bytes: ...
    def delete(self, *, key: str) -> None: ...


class LocalStorageBackend:
    def __init__(self, root: str = ".uploads") -> None:
        import os

        self.root = root
        os.makedirs(root, exist_ok=True)

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        import os

        safe = key.replace("/", "_").replace("\\", "_")
        path = os.path.join(self.root, safe)
        with open(path, "wb") as fh:
            fh.write(data)
        return StoredObject(storage_key=key, size_bytes=len(data), content_type=content_type)

    def delete(self, *, key: str) -> None:
        import os

        try:
            os.remove(os.path.join(self.root, key.replace("/", "_")))
        except FileNotFoundError:
            pass

    def read(self, *, key: str) -> bytes:
        import os

        with open(os.path.join(self.root, key.replace("/", "_").replace("\\", "_")), "rb") as fh:
            return fh.read()


class SupabaseStorageBackend:
    def __init__(self, *, endpoint: str, region: str, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(s3={"addressing_style": "path"}),
        )

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return StoredObject(storage_key=key, size_bytes=len(data), content_type=content_type)

    def read(self, *, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, *, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_storage() -> StorageBackend:
    from app.core.config import get_settings

    settings = get_settings()
    endpoint = settings.SUPABASE_STORAGE_ENDPOINT or settings.S3_ENDPOINT_URL
    region = settings.SUPABASE_STORAGE_REGION or settings.S3_REGION
    access_key = settings.SUPABASE_STORAGE_ACCESS_KEY or settings.S3_ACCESS_KEY
    secret_key = settings.SUPABASE_STORAGE_SECRET_KEY or settings.S3_SECRET_KEY
    bucket = settings.SUPABASE_STORAGE_BUCKET or settings.S3_BUCKET
    if endpoint and access_key and secret_key:
        return SupabaseStorageBackend(endpoint=endpoint, region=region, access_key=access_key, secret_key=secret_key, bucket=bucket)
    if settings.APP_ENV == "production":
        raise RuntimeError("S3 storage is not configured")
    return LocalStorageBackend()
