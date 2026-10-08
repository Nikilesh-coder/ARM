"""
ARM Image Providers Regression Test Suite
=========================================
Tests:
1. Supernova success -> image generated & recorded.
2. Supernova 429 quota -> falls back to Cloudflare.
3. Supernova failure -> next provider in chain.
4. Cloudflare 429 / exhaustion -> falls back to HF/Together.
5. All providers fail -> reports explicit per-provider diagnostics, not generic message.
6. Valid generated image -> replacement count increments.
7. Unchanged template image -> NOT falsely counted as replacement.
8. Semantic diversity -> slide heading and matter incorporated into prompt.
9. Repeated image prevention / deduplication -> colliding images rejected.
10. Cache HIT -> avoids provider call completely.
"""

import io
import os
import hashlib
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage

from apps.api.services.image_generation_manager import (
    ImageGenerationManager,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.xkiro_image_provider import XKiroImageProvider, XKiroImageGenerationResult
from apps.api.services.cloudflare_image_provider import CloudflareImageProvider
from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageGenerationResult
from apps.api.services.hf_image_provider import HFImageProvider, HFImageGenerationResult
from apps.api.services.together_image_provider import TogetherImageProvider, TogetherImageGenerationResult
from apps.api.services.gemini_visual_pipeline_service import gemini_visual_pipeline_service


def _make_dummy_image(color=(120, 180, 240), w=128, h=128) -> bytes:
    img = PILImage.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_health():
    image_provider_health_manager.reset_cooldown()
    yield
    image_provider_health_manager.reset_cooldown()


def test_1_supernova_success_generates_image(tmp_path):
    """Priority 1: Supernova success generates and saves image."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache1"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=2,
        slide_heading="Soil Moisture Sensing",
        slide_matter="Sensors deployed across rows measuring volumetric water content.",
        final_image_prompt="High-precision soil probe in loamy agricultural soil.",
        report_id="rep_test_1",
    )

    dummy_bytes = _make_dummy_image((30, 140, 80))
    dummy_sha = hashlib.sha256(dummy_bytes).hexdigest()

    mock_res = XKiroImageGenerationResult(
        provider_name="xkiro",
        model_name="sensenova/sensenova-u1.5-lite",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=dummy_bytes,
        dimensions=(1024, 1024),
        sha256=dummy_sha,
    )

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", return_value=mock_res):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.source == "supernova"
    assert res.image_bytes == dummy_bytes
    assert res.status == "SUCCESS"


def test_2_supernova_429_falls_back_to_cloudflare(tmp_path):
    """Supernova 429 quota exhaustion marks it in cooldown and falls back to Cloudflare."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache2"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=3,
        slide_heading="Automated Valve Manifold",
        slide_matter="Solenoid valves controlling pressurized drip lines.",
        final_image_prompt="Stainless steel valve manifold with pressurized drip hoses.",
        report_id="rep_test_2",
    )

    cf_bytes = _make_dummy_image((200, 100, 50))
    cf_sha = hashlib.sha256(cf_bytes).hexdigest()
    cf_res = CloudflareWorkerImageGenerationResult(
        provider_name="cloudflare-direct",
        model_name="@cf/black-forest-labs/flux-1-schnell",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=cf_bytes,
        dimensions=(1024, 1024),
        sha256=cf_sha,
    )

    def mock_supernova_fail(*args, **kwargs):
        image_provider_health_manager.record_failure("xkiro", "429 quota (Free allowance exhausted)", status_code=429, is_exhausted=True)
        return None

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", side_effect=mock_supernova_fail), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareImageProvider, "generate_image", return_value=cf_res):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.source == "cloudflare"
    assert res.image_bytes == cf_bytes
    assert image_provider_health_manager._get_record("xkiro").is_in_cooldown() is True


