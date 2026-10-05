"""
ARM xKiro Provider Integration Test Suite
=========================================
Tests:
A. Provider configuration & free-only safety check.
B. Free quota exhaustion blocks execution without paid charges.
C. Mocked async generation: submit job -> poll -> download CDN image -> PIL validate.
D. ImageGenerationManager Priority: Cache -> xKiro (Primary) -> Cloudflare (Fallback).
E. GPU/RTX is strictly disabled (never called).
F. Zero secret exposure in errors or logs.
"""

import os
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage
import httpx

from apps.api.services.xkiro_image_provider import (
    XKiroImageProvider,
    XKiroImageGenerationResult,
)
from apps.api.services.image_generation_manager import (
    ImageGenerationManager,
    ImageGenerationRequest,
)
from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageProvider
from apps.api.services.local_rtx_provider import LocalRTXProvider


def _create_dummy_png_bytes(color: str = "green", w: int = 512, h: int = 512) -> bytes:
    img = PILImage.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# TEST 1: Configuration Detection & Free-Only Setting
# -----------------------------------------------------------------------------
def test_1_xkiro_configuration_and_free_only():
    with patch.dict(os.environ, {"XKIRO_API_KEY": "sk-xt-test-12345", "XKIRO_FREE_ONLY": "true"}):
        assert XKiroImageProvider.is_configured() is True
        assert XKiroImageProvider.is_free_only() is True
        assert XKiroImageProvider.get_model_name() == "sensenova/sensenova-u1.5-lite"

    with patch.dict(os.environ, {"XKIRO_API_KEY": ""}, clear=True):
        assert XKiroImageProvider.is_configured() is False


# -----------------------------------------------------------------------------
# TEST 2: Free Allowance Exhaustion Blocks Paid Charges
# -----------------------------------------------------------------------------
def test_2_free_allowance_exhaustion_blocks_generation():
    """If free tokens remaining is 0, generation must NOT proceed."""
    mock_usage_resp = MagicMock()
    mock_usage_resp.status_code = 200
    mock_usage_resp.json.return_value = {
        "object": "usage",
        "free_tokens": {
            "used_today": 500000,
            "limit_per_day": 500000,
            "remaining": 0,
        },
        "wallet": {
            "balance_usd": "10.000000",
        },
    }

    image_provider_health_manager.reset_cooldown()

    with patch.dict(os.environ, {"XKIRO_API_KEY": "sk-xt-test-12345", "XKIRO_FREE_ONLY": "true"}), \
         patch("httpx.Client.get", return_value=mock_usage_resp):
        allowed, reason = XKiroImageProvider.check_free_quota()
        assert allowed is False
        assert "exhausted" in reason.lower()

        res = XKiroImageProvider.generate_image("Smart Irrigation System")
        assert res is None


