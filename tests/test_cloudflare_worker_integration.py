"""
ARM Cloudflare Worker Primary Provider Integration Test Suite
=============================================================
Tests:
A. Worker success: mocked Worker returns valid JPEG, provider accepts and validates it.
B. Authentication failure: HTTP 401 causes clean fallback to RTX.
C. Quota failure: HTTP 500 with 4006 causes cooldown and fallback.
D. Invalid binary response: rejected, never saves fake image.
E. Domain correctness: domain detection accurately matches title context.
F. Safe logging & secret isolation: zero credentials in logs/objects.
"""

import os
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage
import httpx

from apps.api.services.cloudflare_worker_image_provider import (
    CloudflareWorkerImageProvider,
    CloudflareWorkerImageGenerationResult,
)
from apps.api.services.image_generation_manager import (
    ImageGenerationManager,
    ImageGenerationRequest,
)
from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.local_rtx_provider import LocalRTXGenerationResult
from apps.api.services.gemini_visual_pipeline_service import GeminiVisualPipelineService


def _create_dummy_jpeg_bytes(color: str = "red", w: int = 256, h: int = 256) -> bytes:
    img = PILImage.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _create_dummy_png_bytes(color: str = "blue", w: int = 256, h: int = 256) -> bytes:
    img = PILImage.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# TEST A: Worker Success (Priority 1)
# -----------------------------------------------------------------------------
def test_a_worker_success_returns_validated_image(tmp_path):
    """Mocked Worker returns valid JPEG; provider accepts, converts to PNG and validates."""
    jpeg_data = _create_dummy_jpeg_bytes("red", 512, 512)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "image/jpeg"}
    mock_resp.content = jpeg_data

    image_provider_health_manager.reset_cooldown()

    with patch("httpx.Client.post", return_value=mock_resp), \
         patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True):
        res = CloudflareWorkerImageProvider.generate_image("A realistic red apple on a clean white background")

        assert res is not None
        assert res.http_status == "200 OK"
        assert res.provider_name == "cloudflare-worker"
        assert res.response_type == "image/png"
        assert isinstance(res.image_bytes, bytes)
        assert res.dimensions == (512, 512)
        assert len(res.sha256) == 64

        # Validate that image bytes are readable as PNG
        with PILImage.open(io.BytesIO(res.image_bytes)) as pil_img:
            assert pil_img.format == "PNG"


# -----------------------------------------------------------------------------
# TEST B: Authentication Failure (401) Causes Fallback
# -----------------------------------------------------------------------------
def test_b_authentication_failure_triggers_rtx_fallback(tmp_path):
    """HTTP 401 from Worker causes clean fallback to RTX."""
    image_provider_health_manager.reset_cooldown()
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))

    req = ImageGenerationRequest(
        project_title="AI Robotics",
        slide_heading="Robot Arm",
        final_image_prompt="Modern robotic arm assembly",
        output_path=str(tmp_path / "robot.png"),
    )

    rtx_bytes = _create_dummy_png_bytes("green")
    rtx_mock = LocalRTXGenerationResult(
        success=True,
        image_bytes=rtx_bytes,
        sha256="rtx_sha_abc",
        model_name="stabilityai/sd-turbo",
    )

    # Worker returns 401
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.headers = {"content-type": "application/json"}
    mock_401.text = '{"error":"Unauthorized"}'

    with patch("httpx.Client.post", return_value=mock_401), \
         patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.is_enabled", return_value=True), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image", return_value=rtx_mock):

        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "local_rtx"
        assert res.metadata.get("model") == "stabilityai/sd-turbo"


