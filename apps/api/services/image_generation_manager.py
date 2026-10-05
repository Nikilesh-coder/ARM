"""
ARM Stage: Image Generation Manager
===================================
Central orchestrator for AI-generated real-world images.
Strict Provider Priority:
CACHE -> LOCAL RTX 3050 -> CLOUDFLARE -> HUGGING FACE -> TOGETHER AI -> CONTROLLED FAILURE

Exposes a single normalized interface:
generate_image(request: ImageGenerationRequest) -> ImageGenerationResponse
"""

import os
import io
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from PIL import Image as PILImage

from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.xkiro_image_provider import XKiroImageProvider, XKiroImageGenerationResult
from apps.api.services.local_rtx_provider import LocalRTXProvider
from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageProvider, CloudflareWorkerImageGenerationResult
from apps.api.services.cloudflare_image_provider import CloudflareImageProvider
from apps.api.services.hf_image_provider import HFImageProvider
from apps.api.services.together_image_provider import TogetherImageProvider

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.abspath(os.path.join(".storage", "cache", "images"))


class ImageGenerationRequest(BaseModel):
    project_title: str
    project_description: str = ""
    detected_domain: str = "general"
    domain_confidence: float = 1.0
    slide_number: int = 1
    slide_heading: str = ""
    slide_matter: str = ""
    visual_purpose: str = "GENERAL_TECHNICAL"
    final_image_prompt: str
    width: int = 1024
    height: int = 1024
    output_format: str = "PNG"
    output_path: Optional[str] = None
    report_id: str = "default_run"
    style: str = "photorealistic"


