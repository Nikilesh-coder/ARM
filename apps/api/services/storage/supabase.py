from typing import Optional
from apps.api.services.storage.base import StorageProvider
from apps.api.core.config import settings
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger

logger = get_logger("storage.supabase")


class SupabaseStorageProvider(StorageProvider):
    """Integrates with Supabase Storage."""

    def __init__(self):
        self.url = settings.database.supabase_url
        self.key = settings.database.supabase_service_role_key or settings.database.supabase_anon_key
        logger.info(f"Initialized SupabaseStorageProvider (URL: {self.url or 'unset'})")

    @property
    def client(self):
        return db_manager.client

    def upload_file(self, bucket: str, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        clean_path = path.lstrip("/")
        if self.client:
            try:
                self.client.storage.from_(bucket).upload(
                    clean_path,
                    data,
                    file_options={"content-type": content_type, "upsert": "true"}
                )
                logger.info(f"Uploaded {len(data)} bytes to Supabase storage bucket '{bucket}' at path '{clean_path}'")
                return f"{self.url}/storage/v1/object/public/{bucket}/{clean_path}"
            except Exception as e:
                logger.error(f"Supabase upload error for {bucket}/{clean_path}: {e}")
                raise
        raise RuntimeError("Supabase client is not initialized.")

    def download_file(self, bucket: str, path: str) -> bytes:
        clean_path = path.lstrip("/")
        if self.client:
            try:
                data = self.client.storage.from_(bucket).download(clean_path)
                logger.info(f"Downloaded {len(data)} bytes from Supabase storage bucket '{bucket}' at path '{clean_path}'")
                return data
            except Exception as e:
                logger.error(f"Supabase download error for {bucket}/{clean_path}: {e}")
                raise FileNotFoundError(f"File not found in storage: {bucket}/{clean_path}") from e
        raise RuntimeError("Supabase client is not initialized.")

    def delete_file(self, bucket: str, path: str) -> bool:
        clean_path = path.lstrip("/")
        if self.client:
            try:
                self.client.storage.from_(bucket).remove([clean_path])
                logger.info(f"Deleted from Supabase storage bucket '{bucket}' at path '{clean_path}'")
                return True
            except Exception as e:
                logger.warning(f"Supabase delete error for {bucket}/{clean_path}: {e}")
                return False
        return False

    def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        clean_path = path.lstrip("/")
        if self.client:
            try:
                res = self.client.storage.from_(bucket).create_signed_url(clean_path, expires_in)
                if isinstance(res, dict) and "signedURL" in res:
                    return res["signedURL"]
                if hasattr(res, "signed_url"):
                    return res.signed_url
            except Exception as e:
                logger.warning(f"Error generating signed URL: {e}")
        return f"{self.url}/storage/v1/object/sign/{bucket}/{clean_path}?token=mock_signed_token"

    def exists(self, bucket: str, path: str) -> bool:
        clean_path = path.lstrip("/")
        if self.client:
            try:
                parts = clean_path.rsplit("/", 1)
                folder = parts[0] if len(parts) > 1 else ""
                filename = parts[-1]
                files = self.client.storage.from_(bucket).list(folder)
                return any(f.get("name") == filename for f in files)
            except Exception:
                return False
        return False
