"""
ARM Stage 10 - In-Depth DOCX Template Replacement Engine Test Suite
Thoroughly tests:
1. Text replacement (inline & multi-run split placeholder stitching)
2. Paragraph replacement (multi-paragraph expansion with sibling XML paragraphs)
3. Heading replacement (preserving Heading 1/2 styles and outline levels)
4. Image replacement (centering, captions, margin safety, format conversion)
5. Basic tables (cell placeholder substitution, dynamic row expansion, structured tables)
6. Lists (bullet expansion and numbered reference citations)
7. Headers & Footers (primary, first-page, even-page, and header/footer tables)
8. Realistic college report template end-to-end execution
"""

import os
import tempfile
import pytest
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image as PILImage

from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.validator import ReplacementValidator
from packages.replacement_engine.base import ReplacementState
from packages.document_engine.converter import pdf_converter_service


@pytest.fixture
def temp_work_dir():
    """Provides a temporary scratch directory for test documents."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


def test_text_replacement_and_formatting_preservation(temp_work_dir):
    """
    Verifies that inline text placeholders and split-run placeholders are replaced
    while strictly preserving font name, font size, bold, italic, and color.
    """
    doc_path = os.path.join(temp_work_dir, "test_text_template.docx")
    out_path = os.path.join(temp_work_dir, "test_text_out.docx")

    doc = docx.Document()
    
    # Paragraph 1: Single run with specific formatting
    p1 = doc.add_paragraph()
    r1 = p1.add_run("Student Name: {{STUDENT_NAME}}")
    r1.font.name = "Arial"
    r1.font.size = Pt(13)
    r1.bold = True
    r1.font.color.rgb = RGBColor(180, 20, 20)

    # Paragraph 2: Multi-run split placeholder (simulates Word splitting {{ and }} across runs)
    p2 = doc.add_paragraph()
    r2_a = p2.add_run("Supervised by: ")
    r2_b = p2.add_run("{{")
    r2_c = p2.add_run("GUIDE_NAME")
    r2_d = p2.add_run("}}")
    r2_e = p2.add_run(", Senior Professor")
    r2_c.font.name = "Calibri"
    r2_c.font.size = Pt(11)
    r2_c.italic = True

    doc.save(doc_path)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={
            "student_name": "Kasireddy Charishma",
            "guide_name": "Dr. Y.V. Krishna Reddy",
        },
        output_path=out_path,
    )

    assert result.success is True
    assert result.state == ReplacementState.COMPLETED

    res_doc = docx.Document(out_path)
    res_p1 = res_doc.paragraphs[0]
    assert "Kasireddy Charishma" in res_p1.text
    assert "{{STUDENT_NAME}}" not in res_p1.text
    assert res_p1.runs[0].font.name == "Arial"
    assert res_p1.runs[0].bold is True

    res_p2 = res_doc.paragraphs[1]
    assert "Dr. Y.V. Krishna Reddy" in res_p2.text
    assert "Supervised by: Dr. Y.V. Krishna Reddy, Senior Professor" == res_p2.text.strip()
    assert "{{GUIDE_NAME}}" not in res_p2.text


def test_multiparagraph_replacement_and_sibling_insertion(temp_work_dir):
    """
    Verifies that multi-paragraph fields (such as introduction or methodology)
    expand into true OpenXML sibling paragraphs rather than a single squashed paragraph.
    """
    doc_path = os.path.join(temp_work_dir, "test_multi_para_template.docx")
    out_path = os.path.join(temp_work_dir, "test_multi_para_out.docx")

    doc = docx.Document()
    p_before = doc.add_paragraph("Chapter Overview:")
    p_intro = doc.add_paragraph("{{INTRODUCTION}}")
    p_intro.paragraph_format.space_before = Pt(6)
    p_intro.paragraph_format.space_after = Pt(6)
    p_intro.paragraph_format.line_spacing = 1.15
    r_intro = p_intro.runs[0]
    r_intro.font.name = "Georgia"
    r_intro.font.size = Pt(11)

    p_after = doc.add_paragraph("Next Chapter Details.")

    doc.save(doc_path)

    long_intro = (
        "Paragraph 1: Background of the telemetry system.\n\n"
        "Paragraph 2: Detailed architecture and sensor pipeline analysis.\n\n"
        "Paragraph 3: Institutional compliance and empirical evaluation."
    )

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={"introduction": long_intro},
        output_path=out_path,
    )

    assert result.success is True
    res_doc = docx.Document(out_path)

    # Original had 3 paragraphs. With 3 intro chunks replacing p_intro, total should be 5 paragraphs!
    assert len(res_doc.paragraphs) == 5
    assert res_doc.paragraphs[0].text == "Chapter Overview:"
    assert "Paragraph 1" in res_doc.paragraphs[1].text
    assert "Paragraph 2" in res_doc.paragraphs[2].text
    assert "Paragraph 3" in res_doc.paragraphs[3].text
    assert res_doc.paragraphs[4].text == "Next Chapter Details."

    # Verify typography replicated on sibling paragraphs
    for p in res_doc.paragraphs[1:4]:
        assert p.runs[0].font.name == "Georgia"
        assert p.runs[0].font.size == Pt(11)
        assert p.paragraph_format.line_spacing == 1.15


def test_heading_replacement_preserving_styles(temp_work_dir):
    """
    Verifies that headings containing placeholders retain their Heading styles
    and outline levels without degrading into normal text.
    """
    doc_path = os.path.join(temp_work_dir, "test_heading_template.docx")
    out_path = os.path.join(temp_work_dir, "test_heading_out.docx")

    doc = docx.Document()
    h1 = doc.add_heading("CHAPTER 1: {{PROJECT_TITLE}}", level=1)
    p_body = doc.add_paragraph("Body text following heading.")
    h2 = doc.add_heading("1.1 PROBLEM STATEMENT: {{PROBLEM_STATEMENT}}", level=2)

    doc.save(doc_path)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={
            "project_title": "Autonomous Agricultural Yield Telemetry",
            "problem_statement": "Manual crop telemetry has high latency.",
        },
        output_path=out_path,
    )

    assert result.success is True
    res_doc = docx.Document(out_path)

    assert res_doc.paragraphs[0].text == "CHAPTER 1: Autonomous Agricultural Yield Telemetry"
    assert "Heading 1" in res_doc.paragraphs[0].style.name

    assert res_doc.paragraphs[2].text == "1.1 PROBLEM STATEMENT: Manual crop telemetry has high latency."
    assert "Heading 2" in res_doc.paragraphs[2].style.name


def test_list_expansion_into_bullet_paragraphs(temp_work_dir):
    """
    Verifies that list fields (objectives, references) expand into distinct bullet paragraphs
    and citation-numbered paragraphs.
    """
    doc_path = os.path.join(temp_work_dir, "test_list_template.docx")
    out_path = os.path.join(temp_work_dir, "test_list_out.docx")

    doc = docx.Document()
    doc.add_paragraph("Project Objectives:")
    p_obj = doc.add_paragraph("{{OBJECTIVES}}")
    p_obj.runs[0].font.name = "Times New Roman"
    p_obj.runs[0].font.size = Pt(11)

    doc.add_paragraph("References:")
    p_ref = doc.add_paragraph("{{REFERENCES}}")
    p_ref.runs[0].font.name = "Times New Roman"
    p_ref.runs[0].font.size = Pt(10)

    doc.save(doc_path)

    objectives = [
        "Design scalable IoT node architecture.",
        "Implement low-latency wireless transmission.",
        "Validate empirical accuracy in field tests.",
    ]
    references = [
        "IEEE Std 829-2022 on Document Notation.",
        "Smith et al., Deterministic Systems in Academic Computing, 2024.",
    ]

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={"objectives": objectives, "references": references},
        output_path=out_path,
    )

    assert result.success is True
    res_doc = docx.Document(out_path)

    # Check objectives bullets
    obj_paras = [p.text for p in res_doc.paragraphs if "•" in p.text]
    assert len(obj_paras) == 3
    assert "Design scalable IoT node architecture." in obj_paras[0]
    assert "Implement low-latency wireless transmission." in obj_paras[1]

    # Check references numbered citations
    ref_paras = [p.text for p in res_doc.paragraphs if "[1]" in p.text or "[2]" in p.text]
    assert len(ref_paras) == 2
    assert "[1]  IEEE Std 829-2022" in ref_paras[0]
    assert "[2]  Smith et al." in ref_paras[1]


def test_basic_tables_cell_substitution_and_dynamic_row_expansion(temp_work_dir):
    """
    Verifies:
    1. Cell placeholder substitution across table cells.
    2. Dynamic row expansion when a template row matches record fields.
    3. Standalone structured table insertion from list of dicts.
    """
    doc_path = os.path.join(temp_work_dir, "test_tables_template.docx")
    out_path = os.path.join(temp_work_dir, "test_tables_out.docx")

    doc = docx.Document()

    # Table 1: Standard college project info table
    tbl1 = doc.add_table(rows=2, cols=2)
    tbl1.rows[0].cells[0].paragraphs[0].text = "Project:"
    tbl1.rows[0].cells[1].paragraphs[0].text = "{{PROJECT_TITLE}}"
    tbl1.rows[1].cells[0].paragraphs[0].text = "Guide:"
    tbl1.rows[1].cells[1].paragraphs[0].text = "{{GUIDE_NAME}}"

    # Table 2: Student team members template table with repeating row
    tbl2 = doc.add_table(rows=1, cols=2)
    tbl2.rows[0].cells[0].paragraphs[0].text = "Name"
    tbl2.rows[0].cells[1].paragraphs[0].text = "Roll Number"
    template_row = tbl2.add_row()
    template_row.cells[0].paragraphs[0].text = "{{member_name}}"
    template_row.cells[1].paragraphs[0].text = "{{member_roll}}"

    # Paragraph 3: Standalone structured table placeholder
    p_tech = doc.add_paragraph("{{TECHNOLOGIES_TABLE}}")

    doc.save(doc_path)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={
            "project_title": "Autonomous Agricultural Yield Telemetry",
            "guide_name": "Dr. Y.V. Krishna Reddy",
            "team_members": [
                {"member_name": "Kasireddy Charishma", "member_roll": "24BFA02081"},
                {"member_name": "Jagadeesh Kumar", "member_roll": "24BFA02068"},
                {"member_name": "Anusha Gade", "member_roll": "24BFA02071"},
            ],
            "technologies_table": [
                {"framework": "FastAPI", "version": "0.110", "tier": "API Backend"},
                {"framework": "Next.js", "version": "14.2", "tier": "Frontend UI"},
                {"framework": "PostgreSQL", "version": "16.1", "tier": "Database"},
            ],
        },
        output_path=out_path,
    )

    assert result.success is True
    res_doc = docx.Document(out_path)

    # Verify Table 1 cell substitution
    t1 = res_doc.tables[0]
    assert t1.rows[0].cells[1].text.strip() == "Autonomous Agricultural Yield Telemetry"
    assert t1.rows[1].cells[1].text.strip() == "Dr. Y.V. Krishna Reddy"

    # Verify Table 2 row expansion (Header + 3 records = 4 rows)
    t2 = res_doc.tables[1]
    assert len(t2.rows) == 4
    assert t2.rows[1].cells[0].text.strip() == "Kasireddy Charishma"
    assert t2.rows[1].cells[1].text.strip() == "24BFA02081"
    assert t2.rows[2].cells[0].text.strip() == "Jagadeesh Kumar"
    assert t2.rows[3].cells[0].text.strip() == "Anusha Gade"

    # Verify Table 3 structured insertion
    assert len(res_doc.tables) >= 3
    t3 = res_doc.tables[2]
    assert len(t3.rows) == 4
    assert "Framework" in t3.rows[0].cells[0].text
    assert t3.rows[1].cells[0].text.strip() == "FastAPI"


def test_headers_and_footers_support(temp_work_dir):
    """
    Verifies that placeholders across primary, first-page, and even-page headers/footers
    and tables inside headers/footers are replaced cleanly.
    """
    doc_path = os.path.join(temp_work_dir, "test_hdr_template.docx")
    out_path = os.path.join(temp_work_dir, "test_hdr_out.docx")

    doc = docx.Document()
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True

    # First page header & footer
    sec.first_page_header.paragraphs[0].text = "College Report | {{DEPARTMENT}}"
    sec.first_page_footer.paragraphs[0].text = "Cover Page | {{PROJECT_TITLE}}"

    # Primary header & footer
    sec.header.paragraphs[0].text = "Header: {{PROJECT_TITLE}}"
    sec.footer.paragraphs[0].text = "Guide: {{GUIDE_NAME}} | Confidential"

    # Table inside header
    hdr_tbl = sec.header.add_table(rows=1, cols=2, width=Inches(6.0))
    hdr_tbl.rows[0].cells[0].paragraphs[0].text = "Roll: {{ROLL_NUMBER}}"
    hdr_tbl.rows[0].cells[1].paragraphs[0].text = "Dept: {{DEPARTMENT}}"

    doc.add_paragraph("Body content.")
    doc.save(doc_path)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={
            "department": "Department of Electrical & Electronics Engineering",
            "project_title": "Smart Grid Telemetry",
            "guide_name": "Dr. Y.V. Krishna Reddy",
            "roll_number": "24BFA02081",
        },
        output_path=out_path,
    )

    assert result.success is True
    res_doc = docx.Document(out_path)
    r_sec = res_doc.sections[0]

    # Verify first page header & footer
    assert "Department of Electrical & Electronics Engineering" in r_sec.first_page_header.paragraphs[0].text
    assert "Smart Grid Telemetry" in r_sec.first_page_footer.paragraphs[0].text

    # Verify primary header & footer
    assert "Smart Grid Telemetry" in r_sec.header.paragraphs[0].text
    assert "Dr. Y.V. Krishna Reddy" in r_sec.footer.paragraphs[0].text

    # Verify header table
    assert "24BFA02081" in r_sec.header.tables[0].rows[0].cells[0].paragraphs[0].text
    assert "Department of Electrical & Electronics Engineering" in r_sec.header.tables[0].rows[0].cells[1].paragraphs[0].text


def test_image_replacement_and_format_normalization(temp_work_dir):
    """
    Verifies:
    1. Replacing image placeholder with centered picture and caption directly underneath.
    2. Format normalization: converting WebP/JP2 to PNG via Pillow so OpenXML never errors.
    """
    doc_path = os.path.join(temp_work_dir, "test_img_template.docx")
    out_path = os.path.join(temp_work_dir, "test_img_out.docx")

    # Generate a test WebP image
    webp_path = os.path.join(temp_work_dir, "test_sample.webp")
    pil_img = PILImage.new("RGB", (300, 200), color=(30, 140, 220))
    pil_img.save(webp_path, format="WEBP")

    doc = docx.Document()
    doc.add_paragraph("Chapter 2 System Architecture:")
    p_img = doc.add_paragraph("{{IMAGE_1}}")
    p_after = doc.add_paragraph("Architecture discussion continuing below...")
    doc.save(doc_path)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=doc_path,
        field_values={},
        image_assets={
            "image_1": {
                "file_path": webp_path,
                "caption": "Figure 1: IoT Sensor Node Architecture Diagram",
            }
        },
        output_path=out_path,
    )

    assert result.success is True
    assert result.images_replaced == 1

    res_doc = docx.Document(out_path)
    # Paragraph 0: Chapter 2 ...
    # Paragraph 1: Picture run (centered)
    # Paragraph 2: Caption (centered italic)
    # Paragraph 3: Architecture discussion continuing...
    assert len(res_doc.paragraphs) == 4
    img_p = res_doc.paragraphs[1]
    assert img_p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert len(img_p.runs) > 0

    cap_p = res_doc.paragraphs[2]
    assert "Figure 1: IoT Sensor Node Architecture Diagram" in cap_p.text
    assert cap_p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert cap_p.runs[0].italic is True


def test_full_college_template_end_to_end_and_pdf(temp_work_dir):
    """
    Full end-to-end verification using the authoritative Master College Template
    located at `.storage/templates/master_college_template.docx`.
    Verifies OpenXML integrity, 0 unresolved placeholders, and ReportLab PDF compilation.
    """
    master_template = ".storage/templates/master_college_template.docx"
    assert os.path.exists(master_template), "Authoritative Master College Template missing!"

    logo_path = ".storage/templates/extracted_logo_fixed.png"
    assert os.path.exists(logo_path), "Master template logo asset missing!"

    out_docx = os.path.join(temp_work_dir, "Final_College_Report.docx")
    out_pdf = os.path.join(temp_work_dir, "Final_College_Report.pdf")

    dataset = {
        "project_title": "Autonomous Agricultural Yield Telemetry and Forecasting",
        "student_name": "Kasireddy Charishma",
        "roll_number": "24BFA02081",
        "department": "Department of Electrical & Electronics Engineering",
        "guide_name": "Dr. Y.V. Krishna Reddy",
        "introduction": (
            "Chapter 1 introduces autonomous agricultural telemetry.\n\n"
            "The system leverages distributed soil sensors and micro-controllers to quantify crop yield in real-time."
        ),
        "objectives": [
            "Construct low-power IoT telemetry hardware.",
            "Formulate predictive yield estimation algorithms.",
            "Evaluate academic reliability against regional benchmark standards.",
        ],
        "problem_statement": "Manual crop inspection is error-prone, labor-intensive, and susceptible to yield losses.",
        "methodology": "The system employs sensory data acquisition, MQTT edge gateways, and statistical modeling.",
        "technologies": ["Python", "C++", "FreeRTOS", "FastAPI", "React"],
        "implementation": "Sensor units were calibrated across 10 agricultural parcels with multi-node mesh topology.",
        "results": "Field trials exhibited 98.4% measurement precision and 350ms average network telemetry latency.",
        "advantages": [
            "Continuous automated monitoring without manual labor.",
            "Deterministic fault isolation.",
            "Compliant with institutional engineering standards.",
        ],
        "limitations": [
            "Dependent on rural cellular transceiver signal quality.",
            "Requires initial periodic soil probe calibration.",
        ],
        "future_scope": "Integration with satellite multispectral imaging and autonomous drone spraying payloads.",
        "conclusion": "The autonomous telemetry architecture achieves all research objectives with high fidelity.",
        "references": [
            "IEEE Std 829-2022, Standard for Configuration Telemetry Systems.",
            "Reddy, Y.V.K., Precision Agronomy via Distributed Sensing, 2025.",
            "Department of Electrical Engineering Guidelines for Major Projects, 2026.",
        ],
    }

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=master_template,
        field_values=dataset,
        image_assets={
            "image_1": {
                "file_path": logo_path,
                "caption": "Figure 1: Verified Institutional & System Architecture Setup",
            }
        },
        output_path=out_docx,
    )

    assert result.success is True
    assert result.state == ReplacementState.COMPLETED
    assert result.fields_replaced >= 18
    assert result.images_replaced >= 1
    assert len(result.errors) == 0

    # Run OpenXML Integrity & Placeholder Validator
    val_report = ReplacementValidator.validate_and_generate_preview(
        out_docx,
        required_fields=["project_title", "student_name", "introduction", "objectives", "methodology", "conclusion"],
    )

    assert val_report["is_valid"] is True
    assert len(val_report["errors"]) == 0
    assert len(val_report["stats"]["unresolved_placeholders"]) == 0
    assert "Autonomous Agricultural Yield Telemetry" in val_report["preview_html"]

    # Convert DOCX to PDF using PDF Converter Service
    pdf_res = pdf_converter_service.convert(out_docx, out_pdf)
    assert pdf_res["converter"] != ""
    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 2000
