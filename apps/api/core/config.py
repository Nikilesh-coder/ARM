"""
ReportForge AI - Core Configuration
Centralized configuration management with environment variable validation.
"""

import os
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Locate workspace root and .env file
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = WORKSPACE_ROOT / ".env"
load_dotenv(ENV_FILE, override=True)


class StorageSettings(BaseModel):
    provider: str = os.getenv("STORAGE_PROVIDER", "local")  # 'local' or 'supabase'
    local_dir: str = str(WORKSPACE_ROOT / ".storage")
    bucket_templates: str = os.getenv("STORAGE_BUCKET_TEMPLATES", "templates")
    bucket_evidence: str = os.getenv("STORAGE_BUCKET_EVIDENCE", "evidence")
    bucket_reports: str = os.getenv("STORAGE_BUCKET_REPORTS", "reports")
    docx_max_file_size_mb: int = int(os.getenv("DOCX_MAX_FILE_SIZE_MB", "25"))
    evidence_max_file_size_mb: int = int(os.getenv("EVIDENCE_MAX_FILE_SIZE_MB", "50"))


class AISettings(BaseModel):
    default_provider: str = os.getenv("DEFAULT_AI_PROVIDER", "gemini")  # 'gemini', 'openai', 'anthropic', 'mock'
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    default_model: str = os.getenv("DEFAULT_AI_MODEL", "gemini-1.5-flash")
    timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))


class DatabaseSettings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/reportforge")
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL", None)
    supabase_anon_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY", None)
    supabase_service_role_key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY", None)


class DocumentProviderSettings(BaseModel):
    default_provider: str = os.getenv("DOCUMENT_PROVIDER", "internal")  # 'internal' or 'carbone'
    carbone_api_key: Optional[str] = os.getenv("CARBONE_API_KEY", None)
    carbone_api_url: str = os.getenv("CARBONE_API_URL", "https://api.carbone.io")
    carbone_version: str = os.getenv("CARBONE_VERSION", "4")
    fallback_to_internal: bool = os.getenv("DOCUMENT_FALLBACK_TO_INTERNAL", "true").lower() in ("true", "1", "yes")


class ImageProviderSettings(BaseModel):
    default_provider: str = os.getenv("DEFAULT_IMAGE_PROVIDER", "xkiro")  # 'xkiro', 'cloudflare', 'huggingface', 'native'
    xkiro_api_key: Optional[str] = os.getenv("XKIRO_API_KEY", None)
    xkiro_model: str = os.getenv("XKIRO_MODEL", "sensenova/sensenova-u1.5-lite")
    xkiro_free_only: bool = os.getenv("XKIRO_FREE_ONLY", "true").lower() in ("true", "1", "yes")
    unsplash_access_key: Optional[str] = os.getenv("UNSPLASH_ACCESS_KEY", None)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    stability_api_key: Optional[str] = os.getenv("STABILITY_API_KEY", None)
    hf_token: Optional[str] = os.getenv("HF_TOKEN", None)
    hf_image_model: str = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    cloudflare_account_id: Optional[str] = os.getenv("CLOUDFLARE_ACCOUNT_ID", None)
    cloudflare_api_token: Optional[str] = os.getenv("CLOUDFLARE_API_TOKEN", None)
    cloudflare_image_model: str = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    fallback_to_native: bool = os.getenv("IMAGE_FALLBACK_TO_NATIVE", "true").lower() in ("true", "1", "yes")


class CanvaSettings(BaseModel):
    enabled: bool = os.getenv("CANVA_ENABLED", "false").lower() in ("true", "1", "yes")
    client_id: Optional[str] = os.getenv("CANVA_CLIENT_ID", None)
    client_secret: Optional[str] = os.getenv("CANVA_CLIENT_SECRET", None)
    api_key: Optional[str] = os.getenv("CANVA_API_KEY", None)
    redirect_uri: str = os.getenv("CANVA_REDIRECT_URI", "http://localhost:3000/app/integrations/canva/callback")


class PdfConverterSettings(BaseModel):
    provider: str = os.getenv("PDF_CONVERTER_PROVIDER", "cloudconvert")  # 'cloudconvert' or 'internal'
    cloudconvert_api_key: Optional[str] = os.getenv("CLOUDCONVERT_API_KEY", None)


class AppSettings(BaseModel):
    project_name: str = os.getenv("PROJECT_NAME", "ReportForge AI")
    environment: str = os.getenv("ENVIRONMENT", "development")  # 'development', 'staging', 'production'
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    api_v1_str: str = os.getenv("API_V1_STR", "/api/v1")
    secret_key: str = os.getenv("SECRET_KEY", "dev_secret_key_reportforge_2026_placeholder")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    frontend_url: Optional[str] = os.getenv("FRONTEND_URL", None)
    cors_origins: List[str] = Field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.environment == "production" and "placeholder" in self.secret_key:
            import secrets
            self.secret_key = secrets.token_hex(32)

        # Build dynamic, deduplicated CORS origins
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]

        # Add FRONTEND_URL (e.g. https://arm-frontend.vercel.app)
        frontend_url_env = os.getenv("FRONTEND_URL", "").strip()
        if frontend_url_env:
            for u in frontend_url_env.split(","):
                u_clean = u.strip().rstrip("/")
                if u_clean and u_clean not in origins:
                    origins.append(u_clean)

        # Add CORS_ORIGINS / BACKEND_CORS_ORIGINS
        custom_origins = os.getenv("CORS_ORIGINS") or os.getenv("BACKEND_CORS_ORIGINS")
        if custom_origins:
            custom_origins = custom_origins.strip()
            if custom_origins.startswith("[") and custom_origins.endswith("]"):
                try:
                    import json
                    parsed = json.loads(custom_origins)
                    if isinstance(parsed, list):
                        for item in parsed:
                            item_clean = str(item).strip().rstrip("/")
                            if item_clean and item_clean not in origins:
                                origins.append(item_clean)
                except Exception:
                    pass
            else:
                for item in custom_origins.split(","):
                    item_clean = item.strip().rstrip("/")
                    if item_clean and item_clean not in origins:
                        origins.append(item_clean)

        self.cors_origins = origins

    storage: StorageSettings = Field(default_factory=StorageSettings)
    ai: AISettings = Field(default_factory=AISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    document_provider: DocumentProviderSettings = Field(default_factory=DocumentProviderSettings)
    image_provider: ImageProviderSettings = Field(default_factory=ImageProviderSettings)
    canva: CanvaSettings = Field(default_factory=CanvaSettings)
    pdf_converter: PdfConverterSettings = Field(default_factory=PdfConverterSettings)


settings = AppSettings()


