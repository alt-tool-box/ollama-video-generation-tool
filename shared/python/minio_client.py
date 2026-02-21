from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import io
import os
import sys
from pathlib import Path

# Handle both relative and absolute imports
try:
    from .config import config
except ImportError:
    from config import config


class MinioClient:
    def __init__(self):
        self.client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE
        )
        self.bucket = config.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"MinIO bucket error: {e}")
    
    def upload_file(self, file_path: str, object_name: str, content_type: str = "application/octet-stream") -> str:
        self.client.fput_object(self.bucket, object_name, file_path, content_type=content_type)
        return object_name
    
    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        return object_name
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            expires=timedelta(seconds=expires)
        )
    
    def get_presigned_upload_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.presigned_put_object(
            self.bucket,
            object_name,
            expires=timedelta(seconds=expires)
        )
    
    def download_file(self, object_name: str, file_path: str):
        self.client.fget_object(self.bucket, object_name, file_path)
    
    def get_object_bytes(self, object_name: str) -> bytes:
        response = self.client.get_object(self.bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    
    def delete_object(self, object_name: str):
        self.client.remove_object(self.bucket, object_name)
    
    def list_objects(self, prefix: str = "") -> list:
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]


minio_client = MinioClient()
