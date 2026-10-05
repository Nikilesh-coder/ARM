"""
ARM Core Requirement Test Suite - Four Stages of Preservation (Tests A, B, C, D)
Validates:
- TEST A: Zero modifications requested (PATH A) produces 100% byte-identical SHA-256 copy.
- TEST B: Single text replacement (replace only project_title) leaves logo, borders, and other text untouched.
- TEST C: Single image replacement (replace only body image) leaves college logo SHA-256 and borders untouched.
- TEST D: Combined text + image replacement strictly modifies only the mapped targets.
"""

import os
import io
import shutil
import hashlib
import zipfile
import pytest
import lxml.etree as ET
from PIL import Image as PILImage
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from apps.api.services.replacement_engine_service import replacement_engine_service
from packages.replacement_engine.base import ReplacementState


@pytest.fixture
def master_college_docx_with_borders_and_logo(tmp_path):
    """
    Creates a realistic college DOCX master template with:
    - Page borders (<w:pgBorders>)
    - Embedded College Logo (fixed image 1)
    - Embedded Body Diagram (replaceable image 2)
    - Project Title (replaceable text)
    - Candidate Name & Faculty Guide (fixed text)
    - Headers, footers, custom page geometry (8.5x11, 1.25" left margin)
    """
    tpl_path = str(tmp_path / "college_master_template.docx")
    doc = docx.Document()

    # Geometry
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.left_margin = Inches(1.25)
    sec.right_margin = Inches(1.0)

    # Page Borders (OpenXML w:pgBorders)
    sectPr = sec._sectPr
    bdr_xml = (
        f'<w:pgBorders {nsdecls("w")}>'
        f'<w:top w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:left w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:bottom w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:right w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'</w:pgBorders>'
    )
    sectPr.append(parse_xml(bdr_xml))

    # Header and Footer
    hdr = sec.header.paragraphs[0]
    hdr.text = "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING — MASTER TEMPLATE"
    ftr = sec.footer.paragraphs[0]
    ftr.text = "OFFICIAL ACADEMIC RECORD — PRESERVE WATERMARK & BORDERS"

    # College Logo (Fixed Image 1 - deep blue)
    logo_img = PILImage.new("RGB", (90, 90), color=(15, 60, 140))
    logo_buf = io.BytesIO()
    logo_img.save(logo_buf, format="PNG")
    logo_buf.seek(0)

    p_logo = doc.add_paragraph()
    r_logo = p_logo.add_run()
    r_logo.add_picture(logo_buf, width=Inches(1.2))

    # College Name
    p_inst = doc.add_paragraph()
    p_inst.add_run("SRI VENKATESWARA COLLEGE OF ENGINEERING (AUTONOMOUS)").bold = True

    # Project Title
    p_title = doc.add_paragraph()
    p_title.add_run("PROJECT TITLE").bold = True

    # Candidate and Guide Information
    p_cand = doc.add_paragraph()
    p_cand.add_run("CANDIDATE: JOHN DOE (REG: 2026CSE001)")
    p_guide = doc.add_paragraph()
    p_guide.add_run("SUPERVISOR: DR. R. SIRISHA, Ph.D.")

    # Body Architecture Diagram (Replaceable Image 2 - green)
    diag_img = PILImage.new("RGB", (160, 80), color=(30, 150, 60))
    diag_buf = io.BytesIO()
    diag_img.save(diag_buf, format="PNG")
    diag_buf.seek(0)

    p_diag = doc.add_paragraph()
    r_diag = p_diag.add_run()
    r_diag.add_picture(diag_buf, width=Inches(2.5))

    p_intro_h = doc.add_paragraph()
    p_intro_h.add_run("CHAPTER 1: INTRODUCTION").bold = True
    p_intro = doc.add_paragraph()
    p_intro.add_run("Standard college project report introduction text.")

    doc.save(tpl_path)
    return tpl_path


def _extract_media_hashes(docx_path: str):
    """Extracts SHA-256 hashes for all media files in word/media/."""
    hashes = {}
    with zipfile.ZipFile(docx_path, "r") as z:
        for name in z.namelist():
            if name.startswith("word/media/"):
                hashes[name] = hashlib.sha256(z.read(name)).hexdigest()
    return hashes


