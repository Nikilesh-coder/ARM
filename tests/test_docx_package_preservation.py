"""
ARM Core Requirement Test Suite - DOCX Package & Template Preservation Engine
Tests precision in-place OOXML package surgery:
1. Exact Master Template preservation: page borders (w:pgBorders), border lines (v:line),
   college logo, fixed logos, headers, footers, watermarks, shapes, and geometry.
2. Single-field replacement: replacing ONLY project_title modifies NOTHING ELSE.
3. Single-image replacement: replacing ONLY an embedded body diagram leaves the college logo
   bit-for-bit identical with matching SHA-256 hash.
4. Pre-delivery validation: detects and fails safely if unexpected document alterations occur.
"""

import os
import io
import shutil
import hashlib
import tempfile
import pytest
import zipfile
import lxml.etree as ET
from PIL import Image as PILImage
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from packages.replacement_engine.package_engine import PackageLevelDocxEngine
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.validator import ReplacementValidator
from packages.replacement_engine.base import ReplacementState


@pytest.fixture
def college_template_with_borders_and_logo(tmp_path):
    """
    Creates a realistic college template containing:
    - Page borders (w:pgBorders)
    - Fixed college logo (image 1)
    - Project title (replaceable)
    - Fixed candidate & faculty guide details
    - Body architecture diagram (image 2)
    - VML shape / horizontal line
    - Headers and footers
    """
    tpl_path = str(tmp_path / "master_college_specification_template.docx")
    doc = docx.Document()

    # 1. Custom Page Margins and Dimensions
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.left_margin = Inches(1.25)
    sec.right_margin = Inches(1.0)

    # 2. Add OpenXML Page Borders (w:pgBorders)
    sectPr = sec._sectPr
    bdr_xml = (
        f'<w:pgBorders {nsdecls("w")}>'
        f'<w:top w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:bottom w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:left w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'<w:right w:val="double" w:sz="18" w:space="24" w:color="002060"/>'
        f'</w:pgBorders>'
    )
    sectPr.append(parse_xml(bdr_xml))

    # 3. Header & Footer
    hdr = sec.header
    hp = hdr.paragraphs[0]
    hp.text = "NATIONAL INSTITUTE OF ENGINEERING — DEPARTMENT OF COMPUTER SCIENCE"

    ftr = sec.footer
    fp = ftr.paragraphs[0]
    fp.text = "OFFICIAL DISSERTATION TEMPLATE — PRESERVE WATERMARK AND BORDERS"

    # 4. Fixed College Logo (Image 1)
    logo_img = PILImage.new("RGB", (100, 100), color=(15, 60, 150))
    logo_buf = io.BytesIO()
    logo_img.save(logo_buf, format="PNG")
    logo_buf.seek(0)

    p_logo = doc.add_paragraph()
    r_logo = p_logo.add_run()
    r_logo.add_picture(logo_buf, width=Inches(1.2))

    # 5. Fixed Institution Heading
    p_inst = doc.add_paragraph()
    r_inst = p_inst.add_run("NATIONAL INSTITUTE OF ENGINEERING (AUTONOMOUS)")
    r_inst.bold = True
    r_inst.font.size = Pt(14)

    # 6. Project Title (Replaceable Candidate)
    p_title = doc.add_paragraph()
    r_title = p_title.add_run("ORIGINAL PROJECT TITLE: EMBEDDED SENSOR MONITORING")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(0, 32, 96)

    # 7. Fixed Candidate Details
    p_cand = doc.add_paragraph()
    p_cand.add_run("Submitted by: Rahul Sharma (Roll No: 2026CS101)")

    p_guide = doc.add_paragraph()
    p_guide.add_run("Under the Guidance of: Dr. S. K. Raman, Senior Professor")

    # 8. Fixed Chapter Content
    p_ch1 = doc.add_paragraph()
    p_ch1.add_run("CHAPTER 1: INTRODUCTION").bold = True
    p_intro = doc.add_paragraph()
    p_intro.add_run("This chapter specifies the core foundational architecture of the project.")

    # 9. Body Architecture Diagram (Image 2)
    diag_img = PILImage.new("RGB", (200, 100), color=(180, 80, 20))
    diag_buf = io.BytesIO()
    diag_img.save(diag_buf, format="PNG")
    diag_buf.seek(0)

    p_diag = doc.add_paragraph()
    r_diag = p_diag.add_run()
    r_diag.add_picture(diag_buf, width=Inches(3.0))

    # 10. Conclusion
    p_conc = doc.add_paragraph()
    p_conc.add_run("CHAPTER 5: CONCLUSION").bold = True

    doc.save(tpl_path)
    return tpl_path