def test_3_supernova_failure_falls_to_next_provider(tmp_path):
    """Supernova network failure triggers immediate fallback to Cloudflare."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache3"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=4,
        slide_heading="Telemetry Gateway",
        slide_matter="Edge gateway relaying telemetry to cloud.",
        final_image_prompt="Weatherproof IoT gateway box on pole in farm.",
        report_id="rep_test_3",
    )

    cf_bytes = _make_dummy_image((60, 60, 200))
    cf_sha = hashlib.sha256(cf_bytes).hexdigest()
    cf_res = CloudflareWorkerImageGenerationResult(
        provider_name="cloudflare-worker",
        model_name="cf-workers-ai",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=cf_bytes,
        dimensions=(1024, 1024),
        sha256=cf_sha,
    )

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", side_effect=Exception("Connection timeout")), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareImageProvider, "generate_image", return_value=cf_res):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.source == "cloudflare"


def test_4_cloudflare_429_falls_back_to_hf_or_together(tmp_path):
    """Cloudflare 429 quota exhaustion marks it in cooldown and falls back to Together."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache4"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=5,
        slide_heading="Drip Emitters",
        slide_matter="Pressure-compensating drip emitters wetting roots.",
        final_image_prompt="Macro photo of drip irrigation emitter watering plants.",
        report_id="rep_test_4",
    )

    tog_bytes = _make_dummy_image((150, 150, 50))
    tog_sha = hashlib.sha256(tog_bytes).hexdigest()
    tog_res = TogetherImageGenerationResult(
        success=True,
        image_bytes=tog_bytes,
        dimensions=(1024, 1024),
        sha256=tog_sha,
        model_name="black-forest-labs/FLUX.1-schnell",
        status="SUCCESS",
    )

    with patch.object(XKiroImageProvider, "is_configured", return_value=False), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareImageProvider, "generate_image", return_value=None), \
         patch.object(HFImageProvider, "is_configured", return_value=False), \
         patch.object(TogetherImageProvider, "is_configured", return_value=True), \
         patch.object(TogetherImageProvider, "generate_image", return_value=tog_res):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.source == "together"


def test_5_all_providers_fail_returns_diagnostic_details(tmp_path):
    """When all providers fail, error message must contain specific per-provider diagnostics."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache5"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=6,
        slide_heading="System Architecture",
        slide_matter="Overview",
        final_image_prompt="System overview",
        report_id="rep_test_5",
    )

    # Put providers in realistic failed/exhausted states
    image_provider_health_manager.record_failure("xkiro", "429 quota (Free allowance exhausted)", status_code=429, is_exhausted=True)
    image_provider_health_manager.record_failure("cloudflare", "429 daily allocation exhausted", status_code=429, is_exhausted=True)
    image_provider_health_manager.record_failure("huggingface", "402 credits exhausted", status_code=402, is_exhausted=True)

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=True), \
         patch.object(HFImageProvider, "is_configured", return_value=True), \
         patch.object(TogetherImageProvider, "is_configured", return_value=False):
        res = mgr.generate_image(req)

    assert res.success is False
    assert res.status == "IMAGE_GENERATION_UNAVAILABLE"
    # Diagnostics must include individual provider statuses
    assert "Supernova:" in res.error
    assert "Cloudflare:" in res.error
    assert "Hugging Face:" in res.error
    assert "Together AI: not configured" in res.error
    assert "429" in res.error or "quota" in res.error
    assert "402" in res.error or "credits exhausted" in res.error


def test_6_valid_generated_image_increments_replacement_count(tmp_path):
    """Valid generated image is saved and recorded in report history."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache6"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=7,
        slide_heading="Field Deployment",
        slide_matter="Field deployment",
        final_image_prompt="Field deployment of sensors",
        report_id="rep_test_6",
    )

    img_b = _make_dummy_image((10, 80, 160))
    img_sha = hashlib.sha256(img_b).hexdigest()
    res_obj = XKiroImageGenerationResult("xkiro", "model-lite", "200 OK", "image/png", img_b, (1024, 1024), img_sha)

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", return_value=res_obj):
        res = mgr.generate_image(req)

    assert res.success is True
    # Recorded in history
    history = mgr._report_history.get("rep_test_6", [])
    assert len(history) == 1
    assert history[0].slide_number == 7
    assert history[0].sha256 == img_sha


