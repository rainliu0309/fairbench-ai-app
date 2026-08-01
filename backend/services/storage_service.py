import asyncio
import io
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from core.config import settings


class StorageService:
    """Small async facade over the synchronous MinIO client."""

    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    async def ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self.client.bucket_exists, self.bucket)
        if not exists:
            await asyncio.to_thread(self.client.make_bucket, self.bucket)

    async def put_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        await self.ensure_bucket()
        stream = io.BytesIO(data)
        await asyncio.to_thread(
            self.client.put_object,
            self.bucket,
            object_key,
            stream,
            len(data),
            content_type=content_type,
        )

    async def get_bytes(self, object_key: str) -> bytes:
        response = await asyncio.to_thread(
            self.client.get_object, self.bucket, object_key
        )
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

    async def presigned_get_url(self, object_key: str, minutes: int = 15) -> str:
        return await asyncio.to_thread(
            self.client.presigned_get_object,
            self.bucket,
            object_key,
            expires=timedelta(minutes=minutes),
        )

    async def delete_object(self, object_key: str) -> None:
        """Remove an archive object as part of an explicitly authorized purge."""
        try:
            await asyncio.to_thread(self.client.remove_object, self.bucket, object_key)
        except S3Error as exc:
            if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                raise


storage_service = StorageService()
