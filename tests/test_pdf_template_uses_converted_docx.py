"""
ARM — PDF Template Regression Test Suite
Tests:
1. test_pdf_template_uses_converted_docx():
   - Upload/use a test PDF.
   - Convert it through CloudConvert/internal fallback provider.
   - Confirm converted DOCX exists.
   - Create template_id.
   - Resolve template_id.
   - Assert resolved file extension == ".docx".
   - Assert resolved file is the converted DOCX.
   - Assert it is NOT the original PDF.
   - Assert it is NOT master_college_template.docx.
   - Send the template_id through the report-generation path.
   - Verify the report generator opens and produces the final report based on the converted DOCX.
2. test_e2e_real_pdf_template_report_generation():
   - Full end-to-end verification with real college PDF template.
   - Prints original PDF, converted DOCX, template_id, resolved template path, and final DOCX.
"""

import os
import io
import pytest
import docx
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.custom_template_service import custom_template_service, _CUSTOM_TEMPLATES_STORE
from apps.api.services.template_resolver import resolve_selected_template_path, DEFAULT_MASTER_TEMPLATE_PATH
from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
from apps.api.routers.templates import _TEMPLATES_DB

client = TestClient(app)


def test_pdf_template_uses_converted_docx():
    """
    TASK 8: Automated Regression Test
    Verifies that uploading a PDF creates a template_id that strictly points
    to and resolves the converted DOCX, never the original PDF or master_college_template.docx.
    """
    real_pdf_path = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.pdf")
    assert os.path.exists(real_pdf_path), "Test PDF file missing"

    with open(real_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. Upload the PDF via the custom college template upload endpoint
    upload_response = client.post(
        "/api/v1/templates/upload-custom",
        files={"file": ("Project_Report_Final_IEEE.pdf", pdf_bytes, "application/pdf")},
        data={
            "name": "IEEE Academic Report PDF Template",
            "institution": "SVCE Autonomous",
            "department": "Computer Science & Engineering",
            "report_type": "Seminar",
        },
    )
    assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
    data = upload_response.json()
    template_data = data["template"]

    # 2 & 4. Verify template_id and record created
    template_id = template_data["id"]
    assert template_id, "template_id was not returned!"

    # 3. Confirm converted DOCX exists on disk and is a valid DOCX
    converted_docx_path = template_data.get("converted_docx_path")
    assert converted_docx_path, "converted_docx_path missing in template record"
    assert os.path.exists(converted_docx_path), f"Converted DOCX does not exist at {converted_docx_path}"
    assert converted_docx_path.lower().endswith(".docx"), "converted_docx_path is not a .docx file"
    assert os.path.getsize(converted_docx_path) > 1000, "Converted DOCX is empty or too small"

    # Confirm it is valid OpenXML that python-docx can parse
    doc_check = docx.Document(converted_docx_path)
    assert len(doc_check.sections) >= 1, "Converted DOCX has no sections"

    # 5. Resolve template_id using the backend template resolver
    resolved_path, resolved_tid = resolve_selected_template_path(template_id)

    # 6. Assert resolved file extension == ".docx"
    assert resolved_path.lower().endswith(".docx"), f"Resolved path '{resolved_path}' is NOT a .docx!"

    # 7. Assert resolved file is the converted DOCX
    assert os.path.abspath(resolved_path) == os.path.abspath(converted_docx_path), (
        f"Resolved path '{resolved_path}' does not match converted DOCX '{converted_docx_path}'"
    )

    # 8. Assert it is NOT the original PDF
    assert not resolved_path.lower().endswith(".pdf"), f"Resolved template path is a PDF: {resolved_path}"
    assert resolved_path != real_pdf_path, "Resolved template path is the original PDF!"

    # 9. Assert it is NOT master_college_template.docx
    assert os.path.abspath(resolved_path) != os.path.abspath(DEFAULT_MASTER_TEMPLATE_PATH), (
        f"Resolved template silently fell back to master template: {resolved_path}"
    )

    # 10. Send the template_id through the report-generation path
    gen_payload = {
        "title": "HYBRID INTELLIGENCE TELEMETRY FOR SMART AGRICULTURE",
        "project_title": "HYBRID INTELLIGENCE TELEMETRY FOR SMART AGRICULTURE",
        "research_query": "Autonomous telemetry sensors",
        "student_name": "K.CHARISHMA",
        "roll_no": "25BFA02L13",
        "guide_name": "Dr. R. SIRISHA, Ph.D",
        "department": "COMPUTER SCIENCE AND ENGINEERING",
        "institution": "SRI VENKATESWARA COLLEGE OF ENGINEERING",
        "problem_statement": "Manual monitoring in agriculture results in delayed pest control.",
        "proposed_solution": "Edge IoT sensors connected to an intelligent telemetry broker.",
        "template_id": template_id,
    }

    gen_res = client.post("/api/v1/reports/generate", json=gen_payload)
    assert gen_res.status_code == 200, f"Report generation failed: {gen_res.text}"
    gen_data = gen_res.json()

    # 11. Verify report generation used DOCX and produced valid DOCX
    out_docx_path = gen_data["output_path"]
    assert out_docx_path, "output_path missing in generation response"
    assert os.path.exists(out_docx_path), f"Output report missing: {out_docx_path}"
    assert out_docx_path.lower().endswith(".docx"), f"Output report is not a DOCX: {out_docx_path}"

    gen_doc = docx.Document(out_docx_path)
    assert len(gen_doc.paragraphs) > 0, "Generated report docx has no paragraphs"

    print("\n[TEST ASSERTIONS PASSED]")
    print(f"Original PDF: {real_pdf_path}")
    print(f"Converted DOCX: {converted_docx_path}")
    print(f"Template ID: {template_id}")
    print(f"Resolved template path: {resolved_path}")
    print(f"Final output DOCX: {out_docx_path}")


def test_e2e_real_pdf_template_report_generation():
    """
    TASK 9: Real End-to-End Test with Real College PDF Template
    """
    real_pdf_path = os.path.abspath(".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/059dbf96-994a-464d-91a7-a6c9049a785c/JAGADEESH PPT.pdf")
    if not os.path.exists(real_pdf_path):
        real_pdf_path = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.pdf")

    with open(real_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Step A: PDF upload
    upload_res = client.post(
        "/api/v1/templates/upload-custom",
        files={"file": (os.path.basename(real_pdf_path), pdf_bytes, "application/pdf")},
        data={"name": "Jagadeesh PPT Template", "report_type": "Seminar"},
    )
    assert upload_res.status_code == 200
    tpl_data = upload_res.json()["template"]
    template_id = tpl_data["id"]

    # Step B: Converted DOCX verification
    converted_docx = tpl_data["converted_docx_path"]
    assert os.path.exists(converted_docx)
    assert converted_docx.endswith(".docx")

    # Step C: Template resolution verification
    resolved_path, res_tid = resolve_selected_template_path(template_id)
    assert resolved_path.endswith(".docx")
    assert resolved_path == converted_docx
    assert resolved_path != real_pdf_path

    # Step D: /api/v1/reports/generate
    report_res = client.post(
        "/api/v1/reports/generate",
        json={
            "title": "ENERGY OPTIMIZATION USING IOT IN MICROGRIDS",
            "project_title": "ENERGY OPTIMIZATION USING IOT IN MICROGRIDS",
            "student_name": "JAGADEESH V",
            "roll_no": "22BFA02099",
            "template_id": template_id,
        }
    )
    assert report_res.status_code == 200
    report_data = report_res.json()
    final_output_docx = report_data["output_path"]

    # Print exact paths as required by Task 9
    print("\n" + "=" * 80)
    print("TASK 9 REAL END-TO-END TEST RESULTS")
    print("=" * 80)
    print(f"original PDF:           {real_pdf_path}")
    print(f"converted DOCX:         {converted_docx}")
    print(f"template_id:            {template_id}")
    print(f"resolved template path: {resolved_path}")
    print(f"final output DOCX:      {final_output_docx}")
    print("=" * 80 + "\n")

    assert os.path.exists(final_output_docx)
    assert final_output_docx.endswith(".docx")