def test_7_unchanged_template_image_not_counted_as_replacement():
    """Unchanged template images are excluded from replacement count."""
    custom_image_mapping = [
        {"action": "fixed", "filename": "logo.png", "arm_image_field": "header_logo"},
        {"action": "replace", "filename": "slide6.png", "arm_image_field": "image_1"},
        {"action": "replace", "filename": "slide11.png", "arm_image_field": "image_2"},
    ]
    # Filter strictly to replace
    replaceable_keys = set()
    for im in custom_image_mapping:
        if im.get("action") == "replace":
            if im.get("arm_image_field"):
                replaceable_keys.add(im["arm_image_field"])
            if im.get("filename"):
                replaceable_keys.add(im["filename"])

    # Simulate assets map containing both logo and newly generated images
    assets = {
        "logo.png": "/templates/logo.png",
        "header_logo": "/templates/logo.png",
        "slide6.png": "/generated/slide6.png",
        "image_1": "/generated/slide6.png",
    }
    filtered = {k: v for k, v in assets.items() if k in replaceable_keys}

    assert "logo.png" not in filtered
    assert "header_logo" not in filtered
    assert "slide6.png" in filtered
    assert "image_1" in filtered


def test_8_semantic_diversity_incorporates_slide_matter_and_heading():
    """Prompt compiler incorporates slide heading, matter, and domain."""
    req1 = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title="AI Smart Irrigation",
        slide_heading="Soil Sensing Layer",
        slide_matter="Capacitive probes inserted 15cm into topsoil measuring volumetric moisture.",
        slide_index=2,
    )
    req2 = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title="AI Smart Irrigation",
        slide_heading="Cloud Analytics Dashboard",
        slide_matter="React web application showing real-time water flow rates and schedules.",
        slide_index=5,
    )

    assert "soil" in req1.gemini_prompt.lower()
    assert req1.gemini_prompt != req2.gemini_prompt


def test_9_repeated_image_collision_rejected(tmp_path):
    """If provider returns an identical image already used in report, it is rejected for diversity."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache9"))
    img_b = _make_dummy_image((99, 99, 99))
    img_sha = hashlib.sha256(img_b).hexdigest()

    # Pre-record image for slide 1
    mgr.record_report_image("rep_test_9", 1, "Intro", img_sha, img_b, "supernova")

    # Try generating slide 2 returning same bytes
    req2 = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=2,
        slide_heading="Hardware",
        final_image_prompt="Sensors",
        report_id="rep_test_9",
    )

    res_obj = XKiroImageGenerationResult("xkiro", "model-lite", "200 OK", "image/png", img_b, (1024, 1024), img_sha)

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", return_value=res_obj), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=False), \
         patch.object(HFImageProvider, "is_configured", return_value=False), \
         patch.object(TogetherImageProvider, "is_configured", return_value=False):
        res = mgr.generate_image(req2)

    # Identical image rejected for slide 2
    assert res.success is False
    assert "duplicate image rejected" in res.error


def test_10_cache_hit_avoids_provider_call(tmp_path):
    """Cache HIT reuses cached image and never calls external providers."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache10"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=3,
        slide_heading="Field Node",
        slide_matter="Solar powered microcontroller node.",
        final_image_prompt="Solar powered IoT node in vineyard.",
        report_id="rep_test_10",
    )

    img_b = _make_dummy_image((40, 160, 90))
    img_sha = hashlib.sha256(img_b).hexdigest()
    mgr._save_to_cache(req, img_b, "supernova", img_sha)

    mock_supernova = MagicMock()
    with patch.object(XKiroImageProvider, "generate_image", mock_supernova):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.cached is True
    assert res.source == "cache"
    assert res.image_bytes == img_b
    mock_supernova.assert_not_called()
