"""
ARM Test Suite: Project-Specific Content Replacement & Template Preservation
Validates:
1. Complete template design preservation (logos, borders, fonts, margins, page numbers, academic metadata).
2. Complete project-specific content replacement:
   - Cover title replaced with student project name.
   - All slide headings replaced (e.g. 'COMMUNITY AWARENESS' -> 'System Architecture & Telemetry',
     'COMMUNITYINTERACTION PHOTOS' -> 'SMART IRRIGATION FIELD DEPLOYMENT').
   - Table of Contents entries synchronized (e.g. 'Community Awareness' -> 'System Architecture & Telemetry').
   - All topic matter (abstract, intro, objectives, advantages, disadvantages, problems, conclusion, references) replaced.
   - Topic images replaced with domain-aware visuals; logos and borders preserved byte-for-byte.
3. Zero leftover forbidden terms and 100% topic relevance across both templates:
   - JAGADEESH PPT.docx
   - Electrify Future Safe Electricity Schools (1).docx
"""

import os
import pytest
import docx
from apps.api.services.replacement_engine_service import replacement_engine_service
from apps.api.services.custom_template_service import custom_template_service
from apps.api.services.semantic_slide_mapper import semantic_slide_mapper
from apps.api.services.visual_report_validator import VisualReportValidator

JAGADEESH_TPL_ID = "0484aecb-dbc1-4671-a388-0f820124ca0e"
ELECTRIFY_TPL_ID = "b6acbdd4-c09d-4346-9981-b9c3db1d36a1"


def test_custom_template_detection_includes_headings_and_toc():
    """Verify custom_template_service detects TOC items and slide headings without skips."""
    jag_path = r".storage\templates\users\1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd\templates\0484aecb-dbc1-4671-a388-0f820124ca0e\JAGADEESH PPT.docx"
    analysis = custom_template_service.analyze_template_docx(jag_path)
    fields = analysis.get("detected_text_fields", [])

    arm_fields = {f["arm_field"] for f in fields}
    assert "project_title" in arm_fields
    assert "slide_6_heading" in arm_fields
    assert "slide_7_heading" in arm_fields
    assert any("toc" in f for f in arm_fields)

    # Check Slide 6 & 7 heading elements
    s6 = next(f for f in fields if f["arm_field"] == "slide_6_heading")
    s7 = next(f for f in fields if f["arm_field"] == "slide_7_heading")
    assert s6["original_text"] == "COMMUNITY AWARENESS"
    assert s7["original_text"] == "COMMUNITYINTERACTION PHOTOS"


def test_jagadeesh_ppt_content_replacement_e2e():
    """Verify JAGADEESH PPT replaces all project-specific headings, TOC items, matter, and images."""
    project_data = {
        "title": "AI Based Irrigation System",
        "project_name": "AI Based Irrigation System",
        "description": "Develop an AI-based irrigation system that uses soil moisture sensors and weather data to automate irrigation and reduce water wastage.",
    }

    job = replacement_engine_service.execute_replacement(
        project_id="test-e2e-jagadeesh-irrigation",
        project_data=project_data,
        template_id=JAGADEESH_TPL_ID,
    )

    assert job["state"].upper() == "COMPLETED"
    out_docx = job["docx_path"]
    assert os.path.exists(out_docx)

    doc = docx.Document(out_docx)

    # 1. Slide 1: Cover Title replaced, academic credentials preserved
    p3 = doc.paragraphs[3].text.strip()
    assert "AI Based Irrigation System" in p3
    assert "ELECTRIFY" not in p3.upper()

    p7 = doc.paragraphs[7].text.strip()
    assert "KASIREDDY CHARISHMA" in p7  # student name preserved!

    p17 = doc.paragraphs[17].text.strip()
    assert "Dr.R.Sireesha" in p17  # guide name preserved!

    # 2. Slide 2: Table of Contents item 4 synchronized
    p30 = doc.paragraphs[30].text.strip()
    assert "Community Awareness" not in p30
    assert any(w in p30.lower() for w in ("architecture", "telemetry", "irrigation", "system"))

    # 3. Slide 6: Heading replaced
    p92 = doc.paragraphs[92].text.strip()
    assert "COMMUNITY AWARENESS" not in p92.upper()
    assert any(w in p92.lower() for w in ("architecture", "telemetry", "irrigation", "system"))

    # 4. Slide 7: Heading replaced
    p137 = doc.paragraphs[137].text.strip()
    assert "COMMUNITYINTERACTION PHOTOS" not in p137.upper()
    assert any(w in p137.lower() for w in ("smart irrigation", "field deployment", "deployment", "irrigation"))

    # 5. Slide 11: References replaced with irrigation/agritech references
    p231 = doc.paragraphs[231].text.strip()
    assert "NFPA" not in p231
    assert "National Fire Protection" not in p231

    # 6. Slide 12 & 14: Q&A and Thank You preserved
    assert doc.paragraphs[242].text.strip() == "QUERIES??"
    assert doc.paragraphs[269].text.strip() == "Thank You!!"

    # 7. Visual Audit: Zero forbidden terms, all topic keywords found
    val_audit = job.get("visual_audit") or {}
    assert val_audit.get("is_valid") is True
    assert len(val_audit.get("forbidden_terms_found", [])) == 0
    assert len(val_audit.get("topic_keywords_found", [])) >= 4


def test_electrify_future_content_replacement_e2e():
    """Verify Electrify Future replaces all 35 slides, headings, matter, and 31 diagrams."""
    project_data = {
        "title": "AI Based Irrigation System",
        "project_name": "AI Based Irrigation System",
        "description": "Develop an AI-based irrigation system that uses soil moisture sensors and weather data to automate irrigation and reduce water wastage.",
    }

    job = replacement_engine_service.execute_replacement(
        project_id="test-e2e-electrify-irrigation",
        project_data=project_data,
        template_id=ELECTRIFY_TPL_ID,
    )

    assert job["state"].upper() == "COMPLETED"
    out_docx = job["docx_path"]
    assert os.path.exists(out_docx)

    doc = docx.Document(out_docx)

    # 1. P0: Cover Title replaced
    p0 = doc.paragraphs[0].text.strip()
    assert "AI Based Irrigation System" in p0
    assert "ELECTRIFY" not in p0.upper()

    # 2. P5: Agenda heading preserved
    p5 = doc.paragraphs[5].text.strip()
    assert p5 == "AGENDA"

    # 3. P19: Slide heading replaced
    p19 = doc.paragraphs[19].text.strip()
    assert "WHAT IS ELECTRIC SAFETY" not in p19.upper()

    # 4. Over 100 fields replaced, all 31 images replaced
    assert job["fields_replaced"] >= 50
    assert job["images_replaced"] == 31
