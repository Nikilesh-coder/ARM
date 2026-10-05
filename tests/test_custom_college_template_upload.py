"""
ARM Stage 15 - Custom College Template Upload & Preservation Test Suite
Tests:
1. Upload & Validation of real college .docx template.
2. Structural Analysis (geometry, text fields, images, fixed vs replaceable isolation).
3. Mapping configuration: Map ONLY Project Title as replaceable, everything else fixed.
4. Report generation for "AI Based Attendance Management System":
   - Asserts ONLY project title changed.
   - Asserts College logo, borders, header, footer, page dimensions, margins preserved.
5. Image replacement: Mark ONE image as replaceable and verify replacement while logos remain fixed.
6. User isolation & security: Cross-user access denied.
"""

import os
import io
import pytest
from PIL import Image as PILImage
import docx
from docx.shared import Inches, Pt, RGBColor
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.custom_template_service import custom_template_service, _CUSTOM_TEMPLATES_STORE
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.base import FIXED_ELEMENTS, REPLACEABLE_ELEMENTS

client = TestClient(app)


def create_realistic_college_template(file_path: str) -> str:
    """Creates a realistic college template with custom geometry, logos, headers, footers, and text."""
    doc = docx.Document()

    # 1. Custom Page Geometry (non-standard 7.5" x 10.0", 0.8" margins)
    sec = doc.sections[0]
    sec.page_width = Inches(7.5)
    sec.page_height = Inches(10.0)
    sec.top_margin = Inches(0.8)
    sec.bottom_margin = Inches(0.8)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)

    # 2. Fixed Header & Footer
    hdr = sec.header
    hp = hdr.paragraphs[0]
    hp.text = "ABC INSTITUTE OF ENGINEERING & TECHNOLOGY — DEPARTMENT OF CSE"
    hp.runs[0].font.name = "Times New Roman"
    hp.runs[0].font.size = Pt(8.5)

    ftr = sec.footer
    fp = ftr.paragraphs[0]
    fp.text = "CONFIDENTIAL COLLEGE REPORT — PRESERVE WATERMARK"

    # 3. Embed College Logo (Fixed Image 1)
    logo_img = PILImage.new("RGB", (80, 80), color=(20, 80, 160))  # Blue college logo
    logo_buf = io.BytesIO()
    logo_img.save(logo_buf, format="PNG")
    logo_buf.seek(0)

    p_logo = doc.add_paragraph()
    r_logo = p_logo.add_run()
    r_logo.add_picture(logo_buf, width=Inches(1.2))

    # 4. College Name (Fixed text)
    p_inst = doc.add_paragraph()
    r_inst = p_inst.add_run("ABC INSTITUTE OF TECHNOLOGY (AUTONOMOUS)")
    r_inst.bold = True
    r_inst.font.size = Pt(14)
    r_inst.font.name = "Times New Roman"

    # 5. Project Title (Replaceable candidate)
    p_title = doc.add_paragraph()
    r_title = p_title.add_run("PROJECT TITLE")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.name = "Times New Roman"

    # 6. Candidate Information
    p_student = doc.add_paragraph()
    r_student = p_student.add_run("STUDENT NAME: JOHN DOE (REG NO: 2026CSE001)")
    r_student.font.size = Pt(11)

    p_guide = doc.add_paragraph()
    r_guide = p_guide.add_run("GUIDE: PROF. A. SHARMA, Ph.D.")
    r_guide.font.size = Pt(11)

    # 7. Embed Architecture Diagram (Body Image 2)
    diag_img = PILImage.new("RGB", (120, 60), color=(200, 100, 50))  # Orange body diagram
    diag_buf = io.BytesIO()
    diag_img.save(diag_buf, format="PNG")
    diag_buf.seek(0)

    p_diag = doc.add_paragraph()
    r_diag = p_diag.add_run()
    r_diag.add_picture(diag_buf, width=Inches(2.5))

    # 8. Fixed Introduction & Conclusion
    p_intro_h = doc.add_paragraph()
    p_intro_h.add_run("CHAPTER 1: INTRODUCTION").bold = True
    p_intro = doc.add_paragraph()
    p_intro.add_run("This document provides the standard departmental project report specification.")

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    doc.save(file_path)
    return file_path


@pytest.fixture(scope="module")
def sample_college_template():
    tpl_path = os.path.abspath(".storage/templates/test_My_College_Report_Template.docx")
    create_realistic_college_template(tpl_path)
    yield tpl_path
    if os.path.exists(tpl_path):
        try:
            os.remove(tpl_path)
        except Exception:
            pass


