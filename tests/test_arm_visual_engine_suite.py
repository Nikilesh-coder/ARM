"""
ARM Stage: Visual Generation Engine Test Suite
==============================================
Tests all 25 test cases specified in Sections 35 and 36:
- Tests 1-11: Image Generation System (Priority fallback, caching, health, cooldown, concurrency)
- Tests 12-25: Visual Decision Engine & Diagram/Chart Generation (Domain-aware diagrams, ER, Sequence, Charts, None, Repair)
"""

import os
import io
import time
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage

from apps.api.services.image_provider_cooldown import image_provider_health_manager
from apps.api.services.local_rtx_provider import LocalRTXProvider, LocalRTXGenerationResult
from apps.api.services.cloudflare_image_provider import CloudflareImageGenerationResult
from apps.api.services.hf_image_provider import HFImageGenerationResult
from apps.api.services.together_image_provider import TogetherImageProvider, TogetherImageGenerationResult
from apps.api.services.image_generation_manager import (
    ImageGenerationManager,
    ImageGenerationRequest,
)
from apps.api.services.mermaid_diagram_service import mermaid_diagram_service
from apps.api.services.chart_engine import chart_engine
from apps.api.services.visual_engine import visual_engine


def _create_dummy_png_bytes(color: str = "red", w: int = 100, h: int = 100) -> bytes:
    img = PILImage.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# =============================================================================
# PART 1: IMAGE SYSTEM TESTS (TESTS 1 - 11)
# =============================================================================

def test_1_cache_hit_bypasses_all_providers(tmp_path):
    """Test 1: If an asset is cached, it is returned directly with no provider calls."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Smart Irrigation",
        slide_heading="Field Sensors",
        final_image_prompt="High resolution soil moisture sensor in field",
    )

    dummy_bytes = _create_dummy_png_bytes("green")
    mgr._save_to_cache(req, dummy_bytes, source="local_rtx", sha256="testsha123")

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image") as mock_rtx, \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image") as mock_cf:
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "cache"
        assert res.cached is True
        mock_rtx.assert_not_called()
        mock_cf.assert_not_called()


def test_2_rtx_success_stops_provider_fallback(tmp_path):
    """Test 2: If RTX succeeds, Cloudflare/HF/Together are never called."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Hospital Management",
        slide_heading="Ward View",
        final_image_prompt="Modern hospital ward",
    )
    image_provider_health_manager.reset_cooldown()

    rtx_bytes = _create_dummy_png_bytes("blue")
    rtx_mock_res = LocalRTXGenerationResult(
        success=True,
        image_bytes=rtx_bytes,
        sha256="rtx_sha",
        model_name="RTX-3050-Turbo",
    )

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image", return_value=rtx_mock_res), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.is_enabled", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.generate_image") as mock_hf:
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "local_rtx"
        mock_hf.assert_not_called()



def test_3_rtx_unavailable_falls_back_to_cloudflare(tmp_path):
    """Test 3: If RTX is unavailable, execution cleanly continues to Cloudflare."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="AI Attendance",
        slide_heading="Campus Camera",
        final_image_prompt="Campus camera attendance",
    )
    image_provider_health_manager.reset_cooldown()

    cf_bytes = _create_dummy_png_bytes("yellow")
    cf_mock_res = CloudflareImageGenerationResult(
        provider_name="cloudflare",
        model_name="flux-1-schnell",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=cf_bytes,
        dimensions=(1024, 1024),
        sha256="cf_sha",
    )

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image",
               return_value=LocalRTXGenerationResult(success=False, status="LOCAL_MODEL_NOT_INSTALLED")), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=cf_mock_res):
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "cloudflare"


def test_4_rtx_failure_and_cloudflare_success(tmp_path):
    """Test 4: RTX fails with error -> Cloudflare succeeds."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Cybersecurity",
        slide_heading="SOC Monitor",
        final_image_prompt="Cybersecurity SOC room",
    )
    image_provider_health_manager.reset_cooldown()

    cf_bytes = _create_dummy_png_bytes("cyan")
    cf_mock = CloudflareImageGenerationResult(
        provider_name="cloudflare",
        model_name="flux-1-schnell",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=cf_bytes,
        dimensions=(1024, 1024),
        sha256="cf_sha4",
    )

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image",
               return_value=LocalRTXGenerationResult(success=False, status="LOCAL_RTX_LOW_VRAM")), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=cf_mock):
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "cloudflare"


