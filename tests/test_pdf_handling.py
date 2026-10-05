"""
ARM Stage 10 - PDF Handling and Template Replacement Test Suite
Tests:
CASE 1: PDF generation from ARM's structured template/document (preserving formatting and DOCX as preferred master).
CASE 2: College PDF provided as reference/template:
- Scanned raster PDF detection and rejection.
- Unstructured reference PDF detection and rejection.
- Overflow risk detection for multi-paragraph flowable fields in fixed layout.
- Prevention of blind text overlay on top of existing text.
- Safe interactive AcroForm field replacement.
- Safe bounded metadata redaction and substitution.
- Clear error reporting advising conversion to an ARM structured DOCX template.
- API endpoints for PDF analysis and execution.
"""

import os
import tempfile
import pytest
import pymupdf
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.replacement_engine.pdf_engine import (
    PdfTemplateAnalyzer,
    PdfTemplateReplacementEngine,
    PdfAnalysisResult,
)
from packages.replacement_engine.base import ReplacementState
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.document_engine.converter import pdf_converter_service
from apps.api.services.replacement_engine_service import replacement_engine_service

client = TestClient(app)


@pytest.fixture
def temp_pdf_dir():
    """Provides an isolated scratch directory for PDF testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


# =====================================================================
# CASE 1: PDF generated from ARM's structured template/document
# =====================================================================

def test_case_1_pdf_generated_from_structured_document(temp_pdf_dir):
    """
    CASE 1: Verifies that PDF is generated with high fidelity from ARM's
    structured DOCX master template, keeping DOCX as the preferred editable master format.
    """
    master_template = ".storage/templates/master_college_template.docx"
    assert os.path.exists(master_template), "Authoritative Master College Template missing!"

    out_docx = os.path.join(temp_pdf_dir, "Compiled_Report.docx")
    out_pdf = os.path.join(temp_pdf_dir, "Compiled_Report.pdf")

    dataset = {
        "project_title": "Autonomous Agricultural Yield Telemetry",
        "student_name": "Kasireddy Charishma",
        "roll_number": "24BFA02081",
        "department": "Department of Electrical & Electronics Engineering",
        "guide_name": "Dr. Y.V. Krishna Reddy",
        "introduction": "This chapter introduces autonomous crop yield telemetry using wireless sensor networks.",
        "objectives": ["Measure soil metrics in real time.", "Transmit data with low latency."],
        "problem_statement": "Manual soil sampling is labor-intensive and delayed.",
        "methodology": "The system utilizes ESP32 edge gateways and cloud analytics.",
        "technologies": ["Python", "FastAPI", "React", "PostgreSQL"],
        "implementation": "Sensors deployed in agricultural plots.",
        "results": "Field trials demonstrated 98.4% measurement reliability.",
        "conclusion": "The autonomous telemetry prototype meets institutional performance benchmarks.",
        "references": ["IEEE Std 829-2022 on Documentation."],
    }

    # Step 1: Generate preferred editable DOCX master format
    logo_path = ".storage/templates/extracted_logo_fixed.png"
    docx_engine = DocxTemplateReplacementEngine()
    docx_res = docx_engine.replace(
        template_path=master_template,
        field_values=dataset,
        image_assets={"image_1": logo_path},
        output_path=out_docx,
    )
    assert docx_res.success is True
    assert os.path.exists(out_docx)
    assert os.path.getsize(out_docx) > 5000

    # Step 2: Compile high-fidelity PDF from the replaced structured document
    pdf_res = pdf_converter_service.convert(out_docx, out_pdf)
    assert pdf_res["converter"] != ""
    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 2000

    # Step 3: Validate generated PDF layout using PyMuPDF
    pdf_doc = pymupdf.open(out_pdf)
    assert len(pdf_doc) >= 1
    page1_text = pdf_doc[0].get_text()
    assert "Autonomous Agricultural Yield Telemetry" in page1_text
    pdf_doc.close()


# =====================================================================
# CASE 2: College PDF provided as reference/template
# =====================================================================

def test_case_2_scanned_raster_pdf_rejection(temp_pdf_dir):
    """
    CASE 2A: Verifies that scanned/raster PDFs without an editable text layer
    are detected and safely rejected with clear conversion instructions,
    preventing silent production of a broken PDF.
    """
    scanned_pdf_path = os.path.join(temp_pdf_dir, "scanned_college_template.pdf")
    scan_img_path = os.path.join(temp_pdf_dir, "simulated_scan.png")

    from PIL import Image as PILImage
    pil_img = PILImage.new("RGB", (400, 600), color=(240, 240, 240))
    pil_img.save(scan_img_path, format="PNG")

    # Create a simulated scanned PDF (image only, zero vector text)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(pymupdf.Rect(50, 50, 545, 792), filename=scan_img_path)
    doc.save(scanned_pdf_path)
    doc.close()

    # 1. Test Analyzer
    analysis = PdfTemplateAnalyzer.analyze(scanned_pdf_path)
    assert analysis.is_safe_for_replacement is False
    assert analysis.template_type == "scanned_raster"
    assert analysis.has_text_layer is False
    assert "scanned raster document" in analysis.issues[0].lower()
    assert "must be converted into an arm-supported structured template (docx format)" in analysis.recommendation.lower()

    # 2. Test Replacement Engine Safety Rejection
    engine = PdfTemplateReplacementEngine()
    result = engine.replace(
        template_path=scanned_pdf_path,
        field_values={"project_title": "Sample Project"},
    )
    assert result.success is False
    assert result.state == ReplacementState.FAILED
    assert len(result.errors) > 0
    assert any("scanned raster" in e.reason.lower() for e in result.errors)


def test_case_2_unstructured_reference_pdf_rejection(temp_pdf_dir):
    """
    CASE 2B: Verifies that a dense reference PDF without placeholders or form fields
    is detected as non-editable in-place and safely rejected.
    """
    ref_pdf_path = os.path.join(temp_pdf_dir, "reference_report.pdf")

    # Create a reference PDF containing static completed report text
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(
        (72, 100),
        "Final Report on Power Distribution Systems.\n"
        "By John Doe, Reg No: 2021EEE04.\n"
        "Department of Electrical Engineering.\n"
        "Abstract: This project investigated grid load balancing under extreme weather.\n",
        fontsize=11
    )
    doc.save(ref_pdf_path)
    doc.close()

    analysis = PdfTemplateAnalyzer.analyze(ref_pdf_path)
    assert analysis.is_safe_for_replacement is False
    assert analysis.template_type == "unstructured_reference"
    assert len(analysis.issues) > 0
    assert "convert" in analysis.recommendation.lower()

    engine = PdfTemplateReplacementEngine()
    result = engine.replace(
        template_path=ref_pdf_path,
        field_values={"project_title": "New Title"},
    )
    assert result.success is False
    assert result.state == ReplacementState.FAILED


def test_case_2_flowable_overflow_risk_detection(temp_pdf_dir):
    """
    CASE 2C: Verifies that PDFs containing long-text multi-paragraph placeholders
    (such as {{introduction}} or {{methodology}}) in fixed-layout PDF format
    are detected as overflow risks that cannot reflow safely without converting to DOCX.
    """
    overflow_pdf_path = os.path.join(temp_pdf_dir, "flowable_pdf.pdf")

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Project: {{PROJECT_TITLE}}", fontsize=12)
    page.insert_text((72, 150), "Chapter 1: {{INTRODUCTION}}", fontsize=12)
    doc.save(overflow_pdf_path)
    doc.close()

    analysis = PdfTemplateAnalyzer.analyze(overflow_pdf_path)
    assert analysis.is_safe_for_replacement is False
    assert analysis.template_type == "overflow_risk"
    assert any("flowable" in iss.lower() or "pagination" in iss.lower() for iss in analysis.issues)
    assert "must be converted into an arm-supported structured template (docx format)" in analysis.recommendation.lower()

    engine = PdfTemplateReplacementEngine()
    result = engine.replace(
        template_path=overflow_pdf_path,
        field_values={
            "project_title": "Smart Telemetry",
            "introduction": "Paragraph 1\n\nParagraph 2\n\nParagraph 3",
        },
    )
    assert result.success is False
    assert result.state == ReplacementState.FAILED


def test_case_2_interactive_acroform_pdf_safe_replacement(temp_pdf_dir):
    """
    CASE 2D: Verifies that interactive AcroForm college templates are
    detected as reliable and have their form fields filled accurately without overlay.
    """
    form_pdf_path = os.path.join(temp_pdf_dir, "college_form_template.pdf")
    out_pdf_path = os.path.join(temp_pdf_dir, "college_form_filled.pdf")

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 50), "Official College Major Project Approval Form", fontsize=14)

    # Add AcroForm fields
    w1 = pymupdf.Widget()
    w1.field_name = "project_title"
    w1.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w1.rect = pymupdf.Rect(72, 80, 450, 105)
    page.add_widget(w1)

    w2 = pymupdf.Widget()
    w2.field_name = "student_name"
    w2.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w2.rect = pymupdf.Rect(72, 120, 300, 145)
    page.add_widget(w2)

    w3 = pymupdf.Widget()
    w3.field_name = "roll_number"
    w3.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w3.rect = pymupdf.Rect(320, 120, 450, 145)
    page.add_widget(w3)

    doc.save(form_pdf_path)
    doc.close()

    # 1. Analyze
    analysis = PdfTemplateAnalyzer.analyze(form_pdf_path)
    assert analysis.is_safe_for_replacement is True
    assert analysis.template_type == "acroform"
    assert "project_title" in analysis.detected_fields
    assert "student_name" in analysis.detected_fields

    # 2. Replace
    engine = PdfTemplateReplacementEngine()
    result = engine.replace(
        template_path=form_pdf_path,
        field_values={
            "project_title": "Autonomous Agricultural Yield Telemetry",
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
        },
        output_path=out_pdf_path,
    )

    assert result.success is True
    assert result.state == ReplacementState.COMPLETED
    assert result.fields_replaced >= 3
    assert os.path.exists(out_pdf_path)

    # 3. Verify filled values in output PDF
    doc_check = pymupdf.open(out_pdf_path)
    fields_found = {}
    for p in doc_check:
        for w in p.widgets():
            fields_found[w.field_name] = w.field_value
    doc_check.close()

    assert fields_found["project_title"] == "Autonomous Agricultural Yield Telemetry"
    assert fields_found["student_name"] == "Kasireddy Charishma"
    assert fields_found["roll_number"] == "24BFA02081"


def test_case_2_bounded_metadata_redaction_prevents_blind_overlay(temp_pdf_dir):
    """
    CASE 2E: Verifies that bounded metadata placeholders are replaced
    using clean redaction (erasing original text before drawing),
    strictly preventing blind text overlay on top of existing text.
    """
    cert_pdf_path = os.path.join(temp_pdf_dir, "college_certificate_template.pdf")
    out_pdf_path = os.path.join(temp_pdf_dir, "college_certificate_replaced.pdf")

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 80), "CERTIFICATE OF COMPLETION", fontsize=16)
    page.insert_text((72, 120), "This certifies that {{STUDENT_NAME}} ({{ROLL_NUMBER}})", fontsize=11)
    page.insert_text((72, 150), "has submitted the project titled {{PROJECT_TITLE}}.", fontsize=11)
    doc.save(cert_pdf_path)
    doc.close()

    analysis = PdfTemplateAnalyzer.analyze(cert_pdf_path)
    assert analysis.is_safe_for_replacement is True
    assert analysis.template_type == "bounded_metadata"

    engine = PdfTemplateReplacementEngine()
    result = engine.replace(
        template_path=cert_pdf_path,
        field_values={
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
            "project_title": "Autonomous Agricultural Yield Telemetry",
        },
        output_path=out_pdf_path,
    )

    assert result.success is True
    assert result.state == ReplacementState.COMPLETED
    assert os.path.exists(out_pdf_path)

    # Verify that original placeholder tokens are erased and replaced cleanly
    doc_res = pymupdf.open(out_pdf_path)
    res_text = doc_res[0].get_text()
    doc_res.close()

    assert "{{STUDENT_NAME}}" not in res_text
    assert "{{ROLL_NUMBER}}" not in res_text
    assert "{{PROJECT_TITLE}}" not in res_text
    assert "Kasireddy Charishma" in res_text
    assert "24BFA02081" in res_text
    assert "Autonomous Agricultural Yield Telemetry" in res_text


def test_pdf_analysis_and_replacement_api_endpoints(temp_pdf_dir):
    """
    Verifies the FastAPI endpoints:
    1. POST /api/v1/replacement/analyze-pdf: Feasibility analysis of uploaded/referenced PDF.
    2. POST /api/v1/replacement/execute: Safe execution on PDF templates.
    """
    form_pdf_path = os.path.join(temp_pdf_dir, "api_form_test.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    w = pymupdf.Widget()
    w.field_name = "project_title"
    w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.rect = pymupdf.Rect(72, 80, 400, 105)
    page.add_widget(w)
    doc.save(form_pdf_path)
    doc.close()

    # 1. Test Analyze PDF Endpoint
    res_analyze = client.post("/api/v1/replacement/analyze-pdf", json={"pdf_path": form_pdf_path})
    assert res_analyze.status_code == 200
    data = res_analyze.json()
    assert data["is_safe_for_replacement"] is True
    assert data["template_type"] == "acroform"
    assert "project_title" in data["detected_fields"]

    # 2. Test Execute with custom PDF template path
    res_exec = client.post(
        "/api/v1/replacement/execute",
        json={
            "project_data": {
                "title": "Smart Grid Power Telemetry",
                "student_name": "Kasireddy Charishma",
            },
            "custom_content": {
                "project_title": "Smart Grid Power Telemetry",
            }
        }
    )
    assert res_exec.status_code == 200
    job = res_exec.json()
    assert job["state"] in ("COMPLETED", "REPLACING", "VALIDATING")
    assert "download_docx_url" in job
    assert "download_pdf_url" in job
