"""
ReportForge AI - Storage Service Factory
"""

from apps.api.services.storage.base import StorageProvider
from apps.api.services.storage.local import LocalStorageProvider
from apps.api.services.storage.supabase import SupabaseStorageProvider
from apps.api.core.config import settings


def get_storage_provider() -> StorageProvider:
    """Factory returns configured storage provider."""
    if settings.storage.provider == "supabase" and settings.database.supabase_url:
        return SupabaseStorageProvider()
    return LocalStorageProvider()


__all__ = ["StorageProvider", "LocalStorageProvider", "SupabaseStorageProvider", "get_storage_provider"]
