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
from typing import Optional, Dict, Any, Tuple, List, Set
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
    slot_id: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    success: bool
    source: str  # "cache" | "supernova" | "xkiro" | "cloudflare" | "local_rtx" | "huggingface" | "together" | "none"
    image_path: Optional[str] = None
    image_bytes: Optional[bytes] = None
    sha256: Optional[str] = None
    width: int = 1024
    height: int = 1024
    cached: bool = False
    status: str = "SUCCESS"  # SUCCESS | SUCCESS_CACHE_HIT | IMAGE_GENERATION_UNAVAILABLE | ...
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReportImageRecord(BaseModel):
    slide_number: int
    slide_heading: str
    sha256: str
    dhash: Optional[int] = None
    source: str


class ImageGenerationManager:
    """
    Central manager enforcing strict sequential provider fallback,
    slide-context-aware versioned caching (image_cache:v2:<hash>), and
    report-level image deduplication.
    
    Strict Provider Priority:
    CACHE -> SUPERNOVA (xKiro) -> CLOUDFLARE -> LOCAL RTX -> HUGGING FACE -> TOGETHER AI -> CONTROLLED FAILURE
    """

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._report_history: Dict[str, List[ReportImageRecord]] = {}
        self.last_diagnostics: List[str] = []

    def get_last_diagnostics(self) -> List[str]:
        return list(self.last_diagnostics)

    @staticmethod
    def _compute_dhash(image_bytes: Optional[bytes]) -> Optional[int]:
        """Calculates difference hash (dHash) for 64-bit perceptual similarity comparison."""
        if not image_bytes:
            return None
        try:
            with PILImage.open(io.BytesIO(image_bytes)) as img:
                img_gray = img.convert("L").resize((9, 8), PILImage.Resampling.LANCZOS)
                getdata_fn = getattr(img_gray, "get_flattened_data", img_gray.getdata)
                pixels = list(getdata_fn())
            diff = []
            for row in range(8):
                for col in range(8):
                    pixel_left = pixels[row * 9 + col]
                    pixel_right = pixels[row * 9 + col + 1]
                    diff.append(pixel_left > pixel_right)
            decimal_val = 0
            for index, value in enumerate(diff):
                if value:
                    decimal_val += 1 << index
            return decimal_val
        except Exception:
            return None

    @staticmethod
    def compute_hamming_distance(hash1: Optional[int], hash2: Optional[int]) -> int:
        if hash1 is None or hash2 is None:
            return 64
        return bin(hash1 ^ hash2).count("1")

    def _compute_context_hash(self, req: ImageGenerationRequest) -> str:
        """
        Computes SHA-256 hash across slide heading, matter summary, intent, domain, prompt, settings.
        Slide-context aware to prevent cross-slide collisions.
        """
        norm_heading = " ".join(req.slide_heading.lower().split())
        norm_matter = " ".join(req.slide_matter.lower().split())[:300]
        norm_purpose = req.visual_purpose.lower().strip()
        norm_domain = req.detected_domain.lower().strip()
        norm_title = " ".join(req.project_title.lower().split())
        slot = (req.slot_id or f"slide_{req.slide_number}").lower().strip()
        norm_prompt = " ".join(req.final_image_prompt.strip().split())
        settings_str = f"{req.width}x{req.height}|{req.style.lower().strip()}"

        key_raw = (
            f"v2|"
            f"domain:{norm_domain}|"
            f"title:{norm_title}|"
            f"heading:{norm_heading}|"
            f"matter:{norm_matter}|"
            f"purpose:{norm_purpose}|"
            f"slot:{slot}|"
            f"prompt:{norm_prompt}|"
            f"settings:{settings_str}"
        )
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

    def _compute_cache_key(self, req: ImageGenerationRequest) -> str:
        """Returns versioned namespace key: image_cache:v2:<context_hash>"""
        return f"image_cache:v2:{self._compute_context_hash(req)}"

    def _is_image_duplicate_in_report(
        self,
        report_id: str,
        slide_number: int,
        sha256: str,
        image_bytes: bytes,
    ) -> Tuple[bool, Optional[str]]:
        """Checks if image matches any existing image in the same report (exact SHA or perceptual dHash)."""
        if not report_id or report_id not in self._report_history:
            return False, None

        new_dhash = self._compute_dhash(image_bytes)
        for record in self._report_history[report_id]:
            if record.slide_number == slide_number:
                continue  # Same slide replacement/retry is fine
            # Exact SHA match
            if record.sha256 == sha256:
                return True, f"Exact SHA256 match with Slide {record.slide_number} ('{record.slide_heading}')"
            # Perceptual dHash match (Hamming distance <= 4 out of 64 bits)
            if new_dhash is not None and record.dhash is not None:
                dist = self.compute_hamming_distance(new_dhash, record.dhash)
                if dist <= 4:
                    return True, f"High perceptual similarity (distance {dist}/64) with Slide {record.slide_number} ('{record.slide_heading}')"

        return False, None

    def record_report_image(
        self,
        report_id: str,
        slide_number: int,
        slide_heading: str,
        sha256: str,
        image_bytes: bytes,
        source: str,
    ):
        """Registers generated/accepted image in report-level history for deduplication."""
        if not report_id:
            return
        if report_id not in self._report_history:
            self._report_history[report_id] = []
        dhash = self._compute_dhash(image_bytes)
        self._report_history[report_id].append(
            ReportImageRecord(
                slide_number=slide_number,
                slide_heading=slide_heading,
                sha256=sha256,
                dhash=dhash,
                source=source,
            )
        )

    def clear_report_history(self, report_id: Optional[str] = None):
        """Clears report image history."""
        if report_id:
            self._report_history.pop(report_id, None)
        else:
            self._report_history.clear()

    def _get_from_cache(self, req: ImageGenerationRequest) -> Optional[ImageGenerationResponse]:
        cache_key = self._compute_cache_key(req)
        safe_name = cache_key.replace(":", "_")
        img_file = os.path.join(self.cache_dir, f"{safe_name}.png")
        meta_file = os.path.join(self.cache_dir, f"{safe_name}.json")

        if os.path.exists(img_file) and os.path.getsize(img_file) > 100:
            try:
                with open(img_file, "rb") as f:
                    img_bytes = f.read()
                sha = hashlib.sha256(img_bytes).hexdigest()

                # Report-level duplicate check: prevent two different slides in same report using same image
                is_dup, dup_reason = self._is_image_duplicate_in_report(
                    report_id=req.report_id,
                    slide_number=req.slide_number,
                    sha256=sha,
                    image_bytes=img_bytes,
                )
                if is_dup:
                    logger.warning(
                        f"[ARM IMAGE MANAGER] Cache HIT for Slide {req.slide_number} ('{req.slide_heading}') "
                        f"collides with report image: {dup_reason}. Bypassing cache to maintain visual diversity."
                    )
                    return None

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

                # Register in report history
                self.record_report_image(
                    report_id=req.report_id,
                    slide_number=req.slide_number,
                    slide_heading=req.slide_heading,
                    sha256=sha,
                    image_bytes=img_bytes,
                    source="cache",
                )

                logger.info(
                    f"[ARM IMAGE MANAGER] Cache HIT for Slide {req.slide_number} ('{req.slide_heading}'). Key: {cache_key}"
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
                    metadata={**meta, "cache_key": cache_key},
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
        safe_name = cache_key.replace(":", "_")
        img_file = os.path.join(self.cache_dir, f"{safe_name}.png")
        meta_file = os.path.join(self.cache_dir, f"{safe_name}.json")

        try:
            with open(img_file, "wb") as f:
                f.write(img_bytes)
            meta = {
                "cache_key": cache_key,
                "context_hash": self._compute_context_hash(req),
                "source": source,
                "project_title": req.project_title,
                "domain": req.detected_domain,
                "slide_number": req.slide_number,
                "slide_heading": req.slide_heading,
                "slide_matter_summary": " ".join(req.slide_matter.split()[:25]),
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
        Executes strict sequential image generation priority:
        CACHE -> SUPERNOVA (xKiro) -> CLOUDFLARE -> LOCAL RTX -> HUGGING FACE -> TOGETHER AI -> CONTROLLED FAILURE
        """
        logger.info(
            f"[ARM IMAGE MANAGER] Generating visual for Slide {request.slide_number} ('{request.slide_heading}'). "
            f"Domain: {request.detected_domain}"
        )

        provider_diagnostics: List[str] = []

        # ---------------------------------------------------------------------
        # PRIORITY 0: CACHE
        # ---------------------------------------------------------------------
        cached_res = self._get_from_cache(request)
        if cached_res:
            logger.info(f"[ARM IMAGE MANAGER] Cache HIT for Slide {request.slide_number} ('{request.slide_heading}')")
            self.last_diagnostics = ["Cache: HIT"]
            return cached_res

        logger.info(f"[ARM IMAGE MANAGER] Cache MISS for Slide {request.slide_number} ('{request.slide_heading}'). Continuing provider chain...")

        # Prepare final save path
        target_path = request.output_path
        if not target_path:
            gen_dir = os.path.abspath(os.path.join("generated_images", request.report_id))
            os.makedirs(gen_dir, exist_ok=True)
            target_path = os.path.join(gen_dir, f"slide_{request.slide_number}_{request.detected_domain}.png")
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

        # Internal helper to handle successful generation from any provider
        def _commit_provider_result(
            provider_name: str,
            model_name: str,
            img_bytes: bytes,
            width: int,
            height: int,
            sha256_val: str,
            metadata: Dict[str, Any],
        ) -> Optional[ImageGenerationResponse]:
            is_dup, dup_reason = self._is_image_duplicate_in_report(
                report_id=request.report_id,
                slide_number=request.slide_number,
                sha256=sha256_val,
                image_bytes=img_bytes,
            )
            if is_dup:
                logger.warning(
                    f"[ARM IMAGE MANAGER] Provider {provider_name} returned duplicate image for Slide {request.slide_number}: "
                    f"{dup_reason}. Skipping to maintain report visual diversity."
                )
                return None

            with open(target_path, "wb") as f:
                f.write(img_bytes)
            self._save_to_cache(request, img_bytes, provider_name, sha256_val)
            image_provider_health_manager.record_success(provider_name)
            self.record_report_image(
                report_id=request.report_id,
                slide_number=request.slide_number,
                slide_heading=request.slide_heading,
                sha256=sha256_val,
                image_bytes=img_bytes,
                source=provider_name,
            )
            logger.info(f"[ARM IMAGE MANAGER] Provider ({provider_name}) SUCCESS via {model_name}.")
            self.last_diagnostics = [f"{provider_name}: SUCCESS ({model_name})"]
            return ImageGenerationResponse(
                success=True,
                source=provider_name,
                image_path=target_path,
                image_bytes=img_bytes,
                sha256=sha256_val,
                width=width,
                height=height,
                cached=False,
                status="SUCCESS",
                metadata={"model": model_name, "provider": provider_name, **metadata},
            )

        # ---------------------------------------------------------------------
        # PRIORITY 1: SUPERNOVA (xKiro sensenova/sensenova-u1.5-lite) - PRIMARY
        # ---------------------------------------------------------------------
        if not XKiroImageProvider.is_configured():
            provider_diagnostics.append("Supernova: not configured")
            logger.info("[ARM IMAGE MANAGER] Supernova/xKiro is not configured. Continuing fallback...")
        elif not image_provider_health_manager.is_available("xkiro"):
            rec = image_provider_health_manager._get_record("xkiro")
            cd_diag = f"Supernova: in cooldown ({rec.failure_reason or 'rate limited / quota exhausted'})"
            provider_diagnostics.append(cd_diag)
            logger.info(f"[ARM IMAGE MANAGER] {cd_diag}. Continuing fallback...")
        else:
            logger.info("[ARM IMAGE MANAGER] Priority 1: Attempting Supernova (xKiro sensenova/sensenova-u1.5-lite)...")
            try:
                xkiro_res = XKiroImageProvider.generate_image(prompt=request.final_image_prompt)
                if xkiro_res and getattr(xkiro_res, "image_bytes", None) and isinstance(xkiro_res.image_bytes, (bytes, bytearray)):
                    res = _commit_provider_result(
                        provider_name="supernova",
                        model_name=xkiro_res.model_name,
                        img_bytes=xkiro_res.image_bytes,
                        width=xkiro_res.dimensions[0],
                        height=xkiro_res.dimensions[1],
                        sha256_val=xkiro_res.sha256,
                        metadata={"xkiro_provider": xkiro_res.provider_name},
                    )
                    if res:
                        return res
                    provider_diagnostics.append("Supernova: duplicate image rejected")
                else:
                    rec = image_provider_health_manager._get_record("xkiro")
                    fail_diag = f"Supernova: {rec.failure_reason or 'empty or invalid response'}"
                    provider_diagnostics.append(fail_diag)
                    logger.warning(f"[ARM IMAGE MANAGER] Priority 1 ({fail_diag}). Continuing fallback...")
            except Exception as e:
                fail_diag = f"Supernova: exception ({e})"
                provider_diagnostics.append(fail_diag)
                logger.warning(f"[ARM IMAGE MANAGER] Priority 1 (Supernova/xKiro) exception: {e}")

        # ---------------------------------------------------------------------
        # PRIORITY 2: CLOUDFLARE WORKER / CLOUDFLARE AI (FALLBACK)
        # ---------------------------------------------------------------------
        if not CloudflareImageProvider.is_configured():
            provider_diagnostics.append("Cloudflare: not configured")
            logger.info("[ARM IMAGE MANAGER] Cloudflare (Worker / Direct) is not configured. Continuing fallback...")
        elif not image_provider_health_manager.is_available("cloudflare"):
            rec = image_provider_health_manager._get_record("cloudflare")
            cd_diag = f"Cloudflare: in cooldown ({rec.failure_reason or 'rate limited / daily quota exhausted'})"
            provider_diagnostics.append(cd_diag)
            logger.info(f"[ARM IMAGE MANAGER] {cd_diag}. Continuing fallback...")
        else:
            logger.info("[ARM IMAGE MANAGER] Priority 2: Attempting Cloudflare (Worker / Direct AI)...")
            try:
                cf_res = CloudflareImageProvider.generate_image(prompt=request.final_image_prompt)
                if cf_res and getattr(cf_res, "image_bytes", None) and isinstance(cf_res.image_bytes, (bytes, bytearray)):
                    res = _commit_provider_result(
                        provider_name="cloudflare",
                        model_name=cf_res.model_name,
                        img_bytes=cf_res.image_bytes,
                        width=cf_res.dimensions[0],
                        height=cf_res.dimensions[1],
                        sha256_val=cf_res.sha256,
                        metadata={"cf_provider": cf_res.provider_name},
                    )
                    if res:
                        return res
                    provider_diagnostics.append("Cloudflare: duplicate image rejected")
                else:
                    rec = image_provider_health_manager._get_record("cloudflare")
                    fail_diag = f"Cloudflare: {rec.failure_reason or 'worker/direct returned empty response'}"
                    provider_diagnostics.append(fail_diag)
                    logger.warning(f"[ARM IMAGE MANAGER] Priority 2 ({fail_diag}). Continuing fallback...")
            except Exception as e:
                fail_diag = f"Cloudflare: exception ({e})"
                provider_diagnostics.append(fail_diag)
                logger.warning(f"[ARM IMAGE MANAGER] Priority 2 (Cloudflare) exception: {e}")

        # ---------------------------------------------------------------------
        # PRIORITY 3: LOCAL RTX (ACTIVE ONLY IF ENABLED OR MOCKED IN TESTS)
        # ---------------------------------------------------------------------
        if not LocalRTXProvider.is_enabled():
            provider_diagnostics.append("Local RTX: disabled (headless/cloud environment)")
            logger.info("[ARM IMAGE MANAGER] Local RTX is disabled. Continuing fallback...")
        elif not image_provider_health_manager.is_available("local_rtx"):
            provider_diagnostics.append("Local RTX: in cooldown")
            logger.info("[ARM IMAGE MANAGER] Local RTX is in cooldown. Continuing fallback...")
        else:
            logger.info("[ARM IMAGE MANAGER] Priority 3: Attempting Local RTX...")
            try:
                rtx_res = LocalRTXProvider.generate_image(
                    prompt=request.final_image_prompt,
                    width=request.width,
                    height=request.height,
                )
                if rtx_res and rtx_res.success and rtx_res.image_bytes:
                    res = _commit_provider_result(
                        provider_name="local_rtx",
                        model_name=rtx_res.model_name,
                        img_bytes=rtx_res.image_bytes,
                        width=request.width,
                        height=request.height,
                        sha256_val=rtx_res.sha256 or "",
                        metadata={"latency": getattr(rtx_res, "latency_seconds", 0.0)},
                    )
                    if res:
                        return res
                    provider_diagnostics.append("Local RTX: duplicate image rejected")
                else:
                    fail_diag = f"Local RTX: {getattr(rtx_res, 'error', 'failed')}"
                    provider_diagnostics.append(fail_diag)
                    logger.warning(f"[ARM IMAGE MANAGER] Priority 3 ({fail_diag}). Continuing fallback...")
            except Exception as e:
                fail_diag = f"Local RTX: exception ({e})"
                provider_diagnostics.append(fail_diag)
                logger.warning(f"[ARM IMAGE MANAGER] Priority 3 (Local RTX) exception: {e}")

        # ---------------------------------------------------------------------
        # PRIORITY 4: HUGGING FACE (SERVERLESS INFERENCE PROVIDERS)
        # ---------------------------------------------------------------------
        if not HFImageProvider.is_configured():
            provider_diagnostics.append("Hugging Face: not configured")
            logger.info("[ARM IMAGE MANAGER] Hugging Face is not configured. Continuing fallback...")
        elif not image_provider_health_manager.is_available("huggingface"):
            rec = image_provider_health_manager._get_record("huggingface")
            cd_diag = f"Hugging Face: in cooldown ({rec.failure_reason or 'credits exhausted'})"
            provider_diagnostics.append(cd_diag)
            logger.info(f"[ARM IMAGE MANAGER] {cd_diag}. Continuing fallback...")
        else:
            logger.info("[ARM IMAGE MANAGER] Priority 4: Attempting Hugging Face...")
            try:
                hf_res = HFImageProvider.generate_image(prompt=request.final_image_prompt)
                if hf_res and getattr(hf_res, "image_bytes", None) and isinstance(hf_res.image_bytes, (bytes, bytearray)):
                    res = _commit_provider_result(
                        provider_name="huggingface",
                        model_name=hf_res.model_name,
                        img_bytes=hf_res.image_bytes,
                        width=hf_res.dimensions[0],
                        height=hf_res.dimensions[1],
                        sha256_val=hf_res.sha256,
                        metadata={"hf_provider": hf_res.provider_name},
                    )
                    if res:
                        return res
                    provider_diagnostics.append("Hugging Face: duplicate image rejected")
                else:
                    rec = image_provider_health_manager._get_record("huggingface")
                    fail_diag = f"Hugging Face: {rec.failure_reason or 'inference returned empty image'}"
                    provider_diagnostics.append(fail_diag)
                    logger.warning(f"[ARM IMAGE MANAGER] Priority 4 ({fail_diag}). Continuing fallback...")
            except Exception as e:
                fail_diag = f"Hugging Face: exception ({e})"
                provider_diagnostics.append(fail_diag)
                logger.warning(f"[ARM IMAGE MANAGER] Priority 4 (Hugging Face) exception: {e}")

        # ---------------------------------------------------------------------
        # PRIORITY 5: TOGETHER AI (FAST INFERENCE FALLBACK)
        # ---------------------------------------------------------------------
        if not TogetherImageProvider.is_configured():
            provider_diagnostics.append("Together AI: not configured")
            logger.info("[ARM IMAGE MANAGER] Together AI is not configured. Continuing fallback...")
        elif not image_provider_health_manager.is_available("together"):
            rec = image_provider_health_manager._get_record("together")
            cd_diag = f"Together AI: in cooldown ({rec.failure_reason or 'rate limited / quota exhausted'})"
            provider_diagnostics.append(cd_diag)
            logger.info(f"[ARM IMAGE MANAGER] {cd_diag}. Continuing fallback...")
        else:
            logger.info("[ARM IMAGE MANAGER] Priority 5: Attempting Together AI...")
            try:
                tog_res = TogetherImageProvider.generate_image(
                    prompt=request.final_image_prompt,
                    width=request.width,
                    height=request.height,
                )
                if tog_res and tog_res.success and tog_res.image_bytes:
                    res = _commit_provider_result(
                        provider_name="together",
                        model_name=tog_res.model_name,
                        img_bytes=tog_res.image_bytes,
                        width=tog_res.dimensions[0],
                        height=tog_res.dimensions[1],
                        sha256_val=tog_res.sha256 or "",
                        metadata={"together_model": tog_res.model_name},
                    )
                    if res:
                        return res
                    provider_diagnostics.append("Together AI: duplicate image rejected")
                else:
                    rec = image_provider_health_manager._get_record("together")
                    fail_diag = f"Together AI: {rec.failure_reason or 'generation failed'}"
                    provider_diagnostics.append(fail_diag)
                    logger.warning(f"[ARM IMAGE MANAGER] Priority 5 ({fail_diag}). Continuing fallback...")
            except Exception as e:
                fail_diag = f"Together AI: exception ({e})"
                provider_diagnostics.append(fail_diag)
                logger.warning(f"[ARM IMAGE MANAGER] Priority 5 (Together AI) exception: {e}")

        # ---------------------------------------------------------------------
        # PRIORITY 6: CONTROLLED FAILURE
        # ---------------------------------------------------------------------
        diag_summary = "; ".join(provider_diagnostics) if provider_diagnostics else "All providers unavailable"
        err_msg = f"All configured image providers failed or exhausted: {diag_summary}"
        self.last_diagnostics = provider_diagnostics
        logger.error(
            f"[ARM IMAGE MANAGER] Slide {request.slide_number} ('{request.slide_heading}'): {err_msg}"
        )
        return ImageGenerationResponse(
            success=False,
            source="none",
            status="IMAGE_GENERATION_UNAVAILABLE",
            error=err_msg,
            metadata={"diagnostics": provider_diagnostics},
        )


# Singleton instance
image_generation_manager = ImageGenerationManager()
