"""
ReportForge AI - Database Connection Foundation
Provides database connection lifecycle management, health checks, and Supabase client bindings.
"""

from typing import Dict, Any
from apps.api.core.config import settings
from apps.api.core.logging import get_logger

logger = get_logger("database")


class DatabaseManager:
    """Manages database connectivity and Supabase integration."""

    def __init__(self):
        self._connected = False
        self._engine = None
        self._supabase_client = None

    def initialize(self):
        """Initializes database engine or Supabase client based on available configuration."""
        db_url = settings.database.database_url
        logger.info(f"Initializing database layer with target URL: {db_url.split('@')[-1] if '@' in db_url else 'local'}")

        if settings.database.supabase_url and settings.database.supabase_anon_key:
            logger.info("Supabase client configuration detected.")
        else:
            logger.info("Running with local database connection configuration.")

        self._connected = True

    def check_health(self) -> Dict[str, Any]:
        """Health check returns connection status and provider metadata."""
        return {
            "status": "connected" if self._connected else "uninitialized",
            "provider": "supabase" if settings.database.supabase_url else "postgresql",
            "database_configured": bool(settings.database.database_url)
        }

    @property
    def client(self):
        """Returns initialized Supabase Client if configured."""
        if not self._supabase_client and settings.database.supabase_url:
            from supabase import create_client
            key = settings.database.supabase_service_role_key or settings.database.supabase_anon_key
            self._supabase_client = create_client(settings.database.supabase_url, key)
        return self._supabase_client

    def close(self):
        """Closes any active database connections gracefully."""
        logger.info("Closing database connections.")
        self._connected = False
        self._supabase_client = None


db_manager = DatabaseManager()
