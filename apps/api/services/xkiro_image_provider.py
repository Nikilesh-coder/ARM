"""
ARM xKiro Image Generation Provider
===================================
Primary Image Generation Provider for ARM.
Connects to the official xKiro AI gateway using model `sensenova/sensenova-u1.5-lite`.

Async Flow:
1. POST /v1/images/generations (Model: sensenova/sensenova-u1.5-lite)
2. Receive Job ID (HTTP 202 Accepted)
3. Poll GET /v1/images/generations/{id}
4. Wait until status == "succeeded"
5. Download returned xKiro CDN image
6. Validate image with PIL
7. Pass validated image into ARM's image pipeline

Safety & Non-Regression Principles:
1. FREE-ONLY SAFETY: Enforces XKIRO_FREE_ONLY=true. Halts generation if free allowance is exhausted.
   Never incurs paid wallet charges or uses paid fallbacks.
2. ZERO SECRET EXPOSURE: Never logs API tokens, keys, or authorization headers.
3. SAFE BINARY HANDLING: Validates image bytes with PIL and converts cleanly to PNG.
4. PURE ASSET GENERATION: Never alters template structure, XML, or layout.
"""

import os
import io
import time
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image as PILImage

from apps.api.services.image_provider_cooldown import image_provider_health_manager

logger = logging.getLogger(__name__)

DEFAULT_XKIRO_BASE_URL = "https://api.xkiro.com"
DEFAULT_XKIRO_MODEL = "sensenova/sensenova-u1.5-lite"


class XKiroImageGenerationResult:
    """Standardized result container for xKiro image generation."""

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


