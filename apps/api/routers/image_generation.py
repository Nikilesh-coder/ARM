"""
ARM Image Generation Health & Management Router
===============================================
Exposes health diagnostic endpoint for local and remote image providers.
Never exposes API tokens or secrets.
"""

from fastapi import APIRouter
from typing import Dict, Any

from apps.api.services.xkiro_image_provider import XKiroImageProvider
from apps.api.services.local_rtx_provider import LocalRTXProvider
from apps.api.services.cloudflare_image_provider import CloudflareImageProvider
from apps.api.services.hf_image_provider import HFImageProvider
from apps.api.services.together_image_provider import TogetherImageProvider
from apps.api.services.image_provider_cooldown import image_provider_health_manager

router = APIRouter(prefix="/image-generation", tags=["Visual Generation"])


@router.get("/health")
def get_image_generation_health() -> Dict[str, Any]:
    """
    Returns runtime readiness and health status across all visual image providers.
    Does NOT leak secrets or credentials.
    """
    xkiro_configured = XKiroImageProvider.is_configured()
    xkiro_available = xkiro_configured and image_provider_health_manager.is_available("xkiro")

    hw_status = LocalRTXProvider.get_hardware_status()
    rtx_enabled = LocalRTXProvider.is_enabled()
    rtx_ready = False

    cf_configured = CloudflareImageProvider.is_configured()
    cf_available = cf_configured and image_provider_health_manager.is_available("cloudflare")

    hf_configured = HFImageProvider.is_configured()
    hf_available = hf_configured and image_provider_health_manager.is_available("huggingface")

    together_configured = TogetherImageProvider.is_configured()
    together_available = together_configured and image_provider_health_manager.is_available("together")

    return {
        "status": "healthy",
        "primary_provider": "xkiro",
        "xkiro": {
            "configured": xkiro_configured,
            "available": xkiro_available,
            "model": "sensenova/sensenova-u1.5-lite",
            "free_only": XKiroImageProvider.is_free_only(),
        },
        "cloudflare": {
            "configured": cf_configured,
            "available": cf_available,
        },
        "local_rtx": {
            "enabled": False,
            "gpu_available": False,
            "ready": False,
        },
        "huggingface": {
            "configured": hf_configured,
            "available": hf_available,
        },
        "together": {
            "configured": together_configured,
            "available": together_available,
        },
    }
