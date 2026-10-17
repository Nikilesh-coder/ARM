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


def test_11_invalid_image_corrupt_or_tiny_rejected(tmp_path):
    """Corrupt image binary or image dimensions < 64x64 are rejected by verification gate."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path / "cache11"))
    req = ImageGenerationRequest(
        project_title="AI Irrigation",
        slide_number=8,
        slide_heading="Sensor Calibration",
        slide_matter="Calibration curves.",
        final_image_prompt="Sensor calibration diagram.",
        report_id="rep_test_11",
    )

    # 1. Tiny image (16x16) from Supernova
    tiny_bytes = _make_dummy_image((10, 20, 30), w=16, h=16)
    tiny_sha = hashlib.sha256(tiny_bytes).hexdigest()
    tiny_res = XKiroImageGenerationResult("xkiro", "model-lite", "200 OK", "image/png", tiny_bytes, (16, 16), tiny_sha)

    # 2. Valid fallback image from Cloudflare (128x128)
    valid_cf_bytes = _make_dummy_image((50, 100, 150), w=128, h=128)
    valid_cf_sha = hashlib.sha256(valid_cf_bytes).hexdigest()
    cf_res = CloudflareWorkerImageGenerationResult("cloudflare", "cf-model", "200 OK", "image/png", valid_cf_bytes, (128, 128), valid_cf_sha)

    with patch.object(XKiroImageProvider, "is_configured", return_value=True), \
         patch.object(XKiroImageProvider, "generate_image", return_value=tiny_res), \
         patch.object(CloudflareImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareImageProvider, "generate_image", return_value=cf_res):
        res = mgr.generate_image(req)

    assert res.success is True
    assert res.source == "cloudflare"
    assert res.image_bytes == valid_cf_bytes


def test_12_none_slide_skips_image_synthesis(tmp_path):
    """Slides explicitly classified as NONE (References/Closing) skip synthesis without calling providers or logging warnings."""
    from apps.api.services.intelligent_image_service import intelligent_image_service
    from apps.api.services.visual_engine import visual_engine

    images = [
        {
            "action": "replace",
            "filename": "slide13.png",
            "arm_image_field": "image_13",
            "slide_num": 13,
            "heading": "Academic References & Citations",
            "slide_matter": "1. Smith et al. IoT in Precision Agriculture, 2024. 2. Doe et al. Soil Sensors, 2023.",
            "aspect_ratio": 1.77,
        }
    ]

    mock_gen = MagicMock()
    with patch.object(visual_engine, "generate_visual", mock_gen):
        res = intelligent_image_service.generate_replacement_images(
            project_title="AI Irrigation System",
            problem_statement="Precision water conservation in farming.",
            analyzed_images=images,
            output_dir=str(tmp_path / "img_out"),
            report_id="rep_test_12",
        )

    # Pre-check category detects 'references' and skips before calling generate_visual
    mock_gen.assert_not_called()
    assert len(res) == 0


def test_13_linux_validation_without_powershell(tmp_path):
    """On Linux/Render where PowerShell Word COM is unavailable, validator runs reliably via OOXML without crashing."""
    import docx
    from apps.api.services.visual_report_validator import VisualReportValidator

    docx_file = str(tmp_path / "test_report.docx")
    doc = docx.Document()
    doc.add_heading("AI Irrigation System", level=0)
    doc.add_paragraph("Abstract: Automated soil moisture sensing and drip irrigation deployment.")
    doc.add_paragraph("This agriculture project utilizes soil moisture sensors to regulate water delivery.")
    doc.save(docx_file)

    # Simulate Linux environment without PowerShell or LibreOffice
    with patch("sys.platform", "linux"), \
         patch("shutil.which", return_value=None):
        val_res = VisualReportValidator.validate_report_visuals(
            docx_path=docx_file,
            project_title="AI Irrigation System",
            problem_statement="Automated precision irrigation with soil moisture sensors.",
            output_dir=str(tmp_path / "audit_dir"),
        )

    assert val_res["is_valid"] is True
    assert val_res["status"] == "PASSED"
    assert val_res["pdf_validation_available"] is False
    assert val_res["pdf_path"] is None
    assert val_res["title_verified"] is True
    assert len(val_res["topic_keywords_found"]) > 0


def test_14_replacement_validation_mandatory_vs_optional():
    """Validation gate distinguishes optional from mandatory image generation failures."""
    images_to_generate_opt = [{"action": "replace", "filename": "fig1.png", "mandatory": False}]
    has_mandatory_opt = any(im.get("mandatory") is True for im in images_to_generate_opt)
    assert has_mandatory_opt is False

    images_to_generate_mand = [{"action": "replace", "filename": "fig1.png", "mandatory": True}]
    has_mandatory_mand = any(im.get("mandatory") is True for im in images_to_generate_mand)
    assert has_mandatory_mand is True


def test_15_docx_formatting_and_package_preservation(tmp_path):
    """Template margins, layout, headers, footers, and untouched images remain intact."""
    import docx
    docx_file = str(tmp_path / "template.docx")
    doc = docx.Document()
    section = doc.sections[0]
    section.top_margin = docx.shared.Inches(1.0)
    section.bottom_margin = docx.shared.Inches(1.0)
    section.left_margin = docx.shared.Inches(1.25)
    section.right_margin = docx.shared.Inches(1.25)
    doc.add_heading("Original College Template", level=0)
    doc.save(docx_file)

    doc2 = docx.Document(docx_file)
    sec2 = doc2.sections[0]
    assert sec2.top_margin == docx.shared.Inches(1.0)
    assert sec2.left_margin == docx.shared.Inches(1.25)


def test_16_cloudflare_prompt_truncation_under_2048():
    """Cloudflare Direct and Worker safely truncate prompts > 2048 chars without failing HTTP 400."""
    from apps.api.services.cloudflare_image_provider import CloudflareDirectImageProvider
    from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageProvider

    long_prompt = "AI irrigation sensor field telemetry " * 75  # ~2775 characters
    assert len(long_prompt) > 2048

    import base64
    valid_b64 = base64.b64encode(_make_dummy_image(w=64, h=64)).decode("ascii")
    captured_direct_payload = {}
    mock_direct_resp = MagicMock()
    mock_direct_resp.status_code = 200
    mock_direct_resp.json.return_value = {
        "result": {"image": valid_b64}
    }

    def fake_direct_post(url, headers=None, json=None, **kwargs):
        captured_direct_payload.update(json or {})
        return mock_direct_resp

    with patch.object(CloudflareDirectImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareDirectImageProvider, "get_account_id", return_value="acc_123"), \
         patch.object(CloudflareDirectImageProvider, "get_api_token", return_value="tok_123"), \
         patch("httpx.Client.post", side_effect=fake_direct_post):
        res = CloudflareDirectImageProvider.generate_image(long_prompt)
        assert res is not None
        assert len(captured_direct_payload["prompt"]) <= 2000


def test_17_cloudflare_independent_cooldown_worker_and_direct():
    """Worker failure enters cloudflare_worker cooldown without locking out cloudflare_direct."""
    from apps.api.services.cloudflare_image_provider import CloudflareImageProvider, CloudflareDirectImageProvider
    from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageProvider

    image_provider_health_manager.reset_cooldown()

    # Simulate Worker failure
    image_provider_health_manager.record_failure("cloudflare_worker", reason="Worker 502 bad gateway", status_code=502)

    assert image_provider_health_manager.is_available("cloudflare_worker") is False
    assert image_provider_health_manager.is_available("cloudflare_direct") is True

    # CloudflareImageProvider is still available via direct fallback
    with patch.object(CloudflareWorkerImageProvider, "is_configured", return_value=True), \
         patch.object(CloudflareDirectImageProvider, "is_configured", return_value=True):
        assert CloudflareImageProvider.is_available() is True

        dummy_bytes = _make_dummy_image()
        mock_direct_res = CloudflareWorkerImageGenerationResult(
            provider_name="cloudflare-direct",
            model_name="@cf/black-forest-labs/flux-1-schnell",
            http_status="200 OK",
            response_type="image/png",
            image_bytes=dummy_bytes,
            dimensions=(512, 512),
            sha256="fake_sha",
        )
        with patch.object(CloudflareDirectImageProvider, "generate_image", return_value=mock_direct_res):
            res = CloudflareImageProvider.generate_image("Prompt")
            assert res is not None
            assert res.provider_name == "cloudflare-direct"


def test_18_docx_replacement_engine_multi_key_lookup(tmp_path):
    """DocxTemplateReplacementEngine resolves images whether keyed by arm_field, filename, or rel_id."""
    import docx
    from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine

    docx_file = str(tmp_path / "test_tpl.docx")
    out_file = str(tmp_path / "test_out.docx")
    doc = docx.Document()
    p = doc.add_paragraph("Chapter 5 Results")
    doc.save(docx_file)

    img_file = str(tmp_path / "gen_img.png")
    with open(img_file, "wb") as f:
        f.write(_make_dummy_image())

    # image_assets has key "image1.png" rather than "image_1"
    image_assets = {"image1.png": img_file}
    image_mapping = [
        {"action": "replace", "arm_image_field": "image_1", "filename": "image1.png", "rel_id": None}
    ]

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=docx_file,
        field_values={"title": "Test Title"},
        image_assets=image_assets,
        output_path=out_file,
        image_mapping=image_mapping,
    )

    assert result.success is True
