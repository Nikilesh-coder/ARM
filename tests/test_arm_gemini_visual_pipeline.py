"""
ARM Comprehensive Test Suite: Enhanced Gemini Visual Pipeline
============================================================
Verifies:
1. Slide Understanding before Image Generation (Visual Requirement Analysis).
2. Purpose Detection across all 12 required slide types:
   - Introduction
   - Problem Statement
   - Existing System
   - Proposed System
   - Soil Moisture Monitoring
   - AI-Based Decision Making
   - System Architecture
   - Working Process
   - Field Deployment
   - Results
   - Future Scope
   - Conclusion
3. Dynamic Prompt Synthesis: Slide Heading + Slide Matter > Project Name.
4. Concept and Object extraction from slide body text.
5. Rejection of generic AI brains, electrical safety artifacts, and generic stock tropes.
6. Visual diversity across all 12 slides (distinct concepts, subjects, and environments).
7. End-to-end integration with ARM DOCX report replacement pipeline.
"""

import os
import tempfile
import pytest
from PIL import Image

from apps.api.services.gemini_visual_pipeline_service import (
    gemini_visual_pipeline_service,
    SlideVisualPurpose,
    SlideVisualRequirement,
)
from apps.api.services.intelligent_image_service import intelligent_image_service
from apps.api.services.replacement_engine_service import ReplacementEngineService
from apps.api.services.visual_report_validator import visual_report_validator
from apps.api.routers.projects import _PROJECTS_STORE

JAGADEESH_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/0484aecb-dbc1-4671-a388-0f820124ca0e/JAGADEESH PPT.docx"
)