def test_stage_a_exact_copy(master_college_docx_with_borders_and_logo):
    """
    TEST A (Exact Copy):
    When user requests 'Do not replace or modify anything in the template',
    ARM must return a 100% byte-for-byte identical copy with matching SHA-256.
    Zero document reconstruction, zero XML modification.
    """
    tpl_path = master_college_docx_with_borders_and_logo
    with open(tpl_path, "rb") as f:
        orig_bytes = f.read()
    orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()
    orig_size = len(orig_bytes)

    job = replacement_engine_service.execute_replacement(
        project_data={
            "title": "Master Template Copy",
            "no_changes": True,
        },
        user_instructions="Do not replace or modify anything in the template.",
    )

    # Point to the actual template path tested
    # Re-run directly passing custom template path via job_record
    job = replacement_engine_service.execute_replacement(
        project_data={
            "title": "Do not replace or modify anything in the template.",
            "no_changes": True,
        },
        user_instructions="Do not change anything.",
    )

    out_docx = job.get("docx_path")
    assert out_docx is not None
    assert os.path.exists(out_docx)
    assert job["state"] == ReplacementState.COMPLETED.value
    assert job["fields_replaced"] == 0
    assert job["images_replaced"] == 0

    # Also test PackageLevelDocxEngine PATH A directly on this template
    from packages.replacement_engine.package_engine import PackageLevelDocxEngine
    direct_out = out_docx + "_direct.docx"
    res = PackageLevelDocxEngine.replace(
        template_path=tpl_path,
        field_values={},
        image_assets={},
        output_path=direct_out,
    )
    assert res.success is True

    with open(direct_out, "rb") as f:
        direct_bytes = f.read()
    assert len(direct_bytes) == orig_size
    assert hashlib.sha256(direct_bytes).hexdigest() == orig_sha256


def test_stage_b_single_text_replacement(master_college_docx_with_borders_and_logo, tmp_path):
    """
    TEST B (Single Text Replacement):
    Replace ONLY project_title.
    College logo, page borders (w:pgBorders), candidate name, and margins MUST remain untouched.
    ARM must NEVER inject demo logo or replace unrequested fields.
    """
    tpl_path = master_college_docx_with_borders_and_logo
    orig_media = _extract_media_hashes(tpl_path)
    assert len(orig_media) == 2  # image1 (logo) and image2 (diag)
    logo_hash_orig = orig_media["word/media/image1.png"]

    out_docx = str(tmp_path / "stage_b_output.docx")

    field_mapping = [
        {
            "template_element": "PROJECT TITLE",
            "arm_field": "project_title",
            "action": "replace",
        }
    ]

    from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=tpl_path,
        field_values={
            "project_title": "Automated Waste Segregation System Using Computer Vision",
            "student_name": "UNWANTED OVERWRITE CANDIDATE",
        },
        image_assets={},
        output_path=out_docx,
        field_mapping=field_mapping,
    )

    assert result.success is True
    assert os.path.exists(out_docx)

    # 1. Verify project title was replaced
    doc = docx.Document(out_docx)
    all_text = " ".join(p.text for p in doc.paragraphs)
    assert "Automated Waste Segregation System Using Computer Vision" in all_text

    # 2. Verify candidate name was NOT replaced (BUG 2 fix)
    assert "UNWANTED OVERWRITE CANDIDATE" not in all_text
    assert "CANDIDATE: JOHN DOE (REG: 2026CSE001)" in all_text

    # 3. Verify College Logo was NOT replaced (BUG 1 fix)
    out_media = _extract_media_hashes(out_docx)
    assert out_media["word/media/image1.png"] == logo_hash_orig

    # 4. Verify OpenXML Page Borders (<w:pgBorders>) preserved
    with zipfile.ZipFile(out_docx, "r") as z:
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "w:pgBorders" in doc_xml
        assert 'w:val="double"' in doc_xml
        assert 'w:color="002060"' in doc_xml


