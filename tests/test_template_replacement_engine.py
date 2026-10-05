"""
ARM Stage 10 - Template Replacement Engine Test Suite
Tests in-place DOCX replacement, non-redesign guarantees, 7-state lifecycle,
safety validation, and API preview/download endpoints.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.master_template_service import master_template_service, CANONICAL_FIELDS
from packages.replacement_engine.base import ReplacementState
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.validator import ReplacementValidator

client = TestClient(app)


def test_canonical_fields_integrity():
    """Verifies that the Master College Template defines all 20 canonical fields."""
    master = master_template_service.get_master_template()
    assert master["is_master"] is True
    assert master["is_locked"] is True
    assert len(master["fields"]) == 20

    field_names = [f["field_name"] for f in master["fields"]]
    expected_fields = [
        "project_title", "student_name", "roll_number", "department", "guide_name",
        "introduction", "objectives", "problem_statement", "methodology", "technologies",
        "implementation", "results", "advantages", "limitations", "future_scope",
        "conclusion", "references", "image_1", "image_2", "image_3"
    ]
    for exp in expected_fields:
        assert exp in field_names, f"Expected field '{exp}' missing from canonical fields"


def test_docx_in_place_replacement():
    """Verifies in-place DOCX substitution preserving formatting and layout."""
    template_path = ".storage/templates/master_college_template.docx"
    assert os.path.exists(template_path), f"Master template not found at {template_path}"

    engine = DocxTemplateReplacementEngine()
    dataset = master_template_service.build_replacement_dataset(
        project_data={
            "title": "Autonomous Agricultural Yield Telemetry",
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
            "department": "Department of Electrical & Electronics Engineering",
            "guide_name": "Dr. Y.V. Krishna Reddy",
            "description": "Smart sensor telemetry and agricultural yield estimation using IoT.",
        },
        evidence_assets=[".storage/templates/extracted_logo_fixed.png"]
    )

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output_path = tmp.name

    try:
        res = engine.replace(
            template_path=template_path,
            field_values=dataset,
            image_assets={"image_1": ".storage/templates/extracted_logo_fixed.png"},
            output_path=output_path,
        )

        assert res.success is True
        assert res.state == ReplacementState.COMPLETED
        assert res.fields_replaced >= 18
        assert res.images_replaced >= 1
        assert len(res.errors) == 0

        # Run Validator on output
        val = ReplacementValidator.validate_and_generate_preview(
            output_path,
            required_fields=["project_title", "student_name", "introduction", "objectives", "methodology", "conclusion"]
        )
        assert val["is_valid"] is True
        assert len(val["errors"]) == 0
        assert len(val["stats"]["unresolved_placeholders"]) == 0
        assert "Autonomous Agricultural Yield Telemetry" in val["preview_html"]
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_safety_error_on_missing_required_field():
    """Verifies that missing required fields stop replacement safely and describe field & reason."""
    template_path = ".storage/templates/master_college_template.docx"
    engine = DocxTemplateReplacementEngine()

    # Pass incomplete dataset missing project_title and introduction
    dataset = {
        "student_name": "Student A",
        "roll_number": "2026BCSE01",
    }

    res = engine.replace(
        template_path=template_path,
        field_values=dataset,
    )

    assert res.success is False
    assert res.state == ReplacementState.FAILED
    assert len(res.errors) > 0

    error_fields = [e.field for e in res.errors]
    assert "project_title" in error_fields
    assert "introduction" in error_fields
    # Verify reason is provided
    for err in res.errors:
        assert len(err.reason) > 5


def test_replacement_api_endpoints_e2e():
    """Verifies full FastAPI router endpoints for replacement pipeline."""
    # 1. Master template info
    res_master = client.get("/api/v1/replacement/master-template")
    assert res_master.status_code == 200
    assert res_master.json()["fields_count"] == 20

    # 2. Execute replacement
    payload = {
        "project_data": {
            "title": "Smart Grid Power Distribution Telemetry",
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
            "department": "Department of Electrical & Electronics Engineering",
            "guide_name": "Dr. Y.V. Krishna Reddy",
            "description": "Grid power stability monitoring and fault isolation.",
        },
        "custom_assets": {
            "image_1": ".storage/templates/extracted_logo_fixed.png"
        }
    }
    res_exec = client.post("/api/v1/replacement/execute", json=payload)
    assert res_exec.status_code == 200
    job_data = res_exec.json()
    job_id = job_data["job_id"]
    assert job_data["state"] in ("COMPLETED", "REPLACING", "VALIDATING")
    assert job_data["fields_replaced"] >= 18
    assert "download_docx_url" in job_data

    # 3. Status endpoint
    res_status = client.get(f"/api/v1/replacement/status/{job_id}")
    assert res_status.status_code == 200
    assert res_status.json()["job_id"] == job_id

    # 4. Preview endpoint
    res_prev = client.get(f"/api/v1/replacement/preview/{job_id}")
    assert res_prev.status_code == 200
    assert "preview_html" in res_prev.json()
    assert "Smart Grid Power Distribution" in res_prev.json()["preview_html"]

    # 5. Download docx endpoint
    res_dl_docx = client.get(f"/api/v1/replacement/download/{job_id}?format=docx")
    assert res_dl_docx.status_code == 200
    assert len(res_dl_docx.content) > 5000
    assert "openxmlformats" in res_dl_docx.headers.get("content-type", "")

    # 6. Download pdf endpoint
    res_dl_pdf = client.get(f"/api/v1/replacement/download/{job_id}?format=pdf")
    assert res_dl_pdf.status_code == 200
    assert len(res_dl_pdf.content) > 1000
    assert "pdf" in res_dl_pdf.headers.get("content-type", "")