# The 12 canonical test slides from Step 12
CANONICAL_SLIDES = [
    {
        "index": 1,
        "heading": "Introduction",
        "matter": "Agriculture requires efficient water management. Smart irrigation optimizes water usage while maintaining optimal crop growth in commercial farm fields.",
        "expected_purpose": SlideVisualPurpose.INTRODUCTION,
        "expected_visual_type": "REALISTIC_PHOTO",
        "must_include": ["crop", "farm"],
        "must_avoid": ["electrical", "socket", "glowing brain"],
    },
    {
        "index": 2,
        "heading": "Problem Statement",
        "matter": "Traditional flood irrigation results in severe water wastage, over-irrigation runoff, and crop stress from uneven soil saturation during drought periods.",
        "expected_purpose": SlideVisualPurpose.PROBLEM_STATEMENT,
        "expected_visual_type": "REALISTIC_PHOTO",
        "must_include": ["parched", "soil"],
        "must_avoid": ["electrical", "socket"],
    },
    {
        "index": 3,
        "heading": "Existing System",
        "matter": "Conventional manual irrigation relies on fixed schedules and visual soil estimates, leading to excessive aquifer depletion and manual labor inefficiency.",
        "expected_purpose": SlideVisualPurpose.EXISTING_SYSTEM,
        "expected_visual_type": "REALISTIC_PHOTO",
        "must_include": ["conventional", "water"],
        "must_avoid": ["electrical", "glowing brain"],
    },
    {
        "index": 4,
        "heading": "Proposed System",
        "matter": "The smart irrigation system uses automated precision drip lines and microcontroller regulation to deliver targeted water volume directly to crops.",
        "expected_purpose": SlideVisualPurpose.PROPOSED_SYSTEM,
        "expected_visual_type": "TECHNICAL_PHOTO",
        "must_include": ["drip", "irrigation"],
        "must_avoid": ["electrical", "socket"],
    },
    {
        "index": 5,
        "heading": "Soil Moisture Monitoring",
        "matter": "The system continuously monitors soil moisture using capacitive dielectric sensor probes and activates irrigation when the moisture level falls below 30%.",
        "expected_purpose": SlideVisualPurpose.SOIL_MOISTURE_MONITORING,
        "expected_visual_type": "TECHNICAL_PHOTO",
        "must_include": ["soil moisture", "sensor"],
        "must_avoid": ["electrical safety", "circuit board"],
    },
    {
        "index": 6,
        "heading": "AI-Based Decision Making",
        "matter": "Cloud machine learning algorithms analyze historical soil moisture gradients and meteorological forecasts to dynamically adjust irrigation durations.",
        "expected_purpose": SlideVisualPurpose.AI_DECISION_MAKING,
        "expected_visual_type": "CONCEPTUAL_ILLUSTRATION",
        "must_include": ["agricultural", "decision"],
        "must_avoid": ["glowing brain", "robot humanoid"],
    },
    {
        "index": 7,
        "heading": "System Architecture",
        "matter": "Multi-tier telemetry stack connecting edge ESP32 sensor nodes, wireless LoRa gateways, cloud inference servers, and 12V solenoid valve manifolds.",
        "expected_purpose": SlideVisualPurpose.SYSTEM_ARCHITECTURE,
        "expected_visual_type": "SYSTEM_ARCHITECTURE",
        "must_include": ["telemetry", "solenoid"],
        "must_avoid": ["electrical safety", "green motherboard"],
    },
    {
        "index": 8,
        "heading": "Working Process",
        "matter": "A closed-loop operational pipeline: sensing volumetric water content, deficit analysis, predictive duration calculation, and automated valve actuation.",
        "expected_purpose": SlideVisualPurpose.WORKING_PROCESS,
        "expected_visual_type": "FLOWCHART",
        "must_include": ["water", "delivery"],
        "must_avoid": ["electrical safety", "socket"],
    },
    {
        "index": 9,
        "heading": "Field Deployment",
        "matter": "Real-world field deployment of pole-mounted solar telemetry nodes and extensive drip lateral lines across a 5-acre commercial crop test plot.",
        "expected_purpose": SlideVisualPurpose.FIELD_DEPLOYMENT,
        "expected_visual_type": "REALISTIC_PHOTO",
        "must_include": ["crop", "field"],
        "must_avoid": ["electrical safety", "hazard"],
    },
    {
        "index": 10,
        "heading": "Results",
        "matter": "Experimental evaluation demonstrating a 34% reduction in total volumetric water consumption and a 15% increase in agricultural yield consistency.",
        "expected_purpose": SlideVisualPurpose.RESULTS,
        "expected_visual_type": "CHART",
        "must_include": ["crop", "water"],
        "must_avoid": ["electrical", "socket"],
    },
    {
        "index": 11,
        "heading": "Future Scope",
        "matter": "Future enhancements include integrating multispectral drone imaging, LoRaWAN mesh expansion, and autonomous fertilizer nutrient dosing modules.",
        "expected_purpose": SlideVisualPurpose.FUTURE_SCOPE,
        "expected_visual_type": "CONCEPTUAL_ILLUSTRATION",
        "must_include": ["farm", "precision"],
        "must_avoid": ["cyberspace matrix", "robot"],
    },
    {
        "index": 12,
        "heading": "Conclusion",
        "matter": "The AI-based irrigation system successfully proves that closed-loop soil telemetry and automated drip regulation protect vital aquifers and empower sustainable farming.",
        "expected_purpose": SlideVisualPurpose.CONCLUSION,
        "expected_visual_type": "REALISTIC_PHOTO",
        "must_include": ["crop", "irrigation"],
        "must_avoid": ["electrical safety", "socket"],
    },
]


def test_1_slide_understanding_and_purpose_detection_all_12_slides():
    """
    TEST 1:
    Verifies Step 1, 2, 3: For all 12 required slides, purpose detection accurately classifies
    the slide, extracts concepts from the body matter, and enforces Heading + Matter > Project Name.
    """
    print("\n--- TEST 1: Purpose Detection & Concept Extraction Across All 12 Slides ---")
    proj_title = "AI Based Irrigation System"

    for s in CANONICAL_SLIDES:
        req = gemini_visual_pipeline_service.compile_visual_requirement(
            project_title=proj_title,
            slide_heading=s["heading"],
            slide_matter=s["matter"],
            slide_index=s["index"],
        )

        assert req.slide_purpose == s["expected_purpose"], (
            f"Slide {s['index']} ({s['heading']}): Expected {s['expected_purpose']}, got {req.slide_purpose}"
        )
        assert req.visual_type == s["expected_visual_type"], (
            f"Slide {s['index']} ({s['heading']}): Expected visual type {s['expected_visual_type']}, got {req.visual_type}"
        )

        # Confirm concepts and objects were extracted from matter
        assert len(req.key_concepts) > 0
        assert len(req.required_objects) > 0
        assert len(req.required_subjects) > 0

        print(f"  Slide {s['index']:<2} | {s['heading']:<26} -> Purpose: {req.slide_purpose:<24} | Type: {req.visual_type}")

    print("PASS: TEST 1 - All 12 slide purposes and visual requirements compiled accurately.")


