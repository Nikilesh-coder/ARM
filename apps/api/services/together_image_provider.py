"""
ARM Stage: Together AI Image Generation Provider (Optional Fallback)
===================================================================
Provides optional image synthesis via Together AI text-to-image API.
Strict Rules:
- Only active when TOGETHER_API_KEY is configured.
- Gracefully skipped when unconfigured.
- Handles rate limits, quota limits, and timeouts.
- Never prints tokens in logs.
"""

import os
import base64
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image as PILImage
import io

from apps.api.services.image_provider_cooldown import image_provider_health_manager

logger = logging.getLogger(__name__)

TOGETHER_IMAGE_ENDPOINT = "https://api.together.xyz/v1/images/generations"
DEFAULT_TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"


class TogetherImageGenerationResult:
    def __init__(
        self,
        success: bool,
        image_bytes: Optional[bytes] = None,
        dimensions: Tuple[int, int] = (1024, 1024),
        sha256: Optional[str] = None,
        model_name: str = DEFAULT_TOGETHER_MODEL,
        status: str = "SUCCESS",
        error: Optional[str] = None,
    ):
        self.success = success
        self.image_bytes = image_bytes
        self.dimensions = dimensions
        self.sha256 = sha256
        self.model_name = model_name
        self.status = status
        self.error = error


class TogetherImageProvider:
    """
    Together AI text-to-image provider.
    """

    PROVIDER_NAME = "together"

    @classmethod
    def is_configured(cls) -> bool:
        key = os.getenv("TOGETHER_API_KEY", "").strip()
        return bool(key and not key.startswith("placeholder"))

    @classmethod
    def generate_image(
        cls,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        timeout: float = 30.0,
    ) -> Optional[TogetherImageGenerationResult]:
        if not cls.is_configured():
            return None

        if not image_provider_health_manager.is_available(cls.PROVIDER_NAME):
            logger.info("[ARM TOGETHER] Together AI provider is in cooldown. Skipping.")
            return None

        api_key = os.getenv("TOGETHER_API_KEY", "").strip()
        model = os.getenv("TOGETHER_IMAGE_MODEL", DEFAULT_TOGETHER_MODEL)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": 4,
            "n": 1,
            "response_format": "b64_json",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(TOGETHER_IMAGE_ENDPOINT, headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                data_list = data.get("data", [])
                if data_list and "b64_json" in data_list[0]:
                    b64_str = data_list[0]["b64_json"]
                    img_bytes = base64.b64decode(b64_str)
                    sha256 = hashlib.sha256(img_bytes).hexdigest()

                    image_provider_health_manager.record_success(cls.PROVIDER_NAME)
                    return TogetherImageGenerationResult(
                        success=True,
                        image_bytes=img_bytes,
                        dimensions=(width, height),
                        sha256=sha256,
                        model_name=model,
                        status="SUCCESS",
                    )
            elif resp.status_code == 429:
                err_text = "Rate limit or quota exhausted"
                logger.warning(f"[ARM TOGETHER] Returned 429: {err_text}")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason=err_text,
                    status_code=429,
                    is_exhausted=True,
                )
            else:
                err_text = f"HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(f"[ARM TOGETHER] Failure: {err_text}")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason=err_text,
                    status_code=resp.status_code,
                )
        except Exception as ex:
            logger.error(f"[ARM TOGETHER] Exception: {ex}")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=str(ex),
            )

        return None
