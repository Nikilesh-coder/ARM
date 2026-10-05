"""
ReportForge AI - Local Filesystem Storage Provider
Used for local development, automated testing, and offline execution.
"""

from pathlib import Path
from typing import Optional
from apps.api.services.storage.base import StorageProvider
from apps.api.core.config import settings
from apps.api.core.logging import get_logger

logger = get_logger("storage.local")


class LocalStorageProvider(StorageProvider):
    """Stores files on the local filesystem rooted at settings.storage.local_dir."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.storage.local_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized LocalStorageProvider at {self.base_dir}")

    def _resolve(self, bucket: str, path: str) -> Path:
        clean_path = path.lstrip("/\\")
        target = self.base_dir / bucket / clean_path
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def upload_file(self, bucket: str, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        target = self._resolve(bucket, path)
        target.write_bytes(data)
        logger.debug(f"Saved {len(data)} bytes to {target}")
        return str(target)

    def download_file(self, bucket: str, path: str) -> bytes:
        target = self._resolve(bucket, path)
        if not target.exists():
            raise FileNotFoundError(f"File not found in storage: {bucket}/{path}")
        return target.read_bytes()

    def delete_file(self, bucket: str, path: str) -> bool:
        target = self._resolve(bucket, path)
        if target.exists():
            target.unlink()
            return True
        return False

    def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        return f"/api/v1/storage/{bucket}/{path.lstrip('/')}"

    def exists(self, bucket: str, path: str) -> bool:
        target = self.base_dir / bucket / path.lstrip("/\\")
        return target.exists()