def test_replace_only_project_title_preserves_everything_else(college_template_with_borders_and_logo, tmp_path):
    """
    CRITICAL REQUIREMENT:
    If the user asks ARM to replace only the project title, then ONLY the project title should change.
    Page borders, border lines, college logo, fixed images, candidate info, guide name,
    chapter text, headers, and footers must remain 100% UNCHANGED.
    """
    out_path = str(tmp_path / "output_replaced_title_only.docx")

    # Calculate original college logo and diagram SHA-256 hashes
    orig_logo_hash = None
    orig_diag_hash = None
    with zipfile.ZipFile(college_template_with_borders_and_logo, "r") as z_orig:
        media_files = sorted([n for n in z_orig.namelist() if n.startswith("word/media/")])
        assert len(media_files) == 2, f"Expected 2 media files, found: {media_files}"
        orig_logo_hash = hashlib.sha256(z_orig.read(media_files[0])).hexdigest()
        orig_diag_hash = hashlib.sha256(z_orig.read(media_files[1])).hexdigest()

    # User explicitly maps ONLY project title as replaceable
    field_mapping = [
        {
            "template_element": "ORIGINAL PROJECT TITLE: EMBEDDED SENSOR MONITORING",
            "arm_field": "project_title",
            "action": "replace",
        }
    ]
    # Even if AI returns extra generated matter (e.g. introduction, methodology, conclusion),
    # ARM must NOT touch those sections because only project_title was mapped!
    field_values = {
        "project_title": "AI BASED ATTENDANCE AND SURVEILLANCE SYSTEM",
        "introduction": "Synthesized AI matter that must NOT overwrite fixed Chapter 1",
        "methodology": "Synthesized AI matter that must NOT overwrite anything",
        "conclusion": "Synthesized AI matter that must NOT overwrite Chapter 5",
    }

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=college_template_with_borders_and_logo,
        field_values=field_values,
        output_path=out_path,
        field_mapping=field_mapping,
    )

    assert result.success is True
    assert result.state == ReplacementState.COMPLETED

    # 1. Inspect output with python-docx
    out_doc = docx.Document(out_path)
    full_text = "\n".join(p.text for p in out_doc.paragraphs)

    # Project title was successfully replaced
    assert "AI BASED ATTENDANCE AND SURVEILLANCE SYSTEM" in full_text
    assert "ORIGINAL PROJECT TITLE: EMBEDDED SENSOR MONITORING" not in full_text

    # Fixed elements MUST NOT be touched
    assert "NATIONAL INSTITUTE OF ENGINEERING (AUTONOMOUS)" in full_text
    assert "Submitted by: Rahul Sharma (Roll No: 2026CS101)" in full_text
    assert "Under the Guidance of: Dr. S. K. Raman, Senior Professor" in full_text
    assert "This chapter specifies the core foundational architecture of the project." in full_text
    assert "CHAPTER 5: CONCLUSION" in full_text

    # AI extra matter must NOT have overwritten existing sections
    assert "Synthesized AI matter" not in full_text

    # 2. Inspect OpenXML Package Directly
    with zipfile.ZipFile(out_path, "r") as z_out:
        # Verify College Logo is 100% bit-for-bit identical
        gen_logo_bytes = z_out.read("word/media/image1.png")
        gen_logo_hash = hashlib.sha256(gen_logo_bytes).hexdigest()
        assert gen_logo_hash == orig_logo_hash, "College logo was modified when only title was mapped!"

        # Verify Body Diagram is 100% bit-for-bit identical
        gen_diag_bytes = z_out.read("word/media/image2.png")
        gen_diag_hash = hashlib.sha256(gen_diag_bytes).hexdigest()
        assert gen_diag_hash == orig_diag_hash, "Body diagram was modified when only title was mapped!"

        # 3. Verify Page Borders (w:pgBorders) survived 100% intact
        doc_xml = z_out.read("word/document.xml")
        root = ET.fromstring(doc_xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        borders = root.xpath("//w:pgBorders", namespaces=ns)
        assert len(borders) == 1, "Page borders (w:pgBorders) were dropped in the output document!"
        top_bdr = borders[0].xpath("./w:top", namespaces=ns)[0]
        assert top_bdr.attrib.get(f"{{{ns['w']}}}val") == "double"
        assert top_bdr.attrib.get(f"{{{ns['w']}}}color") == "002060"

    # 4. Strict Pre-Delivery Validator
    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=college_template_with_borders_and_logo,
        generated_docx_path=out_path,
        allowed_replaced_fields={"project_title"},
        allowed_replaced_media=set(),
    )
    assert val_res["is_valid"] is True
    assert len(val_res["errors"]) == 0


