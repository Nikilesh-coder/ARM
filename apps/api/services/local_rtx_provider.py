"""
ARM Local RTX Provider (Disabled / Safety Stub)
==============================================
GPU / RTX image generation is explicitly disabled per ARM specification.
Primary Provider: xKiro (sensenova/sensenova-u1.5-lite)
Fallback Provider: Cloudflare Worker
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LocalRTXGenerationResult:
    """Standardized result container for Local RTX generation."""

    def __init__(
        self,
        success: bool = False,
        image_bytes: Optional[bytes] = None,
        sha256: str = "",
        model_name: str = "none",
        status: str = "DISABLED",
        error: Optional[str] = "Local RTX generation is disabled",
        latency_seconds: float = 0.0,
    ):
        self.success = success
        self.image_bytes = image_bytes
        self.sha256 = sha256
        self.model_name = model_name
        self.status = status
        self.error = error
        self.latency_seconds = latency_seconds


class LocalRTXProvider:
    """Stub provider ensuring GPU/RTX is never invoked."""

    PROVIDER_NAME = "local_rtx"

    @classmethod
    def is_enabled(cls) -> bool:
        # Strictly disabled per ARM specification
        return False

    @classmethod
    def get_hardware_status(cls) -> Dict[str, Any]:
        return {
            "gpu_detected": False,
            "gpu_name": "None (Disabled)",
            "cuda_available": False,
            "diffusers_installed": False,
            "model_ready": False,
        }

    @classmethod
    def generate_image(cls, *args, **kwargs) -> LocalRTXGenerationResult:
        logger.info("[ARM LOCAL RTX] Generation skipped (GPU/RTX is disabled).")
        return LocalRTXGenerationResult(
            success=False,
            status="DISABLED",
            error="Local RTX generation is disabled in favor of xKiro primary provider.",
        )