# -----------------------------------------------------------------------------
# TEST 3: Mocked Full Async Flow (Submit -> Poll -> Download -> Validate)
# -----------------------------------------------------------------------------
def test_3_full_async_flow_succeeds(tmp_path):
    image_provider_health_manager.reset_cooldown()
    fake_png = _create_dummy_png_bytes("teal", 1024, 1024)

    # 1. Quota check response (200 OK, remaining > 0)
    mock_usage_resp = MagicMock()
    mock_usage_resp.status_code = 200
    mock_usage_resp.json.return_value = {
        "free_tokens": {"used_today": 1, "remaining": 499999, "limit_per_day": 500000}
    }

    # 2. Submit response (202 Accepted, Job ID)
    mock_submit_resp = MagicMock()
    mock_submit_resp.status_code = 202
    mock_submit_resp.json.return_value = {
        "id": "job-test-uuid-456",
        "status": "processing",
    }

    # 3. Poll response (200 OK, succeeded, CDN URL)
    mock_poll_resp = MagicMock()
    mock_poll_resp.status_code = 200
    mock_poll_resp.json.return_value = {
        "id": "job-test-uuid-456",
        "status": "succeeded",
        "data": [{"url": "https://cdn.xkiro.com/ai-image-generator/job-test-uuid-456/0.png"}],
    }

    # 4. CDN download response
    mock_cdn_resp = MagicMock()
    mock_cdn_resp.status_code = 200
    mock_cdn_resp.content = fake_png

    def fake_get(url, *args, **kwargs):
        if "/v1/usage" in url:
            return mock_usage_resp
        elif "/v1/images/generations/job-test-uuid-456" in url:
            return mock_poll_resp
        elif "cdn.xkiro.com" in url:
            return mock_cdn_resp
        return MagicMock(status_code=404)

    with patch.dict(os.environ, {"XKIRO_API_KEY": "sk-xt-test-secret-key"}), \
         patch("httpx.Client.post", return_value=mock_submit_resp), \
         patch("httpx.Client.get", side_effect=fake_get), \
         patch("time.sleep", return_value=None):
        res = XKiroImageProvider.generate_image("AI based smart irrigation system")

        assert res is not None
        assert res.provider_name == "xkiro"
        assert res.model_name == "sensenova/sensenova-u1.5-lite"
        assert res.http_status == "200 OK"
        assert res.response_type == "image/png"
        assert res.dimensions == (1024, 1024)
        assert len(res.sha256) == 64

        # Validate with PIL
        with PILImage.open(io.BytesIO(res.image_bytes)) as pil_img:
            assert pil_img.format == "PNG"


# -----------------------------------------------------------------------------
# TEST 4: ImageGenerationManager Priority (xKiro is Primary, Worker is Fallback)
# -----------------------------------------------------------------------------
def test_4_manager_priority_xkiro_over_cloudflare(tmp_path):
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Smart Irrigation",
        slide_heading="Field Deployment",
        final_image_prompt="High tech smart irrigation sensors in crop field",
        output_path=str(tmp_path / "irrigation.png"),
    )

    image_provider_health_manager.reset_cooldown()

    xkiro_png = _create_dummy_png_bytes("green", 1024, 1024)
    xkiro_res = XKiroImageGenerationResult(
        provider_name="xkiro",
        model_name="sensenova/sensenova-u1.5-lite",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=xkiro_png,
        dimensions=(1024, 1024),
        sha256="sha_xkiro_123",
    )

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", return_value=xkiro_res), \
         patch.object(CloudflareWorkerImageProvider, "generate_image") as mock_cf, \
         patch.object(LocalRTXProvider, "generate_image") as mock_rtx:
        res = mgr.generate_image(req)

        assert res.success is True
        assert res.source == "xkiro"
        assert res.metadata.get("model") == "sensenova/sensenova-u1.5-lite"
        # Cloudflare and RTX must NEVER be called when xKiro succeeds
        mock_cf.assert_not_called()
        mock_rtx.assert_not_called()


# -----------------------------------------------------------------------------
# TEST 5: GPU/RTX is Never Used
# -----------------------------------------------------------------------------
def test_5_gpu_rtx_strictly_disabled():
    assert LocalRTXProvider.is_enabled() is False
    hw = LocalRTXProvider.get_hardware_status()
    assert hw["gpu_detected"] is False
    res = LocalRTXProvider.generate_image("Test")
    assert res.success is False
    assert res.status == "DISABLED"


# -----------------------------------------------------------------------------
# TEST 6: Zero Secret Exposure
# -----------------------------------------------------------------------------
def test_6_zero_secret_exposure():
    secret_key = "sk-xt-super-secret-production-token-999"
    with patch.dict(os.environ, {"XKIRO_API_KEY": secret_key}):
        err_msg = f"Failed to authenticate with bearer {secret_key}"
        sanitized = XKiroImageProvider._sanitize(err_msg)
        assert secret_key not in sanitized
        assert "***REDACTED***" in sanitized
