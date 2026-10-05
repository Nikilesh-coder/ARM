"""
ARM Cloudflare Worker Image Generation Provider
==============================================
Primary Image Generation Provider for ARM (Priority 1).
Routes generation requests to the deployed Cloudflare Worker endpoint
(CLOUDFLARE_WORKER_URL + CLOUDFLARE_WORKER_API_KEY).

Strict Non-Regression & Safety Principles:
1. Pure image asset generation only: never modifies template XML, layout, or document structure.
2. Zero Secret Exposure: Never logs API tokens, secrets, or authorization headers.
3. Safe Binary Handling: Expects binary image data (image/jpeg or image/png), validates with PIL.
4. Quota Cooldown: Triggers provider cooldown on 4006 daily quota exhaustion, enabling graceful RTX fallback.
5. Zero Fake Images: Never returns dummy/fake images on failure; returns None to allow clean fallback.
"""

import os
import io
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image as PILImage

from apps.api.services.image_provider_cooldown import image_provider_health_manager

logger = logging.getLogger(__name__)

DEFAULT_WORKER_URL = "https://image-api.2024csm-r260.workers.dev/"


class CloudflareWorkerImageGenerationResult:
    """Standardized result container for Cloudflare Worker image generation."""

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        http_status: str,
        response_type: str,
        image_bytes: bytes,
        dimensions: Tuple[int, int],
        sha256: str,
    ):
        self.provider_name = provider_name
        self.model_name = model_name
        self.http_status = http_status
        self.response_type = response_type
        self.image_bytes = image_bytes
        self.dimensions = dimensions
        self.sha256 = sha256


class CloudflareWorkerImageProvider:
    """Primary image provider wrapping the deployed Cloudflare Worker."""

    PROVIDER_NAME = "cloudflare"

    @classmethod
    def get_worker_url(cls) -> str:
        return os.getenv("CLOUDFLARE_WORKER_URL", DEFAULT_WORKER_URL).strip()

    @classmethod
    def get_worker_key(cls) -> Optional[str]:
        return os.getenv("CLOUDFLARE_WORKER_API_KEY")

    @classmethod
    def is_configured(cls) -> bool:
        url = cls.get_worker_url()
        key = cls.get_worker_key()
        return bool(url and key and key.strip() not in ("", "placeholder", "undefined", "<WORKER_SECRET>"))

    @classmethod
    def generate_image(
        cls,
        prompt: str,
        timeout: float = 60.0,
    ) -> Optional[CloudflareWorkerImageGenerationResult]:
        """
        Sends an authenticated POST request to the deployed Cloudflare Worker:
        POST CLOUDFLARE_WORKER_URL
        Headers:
          Authorization: Bearer <CLOUDFLARE_WORKER_API_KEY>
          Content-Type: application/json
        Body:
          { "prompt": "<ARM generated prompt>" }

        Expects binary image data. Never logs secret keys or sensitive headers.
        """
        worker_url = cls.get_worker_url()
        worker_key = cls.get_worker_key()

        if not cls.is_configured():
            logger.info("Cloudflare Worker unavailable — using RTX fallback")
            return None

        clean_prompt = prompt.strip() if prompt else ""
        if not clean_prompt:
            logger.warning("[CF WORKER] Empty prompt provided. Skipping generation.")
            return None

        # Safe logging: strictly no secrets or auth tokens logged
        logger.info("Cloudflare Worker image generation started")

        headers = {
            "Authorization": f"Bearer {worker_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": clean_prompt}

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(worker_url, json=payload, headers=headers)

            status_code = resp.status_code
            content_type = resp.headers.get("content-type", "").lower()

            if status_code == 200:
                raw_bytes = resp.content

                # Validate image response format via magic bytes or content type
                is_image_data = (
                    "image" in content_type
                    or raw_bytes.startswith(b"\x89PNG")
                    or raw_bytes.startswith(b"\xff\xd8")
                    or raw_bytes.startswith(b"RIFF")
                )

                if is_image_data and len(raw_bytes) > 100:
                    try:
                        with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                            # Verify valid image integrity
                            pil_img.verify()

                        # Re-open for conversion (verify invalidates the buffer)
                        with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                            buf = io.BytesIO()
                            pil_img.convert("RGB").save(buf, format="PNG")
                            png_bytes = buf.getvalue()
                            dims = pil_img.size
                            img_sha = hashlib.sha256(png_bytes).hexdigest()

                        image_provider_health_manager.record_success(cls.PROVIDER_NAME)
                        logger.info("Cloudflare Worker image generation succeeded")

                        return CloudflareWorkerImageGenerationResult(
                            provider_name="cloudflare-worker",
                            model_name="cf-workers-ai",
                            http_status="200 OK",
                            response_type="image/png",
                            image_bytes=png_bytes,
                            dimensions=dims,
                            sha256=img_sha,
                        )
                    except Exception as verify_err:
                        logger.warning(f"[CF WORKER] Invalid image binary received: {verify_err}")
                        image_provider_health_manager.record_failure(
                            cls.PROVIDER_NAME,
                            reason="Corrupt image data received",
                            status_code=502,
                        )
                        return None
                else:
                    logger.warning("[CF WORKER] Response was not valid image binary data.")
                    image_provider_health_manager.record_failure(
                        cls.PROVIDER_NAME,
                        reason="Non-image binary response",
                        status_code=502,
                    )
                    return None

            # Handle quota / neuron limit exhaustion (4006)
            resp_text = resp.text.lower() if resp.text else ""
            if "4006" in resp_text or "allocation" in resp_text or "quota" in resp_text:
                logger.warning("Cloudflare Worker quota exhausted — using fallback")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason="Cloudflare Worker quota exhausted (4006)",
                    status_code=status_code,
                    is_exhausted=True,
                )
                return None

            # Handle Authentication failure (401)
            if status_code == 401:
                logger.warning("Cloudflare Worker unavailable — using RTX fallback")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason="Cloudflare Worker authentication failed (401)",
                    status_code=401,
                )
                return None

            # Handle Rate limiting (429)
            if status_code == 429:
                logger.warning("Cloudflare Worker unavailable — using RTX fallback")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason="Cloudflare Worker rate limited (429)",
                    status_code=429,
                )
                return None

            # Other server or client errors
            logger.warning(f"Cloudflare Worker unavailable — using RTX fallback (HTTP {status_code})")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=f"HTTP {status_code}",
                status_code=status_code,
            )

        except httpx.TimeoutException:
            logger.warning("Cloudflare Worker unavailable — using RTX fallback (Timeout)")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason="Request timed out",
                status_code=504,
            )
        except Exception as ex:
            logger.warning(f"Cloudflare Worker unavailable — using RTX fallback ({type(ex).__name__})")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=f"Connection error: {type(ex).__name__}",
                status_code=500,
            )

        return None
