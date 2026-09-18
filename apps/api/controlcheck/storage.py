"""Storage abstraction for raw project source files.

Supports LocalStorageProvider (default for local development) and S3StorageProvider
(for MinIO / AWS S3 object storage).
"""
import hashlib
import os
import re
from pathlib import Path
from typing import Protocol


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', Path(name).name)
    return cleaned or 'source.bin'


class StorageProvider(Protocol):
    def put(self, project_id: str, filename: str, content: bytes, content_type: str | None = None) -> dict:
        """Stores raw content and returns storage metadata dictionary."""
        ...

    def get(self, storage_key: str) -> bytes:
        """Retrieves raw content by storage key."""
        ...

    def delete(self, storage_key: str) -> None:
        """Deletes raw content by storage key."""
        ...


class LocalStorageProvider:
    def __init__(self, base_dir: str | Path = 'data/storage'):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        target = (self.base_dir / storage_key).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError('Akses path tidak valid (path traversal dicegah).')
        return target

    def put(self, project_id: str, filename: str, content: bytes, content_type: str | None = None) -> dict:
        sha256 = hashlib.sha256(content).hexdigest()
        clean_name = safe_filename(filename)
        safe_pid = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
        storage_key = f"{safe_pid}/{sha256}_{clean_name}"

        target_path = self._resolve_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

        return {
            'storage_key': storage_key,
            'sha256': sha256,
            'size_bytes': len(content),
            'storage_type': 'local',
            'filename': filename,
            'content_type': content_type or 'application/octet-stream'
        }

    def get(self, storage_key: str) -> bytes:
        target_path = self._resolve_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f'File mentah tidak ditemukan: {storage_key}')
        return target_path.read_bytes()

    def delete(self, storage_key: str) -> None:
        target_path = self._resolve_path(storage_key)
        if target_path.is_file():
            target_path.unlink()


class S3StorageProvider:
    def __init__(self, bucket: str, endpoint_url: str | None = None,
                 access_key: str | None = None, secret_key: str | None = None,
                 region: str = 'us-east-1'):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError('boto3 belum terpasang untuk S3StorageProvider.') from exc

        self.bucket = bucket
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_access_key=secret_key,
            region_name=region
        )

    def put(self, project_id: str, filename: str, content: bytes, content_type: str | None = None) -> dict:
        sha256 = hashlib.sha256(content).hexdigest()
        clean_name = safe_filename(filename)
        safe_pid = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
        storage_key = f"{safe_pid}/{sha256}_{clean_name}"
        c_type = content_type or 'application/octet-stream'

        self.client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=content,
            ContentType=c_type,
            Metadata={'sha256': sha256, 'original_filename': filename}
        )

        return {
            'storage_key': storage_key,
            'sha256': sha256,
            'size_bytes': len(content),
            'storage_type': 's3',
            'filename': filename,
            'content_type': c_type
        }

    def get(self, storage_key: str) -> bytes:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=storage_key)
            return resp['Body'].read()
        except Exception as exc:
            raise FileNotFoundError(f'Gagal membaca file dari S3: {storage_key}') from exc

    def delete(self, storage_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_key)
        except Exception:
            pass


def get_storage_provider(base_dir: str | Path | None = None) -> StorageProvider:
    backend = os.environ.get('STORAGE_BACKEND', 'local').lower()
    if backend == 's3' and os.environ.get('S3_BUCKET'):
        return S3StorageProvider(
            bucket=os.environ['S3_BUCKET'],
            endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
            access_key=os.environ.get('AWS_ACCESS_KEY_ID'),
            secret_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
    return LocalStorageProvider(base_dir=base_dir or os.environ.get('LOCAL_STORAGE_DIR', 'data/storage'))
