"""S3-compatible object storage via aioboto3."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings, get_settings
from app.core.exceptions import NotFoundError, StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService(Protocol):
    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str: ...
    async def get_object(self, key: str) -> bytes: ...
    async def delete_object(self, key: str) -> None: ...


class ObjectStorage:
    """Async MinIO/S3 object storage client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._session = None
        self._bucket_ready = False

    def _get_session(self):
        if self._session is None:
            import aioboto3

            self._session = aioboto3.Session()
        return self._session

    def _client_kwargs(self) -> dict:
        return {
            "endpoint_url": self._settings.s3_endpoint,
            "aws_access_key_id": self._settings.s3_access_key,
            "aws_secret_access_key": self._settings.s3_secret_key,
            "region_name": self._settings.s3_region,
            "use_ssl": self._settings.s3_use_ssl,
            "config": Config(signature_version="s3v4", retries={"max_attempts": 3}),
        }

    @asynccontextmanager
    async def _client(self) -> AsyncIterator:
        session = self._get_session()
        async with session.client("s3", **self._client_kwargs()) as client:
            yield client

    async def ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        async with self._client() as client:
            try:
                await client.head_bucket(Bucket=self._settings.s3_bucket)
            except ClientError:
                try:
                    await client.create_bucket(Bucket=self._settings.s3_bucket)
                    logger.info("s3_bucket_created", bucket=self._settings.s3_bucket)
                except ClientError as exc:
                    raise StorageError(f"Failed to create bucket: {exc}") from exc
        self._bucket_ready = True

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        await self.ensure_bucket()
        extra_args: dict = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata
        try:
            async with self._client() as client:
                await client.put_object(
                    Bucket=self._settings.s3_bucket,
                    Key=key,
                    Body=data,
                    **extra_args,
                )
            return key
        except ClientError as exc:
            raise StorageError(f"Upload failed for {key}: {exc}") from exc

    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str:
        return await self.upload_bytes(key, data, content_type=content_type)

    async def download_bytes(self, key: str) -> bytes:
        try:
            async with self._client() as client:
                response = await client.get_object(Bucket=self._settings.s3_bucket, Key=key)
                body = await response["Body"].read()
            return body
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise NotFoundError(f"Object not found: {key}") from exc
            raise StorageError(f"Download failed for {key}: {exc}") from exc

    async def get_object(self, key: str) -> bytes:
        return await self.download_bytes(key)

    async def delete_object(self, key: str) -> None:
        try:
            async with self._client() as client:
                await client.delete_object(Bucket=self._settings.s3_bucket, Key=key)
        except ClientError as exc:
            raise StorageError(f"Delete failed for {key}: {exc}") from exc

    async def object_exists(self, key: str) -> bool:
        try:
            async with self._client() as client:
                await client.head_object(Bucket=self._settings.s3_bucket, Key=key)
            return True
        except ClientError:
            return False

    async def generate_presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        try:
            async with self._client() as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._settings.s3_bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
            return url
        except ClientError as exc:
            raise StorageError(f"Presign failed for {key}: {exc}") from exc


class MemoryStorage:
    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str]] = {}

    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str:
        self._store[key] = (data, content_type)
        return key

    async def get_object(self, key: str) -> bytes:
        if key not in self._store:
            raise FileNotFoundError(f"Object not found: {key}")
        return self._store[key][0]

    async def delete_object(self, key: str) -> None:
        self._store.pop(key, None)


_storage_instance: ObjectStorage | MemoryStorage | None = None


def get_object_storage() -> ObjectStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ObjectStorage()
    return _storage_instance  # type: ignore[return-value]


def get_storage() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MemoryStorage()
    return _storage_instance


async def init_storage() -> None:
    global _storage_instance
    try:
        storage = ObjectStorage()
        await storage.ensure_bucket()
        _storage_instance = storage
        logger.info("s3_storage_initialized")
    except Exception as exc:
        logger.warning("s3_unavailable_using_memory", error=str(exc))
        _storage_instance = MemoryStorage()
