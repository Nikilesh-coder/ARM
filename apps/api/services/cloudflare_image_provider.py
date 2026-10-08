"""
ARM Cloudflare Image Provider Bridge
====================================
Provides support for:
1. CloudflareWorkerImageProvider (Priority 2 Worker)
2. CloudflareDirectImageProvider (Direct Cloudflare Workers AI via Account ID + API Token)
"""

import os
import io
import base64
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image as PILImage

from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.cloudflare_worker_image_provider import (
    CloudflareWorkerImageProvider,
    CloudflareWorkerImageGenerationResult,
)

logger = logging.getLogger(__name__)

DEFAULT_CF_IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"


class CloudflareDirectImageProvider:
    """Direct Cloudflare Workers AI text-to-image provider using Account ID and API Token."""

    PROVIDER_NAME = "cloudflare"

    @classmethod
    def get_account_id(cls) -> Optional[str]:
        return os.getenv("CLOUDFLARE_ACCOUNT_ID")

    @classmethod
    def get_api_token(cls) -> Optional[str]:
        return os.getenv("CLOUDFLARE_API_TOKEN")

    @classmethod
    def get_model(cls) -> str:
        return os.getenv("CLOUDFLARE_IMAGE_MODEL", DEFAULT_CF_IMAGE_MODEL).strip()

    @classmethod
    def is_configured(cls) -> bool:
        account_id = cls.get_account_id()
        token = cls.get_api_token()
        return bool(
            account_id and token and account_id.strip() not in ("", "placeholder") and token.strip() not in ("", "placeholder")
        )

    @classmethod
    def generate_image(
        cls,
        prompt: str,
        timeout: float = 60.0,
    ) -> Optional[CloudflareWorkerImageGenerationResult]:
        if not cls.is_configured():
            return None

        account_id = cls.get_account_id().strip()
        token = cls.get_api_token().strip()
        model = cls.get_model()

        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt.strip()}

        logger.info(f"[CF DIRECT] Initiating direct Cloudflare Workers AI generation via {model}...")

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                img_data = data.get("result", {})
                b64_str = img_data.get("image") if isinstance(img_data, dict) else None
                if b64_str:
                    raw_bytes = base64.b64decode(b64_str)
                    with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                        pil_img.verify()
                    with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                        buf = io.BytesIO()
                        pil_img.convert("RGB").save(buf, format="PNG")
                        png_bytes = buf.getvalue()
                        dims = pil_img.size
                        img_sha = hashlib.sha256(png_bytes).hexdigest()

                    image_provider_health_manager.record_success(cls.PROVIDER_NAME)
                    logger.info(f"[CF DIRECT] Direct Cloudflare AI generation succeeded ({dims[0]}x{dims[1]}).")
                    return CloudflareWorkerImageGenerationResult(
                        provider_name="cloudflare-direct",
                        model_name=model,
                        http_status="200 OK",
                        response_type="image/png",
                        image_bytes=png_bytes,
                        dimensions=dims,
                        sha256=img_sha,
                    )

            status_code = resp.status_code
            err_text = resp.text[:150] if resp.text else ""
            is_quota = status_code in (402, 429) or "quota" in err_text.lower() or "limit" in err_text.lower()
            reason = f"Cloudflare Direct HTTP {status_code}: {err_text}"
            logger.warning(f"[CF DIRECT] {reason}")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=reason,
                status_code=status_code,
                is_exhausted=is_quota,
            )
            return None
        except Exception as e:
            logger.warning(f"[CF DIRECT] Generation exception: {e}")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=f"Exception: {e}",
            )
            return None


class CloudflareImageProvider:
    """Composite Cloudflare provider: tries Cloudflare Worker, falls back to Direct Cloudflare AI."""

    PROVIDER_NAME = "cloudflare"

    @classmethod
    def is_configured(cls) -> bool:
        return CloudflareWorkerImageProvider.is_configured() or CloudflareDirectImageProvider.is_configured()

    @classmethod
    def generate_image(cls, prompt: str, timeout: float = 60.0) -> Optional[CloudflareWorkerImageGenerationResult]:
        if CloudflareWorkerImageProvider.is_configured() and image_provider_health_manager.is_available("cloudflare"):
            res = CloudflareWorkerImageProvider.generate_image(prompt, timeout=timeout)
            if res:
                return res
        if CloudflareDirectImageProvider.is_configured() and image_provider_health_manager.is_available("cloudflare"):
            return CloudflareDirectImageProvider.generate_image(prompt, timeout=timeout)
        return None


CloudflareImageGenerationResult = CloudflareWorkerImageGenerationResult

__all__ = [
    "CloudflareWorkerImageProvider",
    "CloudflareWorkerImageGenerationResult",
    "CloudflareDirectImageProvider",
    "CloudflareImageProvider",
    "CloudflareImageGenerationResult",
]