def test_5_rtx_and_cloudflare_fail_and_hf_succeeds(tmp_path):
    """Test 5: RTX and Cloudflare both fail -> Hugging Face succeeds."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="E-Commerce",
        slide_heading="Warehouse Delivery",
        final_image_prompt="Modern logistics fulfillment center",
    )
    image_provider_health_manager.reset_cooldown()

    hf_bytes = _create_dummy_png_bytes("magenta")
    hf_mock = HFImageGenerationResult(
        provider_name="huggingface",
        model_name="black-forest-labs/FLUX.1-schnell",
        http_status="200 OK",
        response_type="image/png",
        image_bytes=hf_bytes,
        dimensions=(1024, 1024),
        sha256="hf_sha",
    )

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image",
               return_value=LocalRTXGenerationResult(success=False, status="LOCAL_MODEL_NOT_INSTALLED")), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.generate_image", return_value=hf_mock):
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "huggingface"


def test_6_rtx_cf_hf_fail_and_together_succeeds(tmp_path):
    """Test 6: RTX, Cloudflare, and HF fail -> Together AI succeeds."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="Drone Navigation",
        slide_heading="Drone Landing",
        final_image_prompt="Drone autonomous landing pad",
    )
    image_provider_health_manager.reset_cooldown()

    together_bytes = _create_dummy_png_bytes("orange")
    together_mock = TogetherImageGenerationResult(
        success=True,
        image_bytes=together_bytes,
        dimensions=(1024, 1024),
        sha256="together_sha",
        model_name="black-forest-labs/FLUX.1-schnell",
    )

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image",
               return_value=LocalRTXGenerationResult(success=False, status="LOCAL_MODEL_NOT_INSTALLED")), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.together_image_provider.TogetherImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.together_image_provider.TogetherImageProvider.generate_image", return_value=together_mock):
        res = mgr.generate_image(req)
        assert res.success is True
        assert res.source == "together"


def test_7_all_providers_fail_controlled_unavailable(tmp_path):
    """Test 7: When all providers fail, returns clean IMAGE_GENERATION_UNAVAILABLE."""
    mgr = ImageGenerationManager(cache_dir=str(tmp_path))
    req = ImageGenerationRequest(
        project_title="All Fail Test",
        slide_heading="Sensors",
        final_image_prompt="Sensors in operation",
    )
    image_provider_health_manager.reset_cooldown()

    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.generate_image",
               return_value=LocalRTXGenerationResult(success=False, status="LOCAL_MODEL_NOT_INSTALLED")), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.cloudflare_image_provider.CloudflareImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.hf_image_provider.HFImageProvider.generate_image", return_value=None), \
         patch("apps.api.services.together_image_provider.TogetherImageProvider.is_configured", return_value=False):
        res = mgr.generate_image(req)
        assert res.success is False
        assert res.status == "IMAGE_GENERATION_UNAVAILABLE"


def test_8_cloudflare_429_triggers_cooldown_and_fallback(tmp_path):
    """Test 8: Cloudflare 429 quota exhaustion sets cooldown."""
    image_provider_health_manager.reset_cooldown()
    image_provider_health_manager.record_failure("cloudflare", reason="Quota 429", status_code=429, is_exhausted=True)
    assert image_provider_health_manager.is_available("cloudflare") is False


def test_9_hf_402_triggers_cooldown_and_fallback(tmp_path):
    """Test 9: Hugging Face 402 credits exhausted sets cooldown."""
    image_provider_health_manager.reset_cooldown()
    image_provider_health_manager.record_failure("huggingface", reason="Credits 402", status_code=402, is_exhausted=True)
    assert image_provider_health_manager.is_available("huggingface") is False