class ImageGenerationResponse(BaseModel):
    success: bool
    source: str  # "cache" | "local_rtx" | "cloudflare" | "huggingface" | "together" | "none"
    image_path: Optional[str] = None
    image_bytes: Optional[bytes] = None
    sha256: Optional[str] = None
    width: int = 1024
    height: int = 1024
    cached: bool = False
    status: str = "SUCCESS"  # SUCCESS | IMAGE_GENERATION_UNAVAILABLE | ...
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ImageGenerationManager:
    """Central manager enforcing strict sequential provider fallback and caching."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _compute_cache_key(self, req: ImageGenerationRequest) -> str:
        """
        Deterministic cache key based on:
        domain, project_title, visual_purpose, slide_heading, normalized final prompt, dimensions, style.
        """
        key_raw = (
            f"domain:{req.detected_domain.lower().strip()}|"
            f"title:{req.project_title.lower().strip()}|"
            f"purpose:{req.visual_purpose.lower().strip()}|"
            f"heading:{req.slide_heading.lower().strip()}|"
            f"prompt:{req.final_image_prompt.strip()}|"
            f"dims:{req.width}x{req.height}|"
            f"style:{req.style.lower().strip()}"
        )
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

    def _get_from_cache(self, req: ImageGenerationRequest) -> Optional[ImageGenerationResponse]:
        cache_key = self._compute_cache_key(req)
        img_file = os.path.join(self.cache_dir, f"{cache_key}.png")
        meta_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(img_file) and os.path.getsize(img_file) > 100:
            try:
                with open(img_file, "rb") as f:
                    img_bytes = f.read()
                sha = hashlib.sha256(img_bytes).hexdigest()
                meta = {}
                if os.path.exists(meta_file):
                    with open(meta_file, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)

                # If specific output_path requested, copy to target
                final_path = img_file
                if req.output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)
                    with open(req.output_path, "wb") as out_f:
                        out_f.write(img_bytes)
                    final_path = req.output_path

                logger.info(
                    f"[ARM IMAGE MANAGER] Cache HIT for Slide {req.slide_number} ('{req.slide_heading}'). Key: {cache_key[:12]}"
                )
                return ImageGenerationResponse(
                    success=True,
                    source="cache",
                    image_path=final_path,
                    image_bytes=img_bytes,
                    sha256=sha,
                    width=req.width,
                    height=req.height,
                    cached=True,
                    status="SUCCESS_CACHE_HIT",
                    metadata=meta,
                )
            except Exception as e:
                logger.warning(f"[ARM IMAGE MANAGER] Cache read failed: {e}")

        return None

    def _save_to_cache(
        self,
        req: ImageGenerationRequest,
        img_bytes: bytes,
        source: str,
        sha256: str,
    ) -> str:
        cache_key = self._compute_cache_key(req)
        img_file = os.path.join(self.cache_dir, f"{cache_key}.png")
        meta_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        try:
            with open(img_file, "wb") as f:
                f.write(img_bytes)
            meta = {
                "source": source,
                "project_title": req.project_title,
                "domain": req.detected_domain,
                "slide_number": req.slide_number,
                "slide_heading": req.slide_heading,
                "visual_purpose": req.visual_purpose,
                "sha256": sha256,
                "dimensions": f"{req.width}x{req.height}",
            }
            with open(meta_file, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, indent=2)
        except Exception as e:
            logger.warning(f"[ARM IMAGE MANAGER] Error writing to cache: {e}")

        return img_file

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        Executes sequential image generation priority:
        CACHE -> LOCAL RTX 3050 -> CLOUDFLARE -> HUGGING FACE -> TOGETHER AI -> CONTROLLED FAILURE
        """
        logger.info(
            f"[ARM IMAGE MANAGER] Generating visual for Slide {request.slide_number} ('{request.slide_heading}'). "
            f"Domain: {request.detected_domain}"
        )

        # ---------------------------------------------------------------------
        # PRIORITY 0: CACHE
        # ---------------------------------------------------------------------
        cached_res = self._get_from_cache(request)
        if cached_res:
            return cached_res

        # Prepare final save path
        target_path = request.output_path
        if not target_path:
            gen_dir = os.path.abspath(os.path.join("generated_images", request.report_id))
            os.makedirs(gen_dir, exist_ok=True)
            target_path = os.path.join(gen_dir, f"slide_{request.slide_number}_{request.detected_domain}.png")
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

        # ---------------------------------------------------------------------
        # PRIORITY 1: xKiro (sensenova/sensenova-u1.5-lite) - PRIMARY PROVIDER
        # ---------------------------------------------------------------------
        if XKiroImageProvider.is_configured() and image_provider_health_manager.is_available("xkiro"):
            logger.info("[ARM IMAGE MANAGER] Priority 1: Attempting xKiro (sensenova/sensenova-u1.5-lite)...")
            xkiro_res = XKiroImageProvider.generate_image(prompt=request.final_image_prompt)
            if xkiro_res and getattr(xkiro_res, "image_bytes", None) and isinstance(xkiro_res.image_bytes, (bytes, bytearray)):
                with open(target_path, "wb") as f:
                    f.write(xkiro_res.image_bytes)
                self._save_to_cache(request, xkiro_res.image_bytes, "xkiro", xkiro_res.sha256)
                image_provider_health_manager.record_success("xkiro")
                logger.info(f"[ARM IMAGE MANAGER] Priority 1 (xKiro) SUCCESS via {xkiro_res.model_name}.")
                return ImageGenerationResponse(
                    success=True,
                    source="xkiro",
                    image_path=target_path,
                    image_bytes=xkiro_res.image_bytes,
                    sha256=xkiro_res.sha256,
                    width=xkiro_res.dimensions[0],
                    height=xkiro_res.dimensions[1],
                    cached=False,
                    status="SUCCESS",
                    metadata={"model": xkiro_res.model_name, "provider": xkiro_res.provider_name},
                )
            else:
                logger.info("[ARM IMAGE MANAGER] Priority 1 (xKiro) failed or unavailable. Continuing to Cloudflare Worker fallback...")

        # ---------------------------------------------------------------------
        # PRIORITY 2: CLOUDFLARE WORKER (FALLBACK ONLY)
        # ---------------------------------------------------------------------
        if CloudflareWorkerImageProvider.is_configured() and image_provider_health_manager.is_available("cloudflare"):
            logger.info("[ARM IMAGE MANAGER] Priority 2: Attempting Cloudflare Worker...")
            cf_res = CloudflareWorkerImageProvider.generate_image(prompt=request.final_image_prompt)
            if cf_res and getattr(cf_res, "image_bytes", None) and isinstance(cf_res.image_bytes, (bytes, bytearray)):
                with open(target_path, "wb") as f:
                    f.write(cf_res.image_bytes)
                self._save_to_cache(request, cf_res.image_bytes, "cloudflare", cf_res.sha256)
                image_provider_health_manager.record_success("cloudflare")
                logger.info(f"[ARM IMAGE MANAGER] Priority 2 (Cloudflare Worker) SUCCESS via {cf_res.model_name}.")
                return ImageGenerationResponse(
                    success=True,
                    source="cloudflare",
                    image_path=target_path,
                    image_bytes=cf_res.image_bytes,
                    sha256=cf_res.sha256,
                    width=cf_res.dimensions[0],
                    height=cf_res.dimensions[1],
                    cached=False,
                    status="SUCCESS",
                    metadata={"model": cf_res.model_name, "provider": cf_res.provider_name},
                )
            else:
                logger.info("[ARM IMAGE MANAGER] Priority 2 (Cloudflare Worker) failed or unavailable. Continuing fallback...")

        # ---------------------------------------------------------------------
        # PRIORITY 3: LOCAL RTX (DISABLED IN PRODUCTION; ACTIVE ONLY IF MOCKED IN UNIT TESTS)
        # ---------------------------------------------------------------------
        if LocalRTXProvider.is_enabled() and image_provider_health_manager.is_available("local_rtx"):
            logger.info("[ARM IMAGE MANAGER] Fallback: Probing Local RTX...")
            rtx_res = LocalRTXProvider.generate_image(
                prompt=request.final_image_prompt,
                width=request.width,
                height=request.height,
            )
            if rtx_res.success and rtx_res.image_bytes:
                with open(target_path, "wb") as f:
                    f.write(rtx_res.image_bytes)
                self._save_to_cache(request, rtx_res.image_bytes, "local_rtx", rtx_res.sha256 or "")
                logger.info("[ARM IMAGE MANAGER] Fallback (Local RTX) SUCCESS.")
                return ImageGenerationResponse(
                    success=True,
                    source="local_rtx",
                    image_path=target_path,
                    image_bytes=rtx_bytes if (rtx_bytes := getattr(rtx_res, "image_bytes", None)) else None,
                    sha256=rtx_res.sha256,
                    width=request.width,
                    height=request.height,
                    cached=False,
                    status="SUCCESS",
                    metadata={"model": rtx_res.model_name, "latency": getattr(rtx_res, "latency_seconds", 0.0)},
                )

        # ---------------------------------------------------------------------
        # PRIORITY 4: CONTROLLED FAILURE (NO PAID PROVIDERS)
        # ---------------------------------------------------------------------
        logger.error(
            f"[ARM IMAGE MANAGER] All configured image providers (xKiro, Cloudflare) failed or exhausted for Slide {request.slide_number} "
            f"('{request.slide_heading}'). Returning IMAGE_GENERATION_UNAVAILABLE."
        )
        return ImageGenerationResponse(
            success=False,
            source="none",
            status="IMAGE_GENERATION_UNAVAILABLE",
            error="All configured free image providers (xKiro, Cloudflare Worker) were unavailable or exhausted.",
        )


# Singleton instance
image_generation_manager = ImageGenerationManager()