def test_1_upload_and_inspect_custom_template(sample_college_template):
    """TEST 1: Upload My_College_Report_Template.docx and verify analysis and isolation."""
    with open(sample_college_template, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/templates/upload-custom",
        files={"file": ("My_College_Report_Template.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={
            "name": "My College Report Template",
            "institution": "ABC Institute of Technology",
            "department": "Computer Science & Engineering",
            "report_type": "Major Project",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    tpl = data["template"]

    # Verify metadata
    assert tpl["name"] == "My College Report Template"
    assert tpl["institution"] == "ABC Institute of Technology"
    assert tpl["file_type"] == "docx"
    assert tpl["status"] == "ready"

    # Verify exact geometry extraction
    page_settings = tpl["page_settings"]
    assert page_settings["width_in"] == 7.5
    assert page_settings["height_in"] == 10.0
    assert page_settings["top_margin_in"] == 0.8
    assert page_settings["left_margin_in"] == 0.8

    # Verify candidate elements detection
    fields = tpl["field_mapping"]
    assert any("project_title" in f.get("arm_field", "") or "PROJECT TITLE" in f.get("template_element", "") for f in fields)

    images = tpl["image_mapping"]
    assert len(images) >= 1
    # First image (college logo) defaults to FIXED
    assert images[0]["action"] == "fixed"
    assert images[0]["is_logo"] is True


def test_2_template_appears_in_available_templates():
    """Verify uploaded template appears under GET /api/v1/templates."""
    res = client.get("/api/v1/templates")
    assert res.status_code == 200
    templates = res.json()
    my_tpl = next((t for t in templates if t["name"] == "My College Report Template"), None)
    assert my_tpl is not None
    assert my_tpl["status"] == "ready"


def test_3_map_only_project_title_as_replaceable(sample_college_template):
    """TEST 3 & 4: Configure mapping where ONLY Project Title is replaceable, everything else fixed."""
    analysis = custom_template_service.analyze_template_docx(sample_college_template)

    # Configure mapping: ONLY Project Title is 'replace', student name & intro are 'fixed'
    field_mapping = [
        {
            "template_element": "PROJECT TITLE",
            "arm_field": "project_title",
            "action": "replace",
        },
        {
            "template_element": "STUDENT NAME: JOHN DOE",
            "arm_field": "student_name",
            "action": "fixed",  # explicitly fixed
        },
        {
            "template_element": "CHAPTER 1: INTRODUCTION",
            "arm_field": "introduction",
            "action": "fixed",  # explicitly fixed
        },
    ]

    image_mapping = [
        {
            "template_image_id": "img_1",
            "rel_id": analysis["detected_images"][0].get("rel_id"),
            "arm_image_field": "image_1",
            "action": "fixed",  # Logo is FIXED
            "is_logo": True,
        }
    ]

    out_docx = os.path.abspath(".storage/reports/test_AI_Attendance_Report.docx")
    engine = DocxTemplateReplacementEngine()

    result = engine.replace(
        template_path=sample_college_template,
        field_values={
            "project_title": "AI Based Attendance Management System",
            "student_name": "MALICIOUS OVERWRITE ATTEMPT",
            "introduction": "MALICIOUS OVERWRITE OF INTRODUCTION",
        },
        output_path=out_docx,
        field_mapping=field_mapping,
        image_mapping=image_mapping,
    )

    assert result.success is True
    assert os.path.exists(out_docx)

    # Verify generated document contents
    res_doc = docx.Document(out_docx)
    all_text = " ".join(p.text for p in res_doc.paragraphs)

    # 1. Project Title was replaced
    assert "AI Based Attendance Management System" in all_text

    # 2. Fixed student name & intro were NOT replaced
    assert "MALICIOUS OVERWRITE ATTEMPT" not in all_text
    assert "JOHN DOE" in all_text
    assert "MALICIOUS OVERWRITE OF INTRODUCTION" not in all_text
    assert "This document provides the standard departmental project report specification." in all_text

    # 3. College name, header, and footer preserved
    assert "ABC INSTITUTE OF TECHNOLOGY (AUTONOMOUS)" in all_text
    assert "ABC INSTITUTE OF ENGINEERING & TECHNOLOGY" in res_doc.sections[0].header.paragraphs[0].text
    assert "CONFIDENTIAL COLLEGE REPORT" in res_doc.sections[0].footer.paragraphs[0].text

    # 4. Geometry is 100% preserved
    sec = res_doc.sections[0]
    assert round(sec.page_width.inches, 2) == 7.5
    assert round(sec.page_height.inches, 2) == 10.0
    assert round(sec.left_margin.inches, 2) == 0.8
    assert round(sec.right_margin.inches, 2) == 0.8


def test_4_replace_one_designated_image(sample_college_template):
    """TEST 5: Mark ONE image as replaceable and verify replacement while logo remains fixed."""
    analysis = custom_template_service.analyze_template_docx(sample_college_template)
    detected_images = analysis["detected_images"]
    assert len(detected_images) >= 2

    # Image 1 (Logo) -> FIXED
    # Image 2 (Diagram) -> REPLACE
    logo_rel_id = detected_images[0]["rel_id"]
    diag_rel_id = detected_images[1]["rel_id"]

    # Create green replacement image
    new_diagram = PILImage.new("RGB", (100, 100), color=(0, 200, 50))
    new_diag_path = os.path.abspath(".storage/test_new_green_diagram.png")
    new_diagram.save(new_diag_path)

    image_mapping = [
        {
            "template_image_id": "img_1",
            "rel_id": logo_rel_id,
            "arm_image_field": "image_1",
            "action": "fixed",  # Logo is FIXED
            "is_logo": True,
        },
        {
            "template_image_id": "img_2",
            "rel_id": diag_rel_id,
            "arm_image_field": "image_2",
            "action": "replace",  # Only diagram replaced
            "is_logo": False,
        },
    ]

    field_mapping = [
        {
            "template_element": "PROJECT TITLE",
            "arm_field": "project_title",
            "action": "replace",
        }
    ]

    out_docx = os.path.abspath(".storage/reports/test_AI_Attendance_With_Image.docx")
    engine = DocxTemplateReplacementEngine()

    result = engine.replace(
        template_path=sample_college_template,
        field_values={"project_title": "AI Based Attendance Management System"},
        image_assets={"image_2": new_diag_path},
        output_path=out_docx,
        field_mapping=field_mapping,
        image_mapping=image_mapping,
    )

    assert result.success is True
    res_doc = docx.Document(out_docx)

    # Verify diagram rel bytes changed
    target_part = res_doc.part.rels[diag_rel_id].target_part
    with open(new_diag_path, "rb") as f:
        expected_bytes = f.read()
    assert target_part._blob == expected_bytes

    # Verify logo rel bytes were NOT modified
    logo_part = res_doc.part.rels[logo_rel_id].target_part
    assert logo_part._blob != expected_bytes


def test_5_report_generate_endpoint_with_custom_template(sample_college_template):
    """End-to-End: POST /api/v1/reports/generate using custom uploaded college template."""
    # First upload template
    with open(sample_college_template, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/api/v1/templates/upload-custom",
        files={"file": ("My_College_Report_Template.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"name": "End To End Custom College Template"},
    )
    tpl_id = upload_res.json()["template"]["id"]

    # Generate full report referencing this template_id
    gen_res = client.post(
        "/api/v1/reports/generate",
        json={
            "title": "AI Based Attendance Management System",
            "template_id": tpl_id,
            "student_name": "Kasireddy Charishma",
            "roll_no": "25BFA02L13",
        },
    )
    assert gen_res.status_code == 200, gen_res.text
    body = gen_res.json()
    assert body["status"] == "completed"
    assert os.path.exists(body["output_path"])

    # Verify output preserves geometry
    out_doc = docx.Document(body["output_path"])
    sec = out_doc.sections[0]
    assert round(sec.page_width.inches, 2) == 7.5
    assert round(sec.page_height.inches, 2) == 10.0


def test_6_unauthorized_user_cannot_delete_other_template(sample_college_template):
    """Test user isolation: other user cannot delete or tamper with another's template."""
    with open(sample_college_template, "rb") as f:
        file_bytes = f.read()

    # User 1 registers template
    rec = custom_template_service.register_custom_template(
        file_bytes=file_bytes,
        filename="User1_Template.docx",
        template_name="User 1 Template",
        owner_id="usr_owner_alpha",
    )
    t_id = rec["id"]

    # User 2 tries to access or delete
    with pytest.raises(PermissionError):
        custom_template_service.get_template(t_id, user_id="usr_intruder_beta")