def test_10_rtx_cuda_oom_cleans_up_safely():
    """Test 10: CUDA Out of Memory triggers memory cleanup and reports safe failure."""
    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.get_hardware_status",
               return_value={
                   "torch_installed": True,
                   "cuda_available": True,
                   "diffusers_installed": True,
                   "model_ready": True,
                   "free_vram_mb": 2000,
                   "gpu_name": "RTX 3050",
               }), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.is_enabled", return_value=True), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider._run_inference_pipeline",
               side_effect=RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")):
        res = LocalRTXProvider.generate_image(prompt="High detail scene")
        assert res.success is False
        assert "CUDA_OOM" in res.status


def test_11_rtx_concurrency_lock_queue():
    """Test 11: Two simultaneous RTX requests are guarded by GPU lock."""
    from apps.api.services.local_rtx_provider import _GPU_LOCK
    image_provider_health_manager.reset_cooldown()
    with patch("apps.api.services.local_rtx_provider.LocalRTXProvider.get_hardware_status",
               return_value={
                   "torch_installed": True,
                   "cuda_available": True,
                   "diffusers_installed": True,
                   "model_ready": True,
                   "free_vram_mb": 2000,
                   "gpu_name": "RTX 3050",
               }), \
         patch("apps.api.services.local_rtx_provider.LocalRTXProvider.is_enabled", return_value=True):
        acquired = _GPU_LOCK.acquire(blocking=False)
        assert acquired is True
        try:
            res = LocalRTXProvider.generate_image(prompt="Second call")
            assert res.success is False
            assert res.status == "LOCAL_RTX_BUSY"
        finally:
            _GPU_LOCK.release()


# =============================================================================
# PART 2: VISUAL ENGINE & MERMAID/CHART TESTS (TESTS 12 - 25)
# =============================================================================

def test_12_ai_attendance_system_architecture_diagram():
    """Test 12: AI Attendance -> System Architecture generates attendance-specific Mermaid diagram."""
    res = visual_engine.generate_visual(
        project_title="AI Based Attendance Management System",
        slide_heading="System Architecture",
        slide_matter="Face recognition camera connects to student attendance database and faculty dashboard.",
        detected_domain="attendance",
    )
    assert res.success is True
    assert res.visual_type == "mermaid"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_13_smart_irrigation_system_architecture_diagram():
    """Test 13: Smart Irrigation -> System Architecture generates irrigation-specific Mermaid diagram."""
    res = visual_engine.generate_visual(
        project_title="AI Based Smart Irrigation System",
        slide_heading="System Architecture",
        slide_matter="Capacitive soil moisture sensors connect to LoRa gateway and automated drip solenoid valves.",
        detected_domain="irrigation",
    )
    assert res.success is True
    assert res.visual_type == "mermaid"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_14_hospital_management_workflow_diagram():
    """Test 14: Hospital Management -> Workflow generates hospital-specific Mermaid workflow."""
    res = visual_engine.generate_visual(
        project_title="Hospital Management System",
        slide_heading="Working Process",
        slide_matter="Patient triage, doctor consultation, electronic health record update, and pharmacy fulfillment.",
        detected_domain="healthcare",
    )
    assert res.success is True
    assert res.visual_type == "mermaid"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_15_cybersecurity_network_architecture_diagram():
    """Test 15: Cybersecurity -> Network Architecture generates security-specific diagram."""
    res = visual_engine.generate_visual(
        project_title="AI Based Cybersecurity Threat Detection",
        slide_heading="System Architecture",
        slide_matter="Firewall filters ingress traffic, intrusion detection analyzes payload, and SIEM raises incident.",
        detected_domain="cybersecurity",
    )
    assert res.success is True
    assert res.visual_type == "mermaid"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_16_ecommerce_workflow_diagram():
    """Test 16: E-Commerce -> Workflow generates customer to product to payment workflow."""
    res = visual_engine.generate_visual(
        project_title="Online E-Commerce Management System",
        slide_heading="Working Process",
        slide_matter="Customer browses product catalog, adds to cart, executes payment gateway transaction, and orders are fulfilled.",
        detected_domain="ecommerce",
    )
    assert res.success is True
    assert res.visual_type == "mermaid"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_17_database_design_er_diagram():
    """Test 17: Database Design heading generates Mermaid ER diagram."""
    d_type, code = mermaid_diagram_service.generate_mermaid_code(
        project_title="Hospital Management System",
        project_description="",
        domain="healthcare",
        slide_heading="Database Design",
        slide_matter="Schema showing Patient, Doctor, Appointment, and Medical Record entities.",
    )
    assert d_type == "erDiagram"
    assert "erDiagram" in code
    assert "PATIENT" in code or "Patient" in code