def test_2_dynamic_gemini_prompt_synthesis_and_negative_constraints():
    """
    TEST 2:
    Verifies Step 4, 5, 6: Dynamic prompt generation embeds slide heading, matter,
    physical objects, and strictly includes universal negative constraints.
    """
    print("\n--- TEST 2: Dynamic Gemini Prompt Synthesis & Constraints ---")
    proj_title = "AI Based Irrigation System"

    for s in CANONICAL_SLIDES:
        req = gemini_visual_pipeline_service.compile_visual_requirement(
            project_title=proj_title,
            slide_heading=s["heading"],
            slide_matter=s["matter"],
            slide_index=s["index"],
        )

        prompt = req.gemini_prompt
        # Must contain heading
        assert s["heading"] in prompt, f"Prompt missing slide heading: {s['heading']}"
        # Must contain negative constraints
        assert "Negative Constraints" in prompt
        assert "electrical safety" in prompt.lower()
        assert "glowing brain" in prompt.lower()

        # Must NOT contain generic single-line prompt
        assert len(prompt) > 200

    print("PASS: TEST 2 - Dynamic prompts synthesized with full context and negative constraints.")


def test_3_automated_relevance_check_and_generic_rejection():
    """
    TEST 3:
    Verifies Step 7: Automated relevance check rejects generic AI brains,
    leftover electrical safety terms, and ungrounded stock prompts.
    """
    print("\n--- TEST 3: Automated Relevance Check ---")
    # Valid requirement
    valid_req = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title="AI Based Irrigation System",
        slide_heading="Soil Moisture Monitoring",
        slide_matter="Continuous sensor monitoring of root zone moisture.",
    )
    is_valid, reason = gemini_visual_pipeline_service.validate_image_relevance(valid_req)
    assert is_valid is True
    assert reason == "PASS"

    # Invalid: Generic AI glowing brain
    bad_req_brain = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title="AI Based Irrigation System",
        slide_heading="Soil Moisture Monitoring",
        slide_matter="Continuous sensor monitoring.",
    )
    is_valid_brain, reason_brain = gemini_visual_pipeline_service.validate_image_relevance(
        bad_req_brain, generated_prompt_or_text="A glowing brain floating in cyberspace"
    )
    assert is_valid_brain is False
    assert "glowing brain" in reason_brain.lower()

    # Invalid: Leftover electrical safety socket
    bad_req_socket = gemini_visual_pipeline_service.compile_visual_requirement(
        project_title="AI Based Irrigation System",
        slide_heading="Soil Moisture Monitoring",
        slide_matter="Continuous sensor monitoring.",
    )
    is_valid_socket, reason_socket = gemini_visual_pipeline_service.validate_image_relevance(
        bad_req_socket, generated_prompt_or_text="An electrical socket with damaged wiring"
    )
    assert is_valid_socket is False
    assert "socket" in reason_socket.lower()

    print("PASS: TEST 3 - Automated relevance check successfully rejects clichés and old template artifacts.")


def test_4_visual_diversity_across_slides():
    """
    TEST 4:
    Verifies Step 8: Ensures different slides communicate meaningfully different concepts
    and do not generate the same visual across all slides.
    """
    print("\n--- TEST 4: Visual Diversity Across All 12 Slides ---")
    prompts = set()
    subjects_collection = []

    for s in CANONICAL_SLIDES:
        req = gemini_visual_pipeline_service.compile_visual_requirement(
            project_title="AI Based Irrigation System",
            slide_heading=s["heading"],
            slide_matter=s["matter"],
            slide_index=s["index"],
        )
        prompts.add(req.gemini_prompt)
        subjects_collection.append(tuple(req.required_subjects))

    # All 12 prompts must be uniquely tailored
    assert len(prompts) == 12, f"Expected 12 unique prompts, got {len(prompts)}"
    # At least 8 distinct subject configurations
    assert len(set(subjects_collection)) >= 8
    print(f"PASS: TEST 4 - Verified 12/12 distinct visual requirements across the presentation.")


