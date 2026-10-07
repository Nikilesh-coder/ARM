"""
ARM Test Suite: Image Context Diversity, Cache Isolation & Deduplication
========================================================================
Verifies:
1. Exact request repeated -> 1st MISS, 2nd HIT.
2. Same project + different headings -> distinct cache keys (image_cache:v2:<context_hash>).
3. Different slide contexts -> semantically different generated prompts.
4. Multiple images in one report -> distinct image hashes, report history verification.
5. Similarity check -> flag identical/colliding images for unrelated sections.
6. Cache isolation -> unrelated slide does not retrieve another slide's cache.
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
from apps.api.services.gemini_visual_pipeline_service import (
    gemini_visual_pipeline_service,
    SlideVisualPurpose,
)


def _create_dummy_image_bytes(color: tuple = (100, 150, 200), width: int = 64, height: int = 64) -> bytes:
    img = PILImage.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_1_exact_request_repeated_miss_then_hit(tmp_path):
    """
    TEST 1: Exact request repeated -> 1st MISS, 2nd HIT.
    Cache must stay enabled and store versioned cache entries.
    """
    cache_dir = str(tmp_path / "img_cache_1")
    manager = ImageGenerationManager(cache_dir=cache_dir)

    req = ImageGenerationRequest(
        project_title="AI Based Smart Irrigation",
        project_description="Smart autonomous crop irrigation",
        detected_domain="irrigation",
        slide_number=1,
        slide_heading="Introduction",
        slide_matter="Modern agriculture requires automated water management to protect crops.",
        visual_purpose="INTRODUCTION",
        final_image_prompt="A sunlit commercial crop field with neat irrigation lines.",
        width=512,
        height=512,
        report_id="test_run_cache_hit",
        style="photorealistic",
    )

    # 1. Before saving: cache check must be a MISS (returns None)
    cached_before = manager._get_from_cache(req)
    assert cached_before is None, "Expected cache MISS on first call."

    # Mock provider returning fresh image bytes
    dummy_bytes = _create_dummy_image_bytes((30, 180, 50))
    dummy_sha = hashlib.sha256(dummy_bytes).hexdigest()

    with patch("apps.api.services.xkiro_image_provider.XKiroImageProvider.is_configured", return_value=True), \
         patch("apps.api.services.xkiro_image_provider.XKiroImageProvider.generate_image") as mock_xkiro:
        mock_res = MagicMock()
        mock_res.image_bytes = dummy_bytes
        mock_res.sha256 = dummy_sha
        mock_res.dimensions = (512, 512)
        mock_res.model_name = "sensenova/sensenova-u1.5-lite"
        mock_res.provider_name = "xkiro"
        mock_xkiro.return_value = mock_res

        # 1st call: Generates via Supernova (xKiro)
        res1 = manager.generate_image(req)
        assert res1.success is True
        assert res1.cached is False
        assert res1.source == "supernova"

    # 2nd call: Must be a CACHE HIT
    res2 = manager.generate_image(req)
    assert res2.success is True
    assert res2.cached is True
    assert res2.source == "cache"
    assert res2.status == "SUCCESS_CACHE_HIT"
    assert res2.sha256 == dummy_sha


def test_2_same_project_different_headings_distinct_versioned_cache_keys(tmp_path):
    """
    TEST 2: Same project + different headings -> distinct cache keys with image_cache:v2: namespace.
    Ensures cache keys are slide-context aware and not only project title based.
    """
    cache_dir = str(tmp_path / "img_cache_2")
    manager = ImageGenerationManager(cache_dir=cache_dir)

    req_slide_a = ImageGenerationRequest(
        project_title="AI Based Smart Irrigation",
        slide_number=2,
        slide_heading="Soil Moisture Challenges",
        slide_matter="High soil salinity causes rapid sensor probe corrosion.",
        visual_purpose="PROBLEM_STATEMENT",
        final_image_prompt="Field instrumentation in salty soil experiencing sensor corrosion.",
        detected_domain="irrigation",
        width=1024,
        height=1024,
    )

    req_slide_b = ImageGenerationRequest(
        project_title="AI Based Smart Irrigation",
        slide_number=3,
        slide_heading="Solar Powered Pumping",
        slide_matter="Photovoltaic panels driving centrifugal pumps for off-grid fields.",
        visual_purpose="GENERAL_TECHNICAL",
        final_image_prompt="Photovoltaic solar array powering agricultural water pump.",
        detected_domain="irrigation",
        width=1024,
        height=1024,
    )

    key_a = manager._compute_cache_key(req_slide_a)
    key_b = manager._compute_cache_key(req_slide_b)

    assert key_a.startswith("image_cache:v2:"), f"Expected v2 cache namespace, got: {key_a}"
    assert key_b.startswith("image_cache:v2:"), f"Expected v2 cache namespace, got: {key_b}"
    assert key_a != key_b, "Cache keys for different slides in the same project must not collide!"


def test_3_different_slide_contexts_semantically_diverse_prompts():
    """
    TEST 3: Different slide contexts -> semantically different generated prompts.
    Slide Heading + Matter must dictate prompt subjects, objects, and environment.
    """
    project = "AI Based Smart Irrigation System"

    req_soil = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title=project,
        slide_heading="Soil Moisture Challenges",
        slide_matter="Corrosion on capacitive sensor probes in high salinity soil strata.",
        slide_index=2,
    )

    req_solar = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title=project,
        slide_heading="Solar Powered Irrigation",
        slide_matter="Solar photovoltaic panels providing clean energy to centrifugal water pumps in off-grid plots.",
        slide_index=6,
    )

    req_community = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title=project,
        slide_heading="Community Water Governance",
        slide_matter="Farming community workshops and shared water allocation schedules across smallholder farms.",
        slide_index=8,
    )

    # 1. Prompts must be distinct
    assert req_soil.gemini_prompt != req_solar.gemini_prompt
    assert req_solar.gemini_prompt != req_community.gemini_prompt
    assert req_soil.gemini_prompt != req_community.gemini_prompt

    # 2. Specific domain keywords must be contextually isolated
    assert "solar" in req_solar.gemini_prompt.lower()
    assert "community" in req_community.gemini_prompt.lower() or "farmer" in req_community.gemini_prompt.lower()
    assert "soil" in req_soil.gemini_prompt.lower() or "sensor" in req_soil.gemini_prompt.lower()

    # 3. Solar objects should NOT be in soil moisture prompt
    assert "solar-powered" not in req_soil.gemini_prompt.lower()


def test_4_multiple_images_in_one_report_distinct_hashes_and_history(tmp_path):
    """
    TEST 4: Multiple images in one report -> distinct image hashes and report history verification.
    """
    cache_dir = str(tmp_path / "img_cache_4")
    manager = ImageGenerationManager(cache_dir=cache_dir)
    report_id = "report_run_diversity_audit"
    manager.clear_report_history(report_id)

    # Image 1 (Soil)
    bytes_1 = _create_dummy_image_bytes((40, 120, 20), width=64, height=64)
    sha_1 = hashlib.sha256(bytes_1).hexdigest()
    manager.record_report_image(
        report_id=report_id,
        slide_number=1,
        slide_heading="Soil Moisture Monitoring",
        sha256=sha_1,
        image_bytes=bytes_1,
        source="supernova",
    )

    # Image 2 (Solar)
    bytes_2 = _create_dummy_image_bytes((240, 200, 30), width=64, height=64)
    sha_2 = hashlib.sha256(bytes_2).hexdigest()
    manager.record_report_image(
        report_id=report_id,
        slide_number=2,
        slide_heading="Solar Pumping Array",
        sha256=sha_2,
        image_bytes=bytes_2,
        source="supernova",
    )

    # Image 3 (IoT Gateway)
    bytes_3 = _create_dummy_image_bytes((10, 50, 180), width=64, height=64)
    sha_3 = hashlib.sha256(bytes_3).hexdigest()
    manager.record_report_image(
        report_id=report_id,
        slide_number=3,
        slide_heading="IoT Gateway Network",
        sha256=sha_3,
        image_bytes=bytes_3,
        source="cloudflare",
    )

    history = manager._report_history.get(report_id, [])
    assert len(history) == 3, f"Expected 3 recorded images, found {len(history)}"

    hashes = [r.sha256 for r in history]
    assert len(set(hashes)) == 3, "All images in report history must have unique hashes!"


def test_5_similarity_check_flags_colliding_images(tmp_path):
    """
    TEST 5: Similarity check -> flags identical or near-identical duplicate images for different slides in the same report.
    """
    cache_dir = str(tmp_path / "img_cache_5")
    manager = ImageGenerationManager(cache_dir=cache_dir)
    report_id = "report_collision_check"
    manager.clear_report_history(report_id)

    img_bytes = _create_dummy_image_bytes((120, 120, 120), width=64, height=64)
    sha = hashlib.sha256(img_bytes).hexdigest()

    # Register Slide 1 image
    manager.record_report_image(
        report_id=report_id,
        slide_number=1,
        slide_heading="Introduction",
        sha256=sha,
        image_bytes=img_bytes,
        source="supernova",
    )

    # Check Slide 2 attempting to reuse the exact same image bytes
    is_dup, reason = manager._is_image_duplicate_in_report(
        report_id=report_id,
        slide_number=2,
        sha256=sha,
        image_bytes=img_bytes,
    )

    assert is_dup is True, "Exact duplicate image bytes for a different slide must be flagged!"
    assert "match with Slide 1" in reason or "Exact SHA256 match" in reason

    # Same slide re-evaluating itself should NOT be flagged as duplicate
    is_dup_same_slide, _ = manager._is_image_duplicate_in_report(
        report_id=report_id,
        slide_number=1,
        sha256=sha,
        image_bytes=img_bytes,
    )
    assert is_dup_same_slide is False, "Same slide retry must not collide with itself."


def test_6_cache_isolation_unrelated_slide_does_not_retrieve_prior_cache(tmp_path):
    """
    TEST 6: Cache isolation -> unrelated slide does not retrieve another slide's cache.
    """
    cache_dir = str(tmp_path / "img_cache_6")
    manager = ImageGenerationManager(cache_dir=cache_dir)

    req_slide_1 = ImageGenerationRequest(
        project_title="AI Based Smart Irrigation",
        slide_number=1,
        slide_heading="Introduction",
        slide_matter="Overview of agricultural water challenges.",
        visual_purpose="INTRODUCTION",
        final_image_prompt="Overview farm scene.",
        detected_domain="irrigation",
    )

    # Save Slide 1 to cache
    bytes_1 = _create_dummy_image_bytes((10, 80, 20))
    sha_1 = hashlib.sha256(bytes_1).hexdigest()
    manager._save_to_cache(req_slide_1, bytes_1, "supernova", sha_1)

    # Verify Slide 1 hits cache
    cached_1 = manager._get_from_cache(req_slide_1)
    assert cached_1 is not None
    assert cached_1.sha256 == sha_1

    # Unrelated Slide 2 must MISS cache
    req_slide_2 = ImageGenerationRequest(
        project_title="AI Based Smart Irrigation",
        slide_number=2,
        slide_heading="Solar Pumping Units",
        slide_matter="High power solar panels for field pumping.",
        visual_purpose="GENERAL_TECHNICAL",
        final_image_prompt="Solar panels in agricultural plot.",
        detected_domain="irrigation",
    )

    cached_2 = manager._get_from_cache(req_slide_2)
    assert cached_2 is None, "Slide 2 must NOT hit Slide 1's cache entry!"
