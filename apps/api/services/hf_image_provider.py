"""
Hugging Face Inference Providers Image Generation Service for ARM
==================================================================
Free-first text-to-image generation leveraging Hugging Face serverless
Inference Providers (with monthly free inference credit).

Rules:
- Uses official huggingface_hub.InferenceClient.
- Queries models dynamically or uses free-tier compatible models.
- NEVER enables paid billing or purchases credits automatically.
- NEVER exposes or logs HF_TOKEN.
- If credit/quota exhausted or model fails: returns None (no graph fallback).
"""

import io
import os
import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image as PILImage
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from apps.api.core.config import settings

logger = logging.getLogger(__name__)

# Preferred text-to-image models for free serverless inference
PREFERRED_FREE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/sdxl-turbo",
]


class HFImageGenerationResult:
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


class HFImageProvider:
    """Service wrapping Hugging Face Inference Providers for ARM image generation."""

    @classmethod
    def get_token(cls) -> Optional[str]:
        """Retrieves HF_TOKEN safely without exposing or logging it."""
        token = settings.image_provider.hf_token or os.getenv("HF_TOKEN")
        if token and token.strip():
            return token.strip()
        return None

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if HF_TOKEN is configured."""
        return cls.get_token() is not None

    @classmethod
    def query_available_models(cls, limit: int = 10) -> List[str]:
        """
        Queries Hugging Face API dynamically for text-to-image models.
        """
        import urllib.request
        import json

        url = f"https://huggingface.co/api/models?pipeline_tag=text-to-image&sort=downloads&direction=-1&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ARM-ReportForge"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id") for m in data if m.get("id")]
                return models
        except Exception as ex:
            logger.warning(f"[HF IMAGE PROVIDER] Could not dynamically query models: {ex}. Using default list.")
            return PREFERRED_FREE_MODELS

    @classmethod
    def generate_image(
        cls,
        prompt: str,
        model: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Optional[HFImageGenerationResult]:
        """
        Generates an image from prompt using Hugging Face Inference Providers.
        Uses monthly free serverless credit.
        Never enables paid billing.
        If generation fails or quota is exhausted, returns None.
        """
        token = cls.get_token()
        if not token:
            logger.error("[HF IMAGE PROVIDER] HF_TOKEN is not configured in .env or settings. Generation skipped.")
            return None

        # Determine target model
        candidate_models = []
        if model:
            candidate_models.append(model)
        configured_model = settings.image_provider.hf_image_model or os.getenv("HF_IMAGE_MODEL")
        if configured_model and configured_model not in candidate_models:
            candidate_models.append(configured_model)
        for m in PREFERRED_FREE_MODELS:
            if m not in candidate_models:
                candidate_models.append(m)

        # Providers to attempt: 'auto' (recommended by Hugging Face router), then 'hf-inference'
        providers = ["auto", "hf-inference"]

        for target_model in candidate_models:
            for prov in providers:
                try:
                    client = InferenceClient(
                        model=target_model,
                        provider=prov,
                        token=token,
                        timeout=timeout,
                    )

                    # Execute text-to-image
                    pil_img = client.text_to_image(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                    )

                    if isinstance(pil_img, PILImage.Image):
                        # Convert to PNG bytes
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        img_bytes = buf.getvalue()
                        img_sha = hashlib.sha256(img_bytes).hexdigest()
                        dims = pil_img.size

                        return HFImageGenerationResult(
                            provider_name=prov,
                            model_name=target_model,
                            http_status="200 OK",
                            response_type="PIL.Image (image/png)",
                            image_bytes=img_bytes,
                            dimensions=dims,
                            sha256=img_sha,
                        )

                except HfHubHTTPError as hf_err:
                    status_code = getattr(hf_err.response, "status_code", 500) if hasattr(hf_err, "response") else 500
                    logger.warning(
                        f"[HF IMAGE PROVIDER] Model {target_model} on provider {prov} failed with HTTP {status_code}: {hf_err}"
                    )
                    from apps.api.services.image_provider_cooldown import image_provider_health_manager
                    is_exhausted = status_code in (402, 429)
                    reason_label = "credits exhausted" if status_code == 402 else ("quota exhausted" if status_code == 429 else f"HTTP {status_code}")
                    image_provider_health_manager.record_failure(
                        "huggingface",
                        reason=f"{status_code} {reason_label}",
                        status_code=status_code,
                        is_exhausted=is_exhausted,
                    )
                    # If 429 (Rate Limit / Quota) or 402/403 (Payment/Quota Required):
                    if status_code in (429, 402, 403):
                        logger.error(
                            f"[HF IMAGE PROVIDER] Quota / Free tier credit exhausted or restricted on Hugging Face (HTTP {status_code}). "
                            f"STOPPING image generation for this slide (NO GRAPH FALLBACK)."
                        )
                        # Do NOT try paid providers
                        return None
                    # Try next candidate model/provider
                    continue

                except Exception as ex:
                    logger.warning(f"[HF IMAGE PROVIDER] Model {target_model} on provider {prov} error: {ex}")
                    from apps.api.services.image_provider_cooldown import image_provider_health_manager
                    image_provider_health_manager.record_failure(
                        "huggingface",
                        reason=f"error: {str(ex)[:100]}",
                    )
                    continue

        from apps.api.services.image_provider_cooldown import image_provider_health_manager
        if image_provider_health_manager.is_available("huggingface"):
            image_provider_health_manager.record_failure(
                "huggingface",
                reason="all candidate models failed",
            )
        logger.error("[HF IMAGE PROVIDER] All candidate models/providers failed. Returning None (NO GRAPH FALLBACK).")
        return None