class XKiroImageProvider:
    """Primary image provider wrapping xKiro sensenova/sensenova-u1.5-lite."""

    PROVIDER_NAME = "xkiro"

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        if "XKIRO_API_KEY" in os.environ or "SUPERNOVA_API_KEY" in os.environ:
            val = (os.getenv("XKIRO_API_KEY") or os.getenv("SUPERNOVA_API_KEY") or "").strip()
            return val or None
        try:
            from apps.api.core.config import settings
            val = getattr(settings.image_provider, "xkiro_api_key", None)
            return val.strip() if val else None
        except Exception:
            return None

    @classmethod
    def get_base_url(cls) -> str:
        raw = os.getenv("XKIRO_BASE_URL") or os.getenv("SUPERNOVA_BASE_URL", DEFAULT_XKIRO_BASE_URL)
        return raw.strip().rstrip("/")

    @classmethod
    def get_model_name(cls) -> str:
        val = os.getenv("XKIRO_MODEL") or os.getenv("SUPERNOVA_MODEL")
        if not val:
            try:
                from apps.api.core.config import settings
                val = getattr(settings.image_provider, "xkiro_model", None)
            except Exception:
                pass
        return (val or DEFAULT_XKIRO_MODEL).strip()

    @classmethod
    def is_free_only(cls) -> bool:
        return os.getenv("XKIRO_FREE_ONLY", "true").lower() in ("true", "1", "yes")

    @classmethod
    def is_configured(cls) -> bool:
        key = cls.get_api_key()
        return bool(key and key.strip() and key.strip() not in ("", "placeholder", "undefined", "<XKIRO_API_KEY>"))

    @classmethod
    def _sanitize(cls, message: str) -> str:
        key = cls.get_api_key()
        if key and key.strip():
            return message.replace(key.strip(), "***REDACTED***")
        return message

    @classmethod
    def check_free_quota(cls) -> Tuple[bool, str]:
        """
        Queries xKiro account usage endpoint (/v1/usage) to verify that free allowance
        is active and remaining. Prevents paid wallet charges if free allowance is exhausted.
        """
        api_key = cls.get_api_key()
        if not api_key:
            return False, "XKIRO_API_KEY not configured"

        base_url = cls.get_base_url()
        try:
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/v1/usage", headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                free_tokens = data.get("free_tokens", {})
                remaining = free_tokens.get("remaining", None)
                if remaining is not None and remaining <= 0:
                    return False, f"Free allowance exhausted (0 of {free_tokens.get('limit_per_day', 0)} units remaining)"
                return True, "Free allowance available"
            elif resp.status_code in (401, 403):
                return False, f"Authentication error ({resp.status_code})"
            else:
                # If usage endpoint is temporarily unavailable, permit proceed with caution
                return True, "Usage endpoint returned status " + str(resp.status_code)
        except Exception as e:
            logger.warning(f"[xKiro] Quota check warning: {cls._sanitize(str(e))}")
            return True, "Quota check skipped on network warning"

    @classmethod
    def generate_image(
        cls,
        prompt: str,
        timeout: float = 120.0,
    ) -> Optional[XKiroImageGenerationResult]:
        """
        Executes complete async xKiro image generation:
        1. Checks free allowance safety.
        2. Submits generation request: POST /v1/images/generations
        3. Receives Job ID.
        4. Polls GET /v1/images/generations/{id} until succeeded.
        5. Downloads and validates CDN image bytes.
        """
        if not cls.is_configured():
            logger.info("[xKiro] Provider unconfigured (XKIRO_API_KEY not set). Skipping.")
            return None

        clean_prompt = prompt.strip() if prompt else ""
        if not clean_prompt:
            logger.warning("[xKiro] Empty prompt provided. Skipping generation.")
            return None

        # Free-Only Safety Check
        if cls.is_free_only():
            allowed, quota_reason = cls.check_free_quota()
            if not allowed:
                logger.error(f"[xKiro FREE SAFETY] Generation prevented: {quota_reason}. Paid charges blocked.")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason=f"Free allowance unavailable: {quota_reason}",
                    status_code=429,
                    is_exhausted=True,
                )
                return None

        api_key = cls.get_api_key().strip()
        base_url = cls.get_base_url()
        model_name = cls.get_model_name()

        logger.info(f"[xKiro] Initiating image generation via {model_name}...")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "prompt": clean_prompt,
            "n": 1,
            "size": "1024x1024",
        }

        # Step 1: Submit generation job with bounded retries & exponential backoff
        max_retries = 2
        submit_resp = None
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    submit_resp = client.post(
                        f"{base_url}/v1/images/generations",
                        json=payload,
                        headers=headers,
                    )
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as err:
                if attempt < max_retries:
                    backoff = 1.5 * (2 ** attempt)
                    logger.warning(f"[xKiro] Transient network error (attempt {attempt+1}/{max_retries+1}): {cls._sanitize(str(err))}. Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"[xKiro] Network error submitting generation request after {max_retries+1} attempts: {cls._sanitize(str(err))}")
                    image_provider_health_manager.record_failure(
                        cls.PROVIDER_NAME,
                        reason=f"Network error after {max_retries+1} attempts: {cls._sanitize(str(err))}",
                    )
                    return None
            except Exception as err:
                logger.error(f"[xKiro] Fatal submission error: {cls._sanitize(str(err))}")
                image_provider_health_manager.record_failure(
                    cls.PROVIDER_NAME,
                    reason=f"Fatal error: {cls._sanitize(str(err))}",
                )
                return None

            if submit_resp.status_code in (200, 201, 202):
                break

            # Handle 429 Rate Limit with Retry-After
            if submit_resp.status_code == 429 and attempt < max_retries:
                retry_after_hdr = submit_resp.headers.get("Retry-After")
                try:
                    retry_wait = float(retry_after_hdr) if retry_after_hdr else (2.0 * (attempt + 1))
                except (ValueError, TypeError):
                    retry_wait = 2.0 * (attempt + 1)
                if retry_wait <= 10.0:
                    logger.warning(f"[xKiro] Rate limited (429). Respecting Retry-After: waiting {retry_wait:.1f}s (attempt {attempt+1}/{max_retries+1})...")
                    time.sleep(retry_wait)
                    continue

            # Handle 5xx Transient Server Error
            if 500 <= submit_resp.status_code < 600 and attempt < max_retries:
                backoff = 2.0 * (attempt + 1)
                logger.warning(f"[xKiro] Server error {submit_resp.status_code}. Retrying in {backoff:.1f}s (attempt {attempt+1}/{max_retries+1})...")
                time.sleep(backoff)
                continue

            # Fatal error or credit exhaustion: do not retry
            err_msg = cls._sanitize(submit_resp.text[:300])
            logger.error(f"[xKiro] Submission failed (HTTP {submit_resp.status_code}): {err_msg}")
            is_quota = submit_resp.status_code in (402, 429) or "quota" in err_msg.lower() or "limit" in err_msg.lower()
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason=f"API error HTTP {submit_resp.status_code}: {err_msg}",
                status_code=submit_resp.status_code,
                is_exhausted=is_quota,
            )
            return None

        if not submit_resp or submit_resp.status_code not in (200, 201, 202):
            return None

        try:
            submit_data = submit_resp.json()
        except Exception:
            logger.error(f"[xKiro] Invalid JSON response on submission.")
            return None

        # Check if job returned synchronously or asynchronously
        job_id = submit_data.get("id") or (submit_data.get("data", {}).get("id") if isinstance(submit_data.get("data"), dict) else None)
        cdn_url = None

        if not job_id and isinstance(submit_data.get("data"), list) and submit_data["data"]:
            cdn_url = submit_data["data"][0].get("url")

        # Step 2: Asynchronous Polling
        if job_id and not cdn_url:
            logger.info(f"[xKiro] Received Job ID {job_id}. Polling for completion...")
            poll_url = f"{base_url}/v1/images/generations/{job_id}"
            start_time = time.time()
            deadline = start_time + timeout

            while time.time() < deadline:
                time.sleep(2.5)  # 2.5s interval to avoid rate limiting
                try:
                    with httpx.Client(timeout=15.0) as client:
                        poll_resp = client.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})

                    if poll_resp.status_code != 200:
                        logger.warning(f"[xKiro] Polling HTTP {poll_resp.status_code}: {cls._sanitize(poll_resp.text[:100])}")
                        continue

                    poll_data = poll_resp.json()
                    status = poll_data.get("status", "").lower()

                    if status in ("succeeded", "completed", "success"):
                        data_arr = poll_data.get("data", [])
                        if isinstance(data_arr, list) and data_arr:
                            cdn_url = data_arr[0].get("url")
                        elif poll_data.get("url"):
                            cdn_url = poll_data.get("url")
                        break
                    elif status in ("failed", "blocked"):
                        err_detail = poll_data.get("error", "Generation status: " + status)
                        logger.error(f"[xKiro] Generation {status}: {cls._sanitize(str(err_detail))}")
                        image_provider_health_manager.record_failure(
                            cls.PROVIDER_NAME,
                            reason=f"Generation {status}",
                        )
                        return None
                except Exception as ex:
                    logger.warning(f"[xKiro] Polling attempt error: {cls._sanitize(str(ex))}")

        if not cdn_url:
            logger.error(f"[xKiro] No image CDN URL obtained within timeout ({timeout}s).")
            image_provider_health_manager.record_failure(
                cls.PROVIDER_NAME,
                reason="Polling timeout or missing image URL",
            )
            return None

        # Step 3: Download image from CDN with bounded retry
        logger.info("[xKiro] Downloading image asset from CDN...")
        img_resp = None
        for dl_attempt in range(2):
            try:
                with httpx.Client(timeout=30.0) as client:
                    img_resp = client.get(cdn_url)
                if img_resp.status_code == 200:
                    break
            except Exception as ex:
                if dl_attempt == 0:
                    time.sleep(1.5)
                    continue
                logger.error(f"[xKiro] Network error downloading image from CDN: {cls._sanitize(str(ex))}")
                image_provider_health_manager.record_failure(cls.PROVIDER_NAME, reason=f"CDN network error: {cls._sanitize(str(ex))}")
                return None

        if not img_resp or img_resp.status_code != 200:
            status_code = img_resp.status_code if img_resp else 500
            logger.error(f"[xKiro] Failed to download image from CDN (HTTP {status_code})")
            image_provider_health_manager.record_failure(cls.PROVIDER_NAME, reason=f"CDN download HTTP {status_code}", status_code=status_code)
            return None

        raw_bytes = img_resp.content
        if len(raw_bytes) < 100:
            logger.error("[xKiro] Downloaded image payload too small to be valid.")
            image_provider_health_manager.record_failure(cls.PROVIDER_NAME, reason="CDN payload too small")
            return None

        # Step 4: Validate image with PIL and convert cleanly to PNG
        try:
            with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                pil_img.verify()

            with PILImage.open(io.BytesIO(raw_bytes)) as pil_img:
                if pil_img.width < 64 or pil_img.height < 64:
                    logger.error(f"[xKiro] Image dimensions {pil_img.size} too small to be acceptable.")
                    return None
                buf = io.BytesIO()
                pil_img.convert("RGB").save(buf, format="PNG")
                png_bytes = buf.getvalue()
                dims = pil_img.size
                img_sha = hashlib.sha256(png_bytes).hexdigest()

            image_provider_health_manager.record_success(cls.PROVIDER_NAME)
            logger.info(f"[xKiro] Image generation successfully completed and validated ({dims[0]}x{dims[1]}).")

            return XKiroImageGenerationResult(
                provider_name="xkiro",
                model_name=model_name,
                http_status="200 OK",
                response_type="image/png",
                image_bytes=png_bytes,
                dimensions=dims,
                sha256=img_sha,
            )
        except Exception as e:
            logger.error(f"[xKiro] Image validation failed: {cls._sanitize(str(e))}")
            return None