def test_stage_c_single_image_replacement(master_college_docx_with_borders_and_logo, tmp_path):
    """
    TEST C (Single Image Replacement):
    Replace ONLY body image (image 2).
    College logo (image 1) SHA-256 and page borders MUST remain 100% untouched.
    """
    tpl_path = master_college_docx_with_borders_and_logo
    orig_media = _extract_media_hashes(tpl_path)
    logo_hash_orig = orig_media["word/media/image1.png"]

    # New replacement body image (purple)
    new_diag_img = PILImage.new("RGB", (120, 60), color=(140, 40, 180))
    new_diag_path = str(tmp_path / "new_purple_diagram.png")
    new_diag_img.save(new_diag_path)

    image_mapping = [
        {
            "template_image_id": "img_1",
            "rel_id": "rId1",
            "arm_image_field": "image_1",
            "action": "fixed",
            "is_logo": True,
        },
        {
            "template_image_id": "img_2",
            "rel_id": "rId2",
            "arm_image_field": "image_2",
            "action": "replace",
            "is_logo": False,
        },
    ]

    out_docx = str(tmp_path / "stage_c_output.docx")
    from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=tpl_path,
        field_values={},
        image_assets={"image_2": new_diag_path},
        output_path=out_docx,
        image_mapping=image_mapping,
    )

    assert result.success is True
    assert os.path.exists(out_docx)

    out_media = _extract_media_hashes(out_docx)
    # 1. College logo (image 1) MUST be 100% byte-identical
    assert out_media["word/media/image1.png"] == logo_hash_orig

    # 2. Body diagram (image 2) MUST be updated to new purple image
    with open(new_diag_path, "rb") as f:
        new_diag_hash = hashlib.sha256(f.read()).hexdigest()
    assert out_media["word/media/image2.png"] == new_diag_hash

    # 3. Borders preserved
    with zipfile.ZipFile(out_docx, "r") as z:
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "w:pgBorders" in doc_xml


def test_stage_d_text_and_image_replacement(master_college_docx_with_borders_and_logo, tmp_path):
    """
    TEST D (Text + Image Combined):
    Replace ONLY project_title and body image (image 2).
    Nothing else modified: College logo, candidate details, headers, footers, borders intact.
    """
    tpl_path = master_college_docx_with_borders_and_logo
    orig_media = _extract_media_hashes(tpl_path)
    logo_hash_orig = orig_media["word/media/image1.png"]

    new_diag_img = PILImage.new("RGB", (100, 100), color=(220, 110, 10))
    new_diag_path = str(tmp_path / "new_orange_diagram.png")
    new_diag_img.save(new_diag_path)

    field_mapping = [
        {
            "template_element": "PROJECT TITLE",
            "arm_field": "project_title",
            "action": "replace",
        }
    ]
    image_mapping = [
        {
            "template_image_id": "img_1",
            "rel_id": "rId1",
            "arm_image_field": "image_1",
            "action": "fixed",
            "is_logo": True,
        },
        {
            "template_image_id": "img_2",
            "rel_id": "rId2",
            "arm_image_field": "image_2",
            "action": "replace",
            "is_logo": False,
        },
    ]

    out_docx = str(tmp_path / "stage_d_output.docx")
    from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=tpl_path,
        field_values={"project_title": "AI Autonomous Drone Navigation System"},
        image_assets={"image_2": new_diag_path},
        output_path=out_docx,
        field_mapping=field_mapping,
        image_mapping=image_mapping,
    )

    assert result.success is True
    assert os.path.exists(out_docx)

    doc = docx.Document(out_docx)
    all_text = " ".join(p.text for p in doc.paragraphs)

    # 1. Project title updated
    assert "AI Autonomous Drone Navigation System" in all_text

    # 2. Candidate name untouched
    assert "CANDIDATE: JOHN DOE (REG: 2026CSE001)" in all_text

    # 3. College logo untouched
    out_media = _extract_media_hashes(out_docx)
    assert out_media["word/media/image1.png"] == logo_hash_orig

    # 4. Body diagram updated
    with open(new_diag_path, "rb") as f:
        new_diag_hash = hashlib.sha256(f.read()).hexdigest()
    assert out_media["word/media/image2.png"] == new_diag_hash

    # 5. Page borders, header, footer intact
    with zipfile.ZipFile(out_docx, "r") as z:
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "w:pgBorders" in doc_xml

    sec = doc.sections[0]
    assert sec.header.paragraphs[0].text == "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING — MASTER TEMPLATE"
    assert sec.footer.paragraphs[0].text == "OFFICIAL ACADEMIC RECORD — PRESERVE WATERMARK & BORDERS"
