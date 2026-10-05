"""
ReportForge AI - Storage Provider Abstraction
Interface for object storage (local filesystem, Supabase Storage, S3).
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Abstract base class defining contract for file storage."""

    @abstractmethod
    def upload_file(self, bucket: str, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads binary data to the given bucket and relative path. Returns access URI/path."""
        pass

    @abstractmethod
    def download_file(self, bucket: str, path: str) -> bytes:
        """Downloads file binary bytes from storage."""
        pass

    @abstractmethod
    def delete_file(self, bucket: str, path: str) -> bool:
        """Deletes file at bucket/path."""
        pass

    @abstractmethod
    def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Generates a secure temporary download URL for client access."""
        pass

    @abstractmethod
    def exists(self, bucket: str, path: str) -> bool:
        """Checks if a file exists at the given bucket and path."""
        pass