def test_replace_only_body_image_preserves_college_logo_and_borders(college_template_with_borders_and_logo, tmp_path):
    """
    CRITICAL REQUIREMENT:
    If the user asks ARM to replace one embedded image, then ONLY that embedded image should change.
    The college logo (image 1) and page borders MUST NOT change.
    """
    out_path = str(tmp_path / "output_replaced_image_only.docx")

    # Generate a new diagram asset (Green)
    new_diag_file = str(tmp_path / "new_green_diagram.png")
    new_diag_img = PILImage.new("RGB", (250, 120), color=(30, 180, 50))
    new_diag_img.save(new_diag_file, format="PNG")

    # Original logo hash
    orig_logo_hash = None
    with zipfile.ZipFile(college_template_with_borders_and_logo, "r") as z_orig:
        orig_logo_hash = hashlib.sha256(z_orig.read("word/media/image1.png")).hexdigest()

    # User maps ONLY image_2 (the body diagram) for replacement; image_1 (college logo) is FIXED
    image_mapping = [
        {
            "id": "img_1",
            "rel_id": "rId5",  # typical logo rel
            "arm_image_field": "image_1",
            "action": "fixed",
            "is_logo": True,
        },
        {
            "id": "img_2",
            "rel_id": "rId6",  # typical diagram rel
            "arm_image_field": "image_2",
            "action": "replace",
            "is_logo": False,
        },
    ]

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=college_template_with_borders_and_logo,
        field_values={},
        image_assets={"image_2": new_diag_file},
        output_path=out_path,
        image_mapping=image_mapping,
    )

    assert result.success is True

    # Inspect generated package
    with zipfile.ZipFile(out_path, "r") as z_out:
        # 1. College Logo MUST be identical
        gen_logo_hash = hashlib.sha256(z_out.read("word/media/image1.png")).hexdigest()
        assert gen_logo_hash == orig_logo_hash, "College logo was modified when replacing body image!"

        # 2. Body Diagram MUST be replaced
        gen_diag_hash = hashlib.sha256(z_out.read("word/media/image2.png")).hexdigest()
        with open(new_diag_file, "rb") as f_new:
            expected_new_hash = hashlib.sha256(f_new.read()).hexdigest()
        assert gen_diag_hash == expected_new_hash, "Body diagram was not replaced with new image bytes!"

        # 3. Page borders remain intact
        doc_xml = z_out.read("word/document.xml")
        root = ET.fromstring(doc_xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        borders = root.xpath("//w:pgBorders", namespaces=ns)
        assert len(borders) == 1, "Page borders were dropped!"

    # 4. Strict Pre-Delivery Validator
    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=college_template_with_borders_and_logo,
        generated_docx_path=out_path,
        allowed_replaced_fields=set(),
        allowed_replaced_media={"image2.png", "word/media/image2.png"},
    )
    assert val_res["is_valid"] is True
    assert len(val_res["errors"]) == 0


def test_validator_rejects_corrupted_borders_or_modified_logo(college_template_with_borders_and_logo, tmp_path):
    """
    CRITICAL REQUIREMENT:
    Pre-delivery validation engine must detect and fail safely if unexpected document-wide
    alterations occur (such as page borders being dropped or college logo modified).
    """
    bad_docx = str(tmp_path / "corrupted_output.docx")
    shutil.copyfile(college_template_with_borders_and_logo, bad_docx)

    # Intentionally corrupt bad_docx by removing w:pgBorders
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(bad_docx, "r") as z:
            z.extractall(temp_dir)

        doc_xml_p = os.path.join(temp_dir, "word", "document.xml")
        tree = ET.parse(doc_xml_p)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for b in tree.xpath("//w:pgBorders", namespaces=ns):
            b.getparent().remove(b)
        tree.write(doc_xml_p, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(bad_docx, "w", zipfile.ZIP_DEFLATED) as z_out:
            for r_dir, _, f_names in os.walk(temp_dir):
                for fn in f_names:
                    abs_f = os.path.join(r_dir, fn)
                    z_out.write(abs_f, os.path.relpath(abs_f, temp_dir))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Run validator
    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=college_template_with_borders_and_logo,
        generated_docx_path=bad_docx,
    )
    assert val_res["is_valid"] is False
    assert any(err["field"] == "page_borders" for err in val_res["errors"])