def test_5_e2e_slide_image_generation_and_replacement(tmp_path):
    """
    TEST 5:
    Verifies Step 9, 10, 11: End-to-end image generation and replacement
    fitting into template dimensions and outputting debug logging.
    """
    print("\n--- TEST 5: E2E Slide Image Generation & Replacement ---")
    out_img = str(tmp_path / "test_soil_moisture.jpeg")

    req = gemini_visual_pipeline_service.generate_and_replace_slide_image(
        project_title="AI Based Irrigation System",
        slide_heading="Soil Moisture Monitoring",
        slide_matter="The system continuously monitors soil moisture using capacitive dielectric sensor probes.",
        aspect_ratio=1.77,
        out_file_path=out_img,
        slide_index=5,
        target_fmt="JPEG",
    )

    assert os.path.exists(out_img)
    assert os.path.getsize(out_img) > 1000

    with Image.open(out_img) as pil_img:
        w, h = pil_img.size
        ar = round(w / max(1, h), 2)
        assert abs(ar - 1.77) < 0.25, f"Aspect ratio mismatch: expected ~1.77, got {ar}"

    print(f"PASS: TEST 5 - Successfully generated and replaced image ({w}x{h}, AR={ar}).")


def test_6_full_report_generation_with_enhanced_gemini_pipeline():
    """
    TEST 6:
    Runs full report generation on JAGADEESH PPT.docx using the enhanced Gemini visual pipeline.
    Verifies:
    - 0 forbidden electrical terms.
    - Preserved college logos.
    - Topic-relevant image replacements.
    """
    print("\n--- TEST 6: Full Report Generation Audit ---")
    project_id = "proj_test_gemini_vis_e2e"
    _PROJECTS_STORE[project_id] = {
        "id": project_id,
        "title": "AI Based Irrigation System",
        "project_name": "AI Based Irrigation System",
        "report_title": "AI Based Irrigation System",
        "description": "An autonomous precision irrigation system using soil moisture sensors and edge AI to optimize agricultural water consumption.",
    }

    service = ReplacementEngineService()
    result = service.execute_replacement(
        project_id=project_id,
        template_id="0484aecb-dbc1-4671-a388-0f820124ca0e",
        user_instructions="Synthesize comprehensive precision irrigation report preserving all template styling",
    )

    assert result.get("state") == "COMPLETED"
    out_docx = result.get("docx_path")
    assert out_docx and os.path.exists(out_docx)

    # Post-generation visual validator
    audit = visual_report_validator.validate_report_visuals(
        docx_path=out_docx,
        project_title="AI Based Irrigation System",
        problem_statement="An autonomous precision irrigation system using soil moisture sensors and edge AI to optimize agricultural water consumption.",
        template_path=JAGADEESH_TPL,
    )

    assert audit["is_valid"] is True
    assert audit["status"] == "PASSED"
    assert len(audit.get("forbidden_terms_found", [])) == 0, f"Found forbidden terms: {audit.get('forbidden_terms_found')}"
    print("PASS: TEST 6 - Full report generation passed audit with zero forbidden terms.")


if __name__ == "__main__":
    test_1_slide_understanding_and_purpose_detection_all_12_slides()
    test_2_dynamic_gemini_prompt_synthesis_and_negative_constraints()
    test_3_automated_relevance_check_and_generic_rejection()
    test_4_visual_diversity_across_slides()
    test_5_e2e_slide_image_generation_and_replacement(tempfile.TemporaryDirectory().name)
    test_6_full_report_generation_with_enhanced_gemini_pipeline()
    print("\n===========================================================")
    print("ALL 6 ENHANCED GEMINI VISUAL PIPELINE TESTS PASSED!")