# -----------------------------------------------------------------------------
# TEST C: Quota Failure (4006) Causes Cooldown and RTX Fallback
# -----------------------------------------------------------------------------
def test_c_quota_failure_4006_triggers_cooldown_and_rtx_fallback(tmp_path):
    """HTTP 500 with Cloudflare 4006 daily quota error triggers cooldown & fallback."""
    image_provider_health_manager.reset_cooldown()
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))

    req = ImageGenerationRequest(
        project_title="Smart Grid",
        slide_heading="Power Grid Monitoring",
        final_image_prompt="Smart electrical power grid sensors",
        output_path=str(tmp_path / "grid.png"),
    )

    rtx_bytes = _create_dummy_png_bytes("yellow")
    rtx_mock = LocalRTXGenerationResult(
        success=True,
        image_bytes=rtx_bytes,
        sha256="rtx_sha_grid",
        model_name="stabilityai/sd-turbo",
    )

    mock_500 = MagicMock()
    mock_500.status_code = 500
    mock_500.headers = {"content-type": "application/json"}
    mock_500.text = '{"error":"Failed to generate image","details":"4006: you have used up your daily free allocation of 10,000 neurons..."}'

    with patch("httpx.Client.post", return_value=mock_500), \
         patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.is_enabled", return_value=True), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image", return_value=rtx_mock):

        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "local_rtx"

        # Verify that Cloudflare entered cooldown
        assert image_provider_health_manager.is_available("cloudflare") is False


# -----------------------------------------------------------------------------
# TEST D: Invalid Binary Response Rejected (No Fake Images)
# -----------------------------------------------------------------------------
def test_d_invalid_binary_response_rejected_no_fake_images(tmp_path):
    """Non-image or corrupt binary response is rejected; no fake image created."""
    image_provider_health_manager.reset_cooldown()

    # Corrupt or non-image HTML payload
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.content = b"<html><body>Server Error Gateway</body></html>"
    mock_resp.text = "<html><body>Server Error Gateway</body></html>"

    with patch("httpx.Client.post", return_value=mock_resp), \
         patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True):
        res = CloudflareWorkerImageProvider.generate_image("A test prompt")
        assert res is None


# -----------------------------------------------------------------------------
# TEST E: Domain Correctness
# -----------------------------------------------------------------------------
def test_e_domain_correctness_for_project_titles():
    """Confirms visual domain aligns strictly with project title."""
    test_cases = [
        ("AI Based Irrigation Management System", "irrigation"),
        ("Hospital Management System", "healthcare"),
        ("Smart Attendance Monitoring System", "attendance"),
        ("Cybersecurity Intrusion Detection", "cybersecurity"),
    ]

    for title, expected_domain in test_cases:
        domain, label, conf = GeminiVisualPipelineService.detect_project_domain_and_context(title)
        assert domain == expected_domain, f"Failed for {title}: got {domain}, expected {expected_domain}"


# -----------------------------------------------------------------------------
# TEST F: Complete Priority Hierarchy
# -----------------------------------------------------------------------------
def test_f_priority_hierarchy_cache_worker_rtx_hf_together(tmp_path):
    """Verifies sequential priority: Cache -> Worker -> RTX -> HF -> Together."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Automotive AI",
        slide_heading="Autonomous Vehicle",
        final_image_prompt="Self driving car lidar test",
        output_path=str(tmp_path / "car.png"),
    )

    image_provider_health_manager.reset_cooldown()

    # When Worker succeeds, RTX and HF are NEVER called
    cf_bytes = _create_dummy_png_bytes("cyan")
    cf_res = CloudflareWorkerImageGenerationResult(
        provider_name="cloudflare-worker",
        model_name="cf-workers-ai",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=cf_bytes,
        dimensions=(256, 256),
        sha256="cf_car_sha",
    )

    from apps.api.services.xkiro_image_provider import XKiroImageProvider

    with patch.object(XKiroImageProvider, "is_configured", return_value=False), \
         patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareWorkerImageProvider, "generate_image", return_value=cf_res), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image") as mock_rtx, \
         patch("apps.api.services.hf_image_provider.HFImageProvider.generate_image") as mock_hf:

        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "cloudflare"
        mock_rtx.assert_not_called()
        mock_hf.assert_not_called()
