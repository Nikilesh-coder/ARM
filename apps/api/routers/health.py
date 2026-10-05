"""
ReportForge AI - Health Router
Provides detailed subsystem readiness status.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from apps.api.core.config import settings
from apps.api.core.database import db_manager
from apps.api.services.storage import get_storage_provider
from apps.api.services.ai import get_ai_provider

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def detailed_health_check():
    ai = get_ai_provider()
    storage = get_storage_provider()
    db = db_manager.check_health()

    return {
        "status": "healthy",
        "service": "reportforge-api",
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "database": db,
            "storage": {
                "provider": storage.__class__.__name__,
                "configured": True
            },
            "ai": {
                "provider": ai.__class__.__name__,
                "configured": ai.is_configured()
            }
        }
    }
