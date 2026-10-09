"""
ReportForge AI - FastAPI Application Entry Point
"""

import sys
from pathlib import Path

# Ensure stdout and stderr use UTF-8 on Windows to safely handle Unicode ligatures and special characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure root workspace is in sys.path so packages.* and apps.* resolve cleanly
WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from apps.api.core.config import settings  # noqa: E402
from apps.api.core.logging import setup_logging, get_logger  # noqa: E402
from apps.api.core.exceptions import setup_exception_handlers  # noqa: E402
from apps.api.core.database import db_manager  # noqa: E402
from apps.api.routers import (  # noqa: E402
    health_router,
    projects_router,
    templates_router,
    reports_router,
    agent_router,
    assets_router,
    replacement_router,
    integrations_router,
    image_generation_router,
    auth_router,
)


# Initialize structured logging
setup_logging()
logger = get_logger("main")

# Initialize database foundation
db_manager.initialize()

# Initialize canonical report file storage foundation
from apps.api.services.report_file_storage_service import ReportFileStorageService  # noqa: E402
ReportFileStorageService.initialize()

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Deterministic Academic Document Synthesis & AI Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def on_app_startup():
    ReportFileStorageService.initialize()

# Register global exception handlers
setup_exception_handlers(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https://arm-caw2(-[a-z0-9-]+)?\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Required Health Endpoint: GET /health -> {"status": "healthy"}
@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# Mount API V1 Routers
app.include_router(health_router, prefix=settings.api_v1_str)
app.include_router(projects_router, prefix=settings.api_v1_str)
app.include_router(templates_router, prefix=settings.api_v1_str)
app.include_router(reports_router, prefix=settings.api_v1_str)
app.include_router(agent_router, prefix=settings.api_v1_str)
app.include_router(assets_router, prefix=settings.api_v1_str)
app.include_router(replacement_router, prefix=settings.api_v1_str)
app.include_router(integrations_router, prefix=settings.api_v1_str)
app.include_router(image_generation_router, prefix=settings.api_v1_str)
app.include_router(auth_router, prefix=settings.api_v1_str)



@app.get("/", tags=["Root"])
def root():
    return {
        "name": settings.project_name,
        "status": "operational",
        "documentation": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=True)
