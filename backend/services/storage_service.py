import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from core.config import settings


class StorageService:
    """Async facade for MinIO and managed S3-compatible object stores.

    Boto3 is intentionally used for both providers. This keeps local MinIO
    behavior unchanged while allowing the free production profile to use
    Supabase Storage without introducing provider-specific business logic.
    """

    def __init__(self) -> None:
        addressing_style = "path" if settings.s3_force_path_style else "virtual"
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": addressing_style},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        self.bucket = settings.storage_bucket

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self.client.head_bucket, Bucket=self.bucket)
            return
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = str(error.get("Code", ""))
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            missing = code in {"404", "NoSuchBucket", "NotFound"} or status == 404
            if not missing:
                raise

        if not settings.s3_auto_create_bucket:
            raise RuntimeError(
                f"Object-storage bucket '{self.bucket}' does not exist. "
                "Create it in the storage provider before uploading files."
            )
        await asyncio.to_thread(self.client.create_bucket, Bucket=self.bucket)

    async def put_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        await self.ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )

    async def get_bytes(self, object_key: str) -> bytes:
        response = await asyncio.to_thread(
            self.client.get_object, Bucket=self.bucket, Key=object_key
        )
        body = response["Body"]
        try:
            return await asyncio.to_thread(body.read)
        finally:
            body.close()

    async def presigned_get_url(self, object_key: str, minutes: int = 15) -> str:
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=minutes * 60,
        )

    async def delete_object(self, object_key: str) -> None:
        """Remove an archive object as part of an explicitly authorized purge."""
        try:
            await asyncio.to_thread(
                self.client.delete_object, Bucket=self.bucket, Key=object_key
            )
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchKey", "NoSuchObject", "NotFound"}:
                raise


storage_service = StorageService()
