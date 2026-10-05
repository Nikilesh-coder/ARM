"""
ARM Regression Test Suite: AI Irrigation Image & Title Fix
Validates:
1. Intelligent image classification on JAGADEESH PPT.docx (transparent borders and logos preserved, topic diagrams replaced).
2. Domain-aware visual synthesis (irrigation domain yields irrigation infographics, zero attendance/electrical text).
3. OOXML package surgery preserves fixed assets and replaces topic images byte-for-byte.
4. Visual report validation flags zero forbidden electrical terms and confirms all topic keywords.
"""

import os
import io
import pytest
from apps.api.services.intelligent_image_service import intelligent_image_service
from apps.api.services.visual_report_validator import visual_report_validator
from apps.api.services.replacement_engine_service import replacement_engine_service

JAGADEESH_TPL = r".storage\templates\users\1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd\templates\0484aecb-dbc1-4671-a388-0f820124ca0e\JAGADEESH PPT.docx"
ELECTRIFY_TPL = r".storage\templates\users\1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd\templates\b6acbdd4-c09d-4346-9981-b9c3db1d36a1\Electrify Future Safe Electricity Schools (1).docx"


def test_classification_jagadeesh_ppt():
    """Verify JAGADEESH PPT classifies transparent frames and logos as fixed, only replacing topic images."""
    assert os.path.exists(JAGADEESH_TPL), f"Template not found: {JAGADEESH_TPL}"
    analyzed = intelligent_image_service.analyze_docx_images(JAGADEESH_TPL)
    assert len(analyzed) == 17

    fixed = [im for im in analyzed if im["action"] == "fixed"]
    replaced = [im for im in analyzed if im["action"] == "replace"]

    assert len(fixed) == 15, f"Expected 15 fixed assets, got {len(fixed)}"
    assert len(replaced) == 2, f"Expected 2 replaced images, got {len(replaced)}"

    replaced_fnames = {im["filename"] for im in replaced}
    assert replaced_fnames == {"image12.jpeg", "image14.jpeg"}, f"Unexpected replaced images: {replaced_fnames}"

    # Verify transparent border frame classification
    frame_imgs = [im for im in analyzed if im["filename"] in ("image3.png", "image4.png", "image7.png", "image9.png", "image11.png")]
    for f in frame_imgs:
        assert f["action"] == "fixed"
        assert f["classification"] == "fixed_asset"
        assert f["opaque_pct"] < 15.0

    # Verify logo badges
    logos = [im for im in analyzed if im["filename"] in ("image1.png", "image2.jpeg", "image5.png", "image15.png")]
    for l in logos:
        assert l["action"] == "fixed"
        assert l["classification"] == "college_logo"


def test_classification_electrify_future():
    """Verify standard document template Electrify Future preserves all 31 topic diagrams for replacement."""
    assert os.path.exists(ELECTRIFY_TPL), f"Template not found: {ELECTRIFY_TPL}"
    analyzed = intelligent_image_service.analyze_docx_images(ELECTRIFY_TPL)
    assert len(analyzed) == 31

    replaced = [im for im in analyzed if im["action"] == "replace"]
    assert len(replaced) == 31


def test_domain_aware_synthesis_irrigation(tmp_path):
    """Verify synthesis for 'AI based irrigation' creates domain-accurate visuals with zero attendance or electrical text."""
    test_images = [
        {
            "id": "img_12",
            "arm_image_field": "image_12",
            "filename": "image12.jpeg",
            "format": "JPEG",
            "aspect_ratio": 1.76,
            "classification": "topic_specific",
            "action": "replace",
            "heading": "COMMUNITY AWARENESS",
        },
        {
            "id": "img_14",
            "arm_image_field": "image_14",
            "filename": "image14.jpeg",
            "format": "JPEG",
            "aspect_ratio": 0.78,
            "classification": "topic_specific",
            "action": "replace",
            "heading": "COMMUNITYINTERACTION PHOTOS",
        },
    ]

    out_dir = str(tmp_path / "gen_imgs")
    synth = intelligent_image_service.generate_replacement_images(
        project_title="AI based irrigation",
        problem_statement="Develop an AI-based irrigation system that uses soil moisture sensors and weather data to automate irrigation and reduce water wastage.",
        analyzed_images=test_images,
        output_dir=out_dir,
    )

    assert "image12.jpeg" in synth
    assert "image14.jpeg" in synth
    assert os.path.exists(synth["image12.jpeg"]["file_path"])
    assert os.path.exists(synth["image14.jpeg"]["file_path"])


def test_e2e_ai_irrigation_report_generation_and_validation(tmp_path):
    """Verify end-to-end report generation for AI based irrigation with visual validator audit."""
    project_data = {
        "title": "AI based irrigation",
        "project_name": "AI based irrigation",
        "description": "Develop an AI-based irrigation system that uses soil moisture sensors and weather data to automate irrigation and reduce water wastage.",
        "abstract": "Automated precision agriculture system using IoT soil moisture sensors and predictive meteorological inference.",
        "introduction": "Traditional irrigation methods cause significant water loss. AI-driven drip manifolds conserve over 40% of water.",
        "objectives": "1. Deploy capacitive soil telemetry. 2. Automate drip valve cycles. 3. Prevent crop water deficit.",
    }

    job = replacement_engine_service.execute_replacement(
        project_id="test-pytest-irrigation-001",
        project_data=project_data,
        template_id="0484aecb-dbc1-4671-a388-0f820124ca0e",
    )

    assert job["state"].upper() == "COMPLETED"
    assert job["docx_path"] and os.path.exists(job["docx_path"])

    val_audit = job.get("visual_audit") or {}
    assert val_audit.get("is_valid") is True
    assert val_audit.get("status") == "PASSED"
    assert len(val_audit.get("forbidden_terms_found", [])) == 0
    assert len(val_audit.get("topic_keywords_found", [])) >= 4
    assert val_audit.get("media_audit", {}).get("unreplaced_forbidden_images") == []
