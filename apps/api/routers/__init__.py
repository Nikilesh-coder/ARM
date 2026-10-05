"""
ReportForge AI Routers
"""

from .health import router as health_router
from .projects import router as projects_router
from .templates import router as templates_router
from .reports import router as reports_router
from .agent import router as agent_router
from .assets import router as assets_router
from .replacement import router as replacement_router
from .integrations import router as integrations_router
from .image_generation import router as image_generation_router

__all__ = [
    "health_router",
    "projects_router",
    "templates_router",
    "reports_router",
    "agent_router",
    "assets_router",
    "replacement_router",
    "integrations_router",
    "image_generation_router",
]