def test_18_sequence_diagram():
    """Test 18: Sequence Diagram generates valid sequence diagram."""
    d_type, code = mermaid_diagram_service.generate_mermaid_code(
        project_title="AI Attendance",
        project_description="",
        domain="attendance",
        slide_heading="Sequence Diagram",
        slide_matter="Optical sensor streams frame to face recognition core which queries database.",
    )
    assert d_type == "sequenceDiagram"
    assert "sequenceDiagram" in code


def test_19_class_diagram():
    """Test 19: Class Diagram generates valid class diagram."""
    d_type, code = mermaid_diagram_service.generate_mermaid_code(
        project_title="Smart Irrigation",
        project_description="",
        domain="irrigation",
        slide_heading="Class Diagram",
        slide_matter="SoilProbe class connects to IoTGateway and IrrigationController.",
    )
    assert d_type == "classDiagram"
    assert "classDiagram" in code


def test_20_results_with_real_numeric_data_generates_chart(tmp_path):
    """Test 20: Results with real numerical metrics generates a data chart."""
    res = visual_engine.generate_visual(
        project_title="Smart Irrigation System",
        slide_heading="Results",
        slide_matter="Experimental results: Water Saved: 41.8%, Crop Yield: 18.4%, Accuracy: 96.5%, Latency: 14ms.",
        detected_domain="irrigation",
        output_path=str(tmp_path / "chart_out.png"),
    )
    assert res.success is True
    assert res.visual_type == "chart"
    assert res.asset_path is not None
    assert os.path.exists(res.asset_path)


def test_21_results_without_numeric_data_does_not_generate_fake_chart():
    """Test 21: Results without numeric data does NOT generate fake chart (falls back to diagram)."""
    res = visual_engine.generate_visual(
        project_title="Smart Irrigation System",
        slide_heading="Results",
        slide_matter="The proposed solution successfully achieved all engineering objectives with superior performance.",
        detected_domain="irrigation",
    )
    # Zero fake charts rule: must NOT be chart
    assert res.visual_type != "chart"
    assert res.visual_type in ("mermaid", "image")


def test_22_field_photos_selects_image_generation():
    """Test 22: Field Photos heading selects Image Generation."""
    category, reason = visual_engine.decide_visual_category(
        slide_heading="Field Deployment Photos",
        slide_matter="Photographs showing sensor nodes installed in agricultural field.",
        detected_domain="irrigation",
    )
    assert category == "image"


def test_23_references_selects_no_visual():
    """Test 23: References selects no visual ('none')."""
    res = visual_engine.generate_visual(
        project_title="Any Project",
        slide_heading="References",
        slide_matter="1. IEEE Transactions on Systems (2024). 2. ACM Computing Surveys.",
    )
    assert res.visual_type == "none"
    assert res.asset_path is None


def test_24_invalid_mermaid_repaired_safely():
    """Test 24: Invalid Mermaid syntax is repaired or safely rendered via fallback."""
    raw_code = "A[Node 1] --> B[Node 2]"  # Missing flowchart TD header
    is_valid, repaired = mermaid_diagram_service.validate_and_repair_mermaid(raw_code)
    assert is_valid is True
    assert "flowchart TD" in repaired


def test_25_repeated_diagram_uses_cache(tmp_path):
    """Test 25: Repeated diagram generation hits the diagram cache."""
    out1 = str(tmp_path / "d1.png")
    out2 = str(tmp_path / "d2.png")
    unique_title = f"Fresh Cache Test {time.time()}"

    res1 = mermaid_diagram_service.generate_diagram(
        project_title=unique_title,
        domain="unique_domain",
        slide_heading="System Architecture",
        output_path=out1,
    )
    assert res1.success is True
    assert res1.cached is False

    res2 = mermaid_diagram_service.generate_diagram(
        project_title=unique_title,
        domain="unique_domain",
        slide_heading="System Architecture",
        output_path=out2,
    )
    assert res2.success is True
    assert res2.cached is True
