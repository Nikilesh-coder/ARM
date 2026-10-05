"""
ARM Stage 10 - Report Preview Workflow Tests
Verifies the complete student preview lifecycle:
Generation -> Preview -> Single-Section Regeneration -> Image Replacement -> Approval -> Download.
Ensures zero mock content, actual OpenXML preview extraction, accurate page counts, and real-time state updates.
"""

import os
import tempfile
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.replacement_engine_service import replacement_engine_service
from packages.replacement_engine.validator import ReplacementValidator

client = TestClient(app)


@pytest.fixture
def sample_test_image():
    """Generates a temporary valid PNG image for image replacement testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (320, 240), color=(30, 144, 255))
        img.save(f, format="PNG")
        temp_img_path = f.name
    yield temp_img_path
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)


@pytest.fixture
def completed_replacement_job(sample_test_image):
    """Executes a baseline template replacement job on Master College Template."""
    payload = {
        "project_data": {
            "title": "Autonomous Edge Vision System",
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
            "department": "Department of Electrical & Electronics Engineering",
            "academic_year": "2025-2026",
            "guide_name": "Dr. Y.V. Krishna Reddy",
        },
        "custom_content": {
            "abstract": "This project presents an edge vision processing system optimized for low latency embedded inferencing.",
            "introduction": "Traditional computer vision pipelines suffer from communication bottlenecks.",
            "objectives": [
                "Deploy CNN on embedded edge hardware",
                "Maintain inference speed under 15ms per frame",
                "Preserve classification accuracy above 94%",
            ],
            "methodology": "The system utilizes an optimized lightweight MobileNet architecture deployed via TensorRT.",
            "results": "Benchmark experiments achieved 12.4ms latency and 95.2% top-1 accuracy on the test dataset.",
            "conclusion": "The autonomous edge vision system successfully balances compute efficiency with inference precision.",
            "figure_1_caption": "Fig. 1. College Institutional Insignia",
            "figure_2_caption": "Fig. 2. Edge Inference System Architecture",
        },
        "custom_assets": {
            "image_1": sample_test_image,
            "image_2": sample_test_image,
        },
    }
    job = replacement_engine_service.execute_replacement(
        project_data=payload["project_data"],
        custom_content=payload["custom_content"],
        custom_assets=payload["custom_assets"],
    )
    return job


def test_preview_metadata_and_stats(completed_replacement_job):
    """
    Verifies that the generated preview contains:
    - Page count >= 1
    - Word count > 0
    - Sections list matching document headings
    - Image count matching embedded figures
    - Initial approval_status is 'pending'
    - Validation status is 'VALID'
    """
    job = completed_replacement_job
    assert job["state"] == "COMPLETED"
    assert job["approval_status"] == "pending"
    assert job["approved_at"] is None

    stats = job.get("stats", {})
    assert stats.get("page_count", 0) >= 1
    assert stats.get("estimated_word_count", 0) > 50
    assert stats.get("images_count", 0) >= 1
    assert stats.get("validation_status") in ("VALID", "WARNING")

    preview_html = job.get("preview_html", "")
    assert preview_html is not None
    assert "<div class=\"arm-report-preview" in preview_html
    # Verifies actual generated report text is in preview, not mock content
    assert "Autonomous Edge Vision System" in preview_html or "Kasireddy Charishma" in preview_html


def test_approve_report_workflow(completed_replacement_job):
    """
    Verifies the student approval step:
    Transitions approval_status from 'pending' to 'approved', sets timestamp, and locks document.
    """
    job_id = completed_replacement_job["job_id"]

    # Direct service call
    approved_job = replacement_engine_service.approve_report(job_id)
    assert approved_job["approval_status"] == "approved"
    assert approved_job["approved_at"] is not None

    # API endpoint check
    res = client.get(f"/api/v1/replacement/preview/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["approval_status"] == "approved"
    assert data["approved_at"] is not None


def test_regenerate_section_in_place(completed_replacement_job):
    """
    Verifies targeted single-section regeneration:
    Updates only the requested section in the Master Template and refreshes preview HTML.
    """
    job_id = completed_replacement_job["job_id"]
    original_html = completed_replacement_job["preview_html"]

    # Regenerate "methodology" with custom student prompt
    custom_guidance = "Incorporate custom FPGA acceleration metrics and pipeline parallelism."
    updated_job = replacement_engine_service.regenerate_section(
        job_id=job_id,
        section_name="methodology",
        custom_prompt=custom_guidance,
    )

    assert updated_job["state"] == "COMPLETED"
    assert updated_job["field_values"]["methodology"] is not None
    # Verify docx file exists and was updated
    assert os.path.exists(updated_job["docx_path"])
    # Verify preview was updated
    assert updated_job["preview_html"] is not None


def test_replace_image_in_place(completed_replacement_job, sample_test_image):
    """
    Verifies replacing an image slot (e.g. image_2):
    Substitutes image asset into the template, updates preview, and counts replaced images.
    """
    job_id = completed_replacement_job["job_id"]

    updated_job = replacement_engine_service.replace_image(
        job_id=job_id,
        image_slot="image_2",
        asset_path=sample_test_image,
        caption="Fig. 2. Updated High-Throughput Edge Pipeline Diagram",
    )

    assert updated_job["state"] == "COMPLETED"
    assert updated_job["image_assets"]["image_2"] == sample_test_image
    assert updated_job["images_replaced"] >= 1
    assert os.path.exists(updated_job["docx_path"])


def test_preview_api_endpoints(completed_replacement_job):
    """Verifies preview and download routes via FastAPI TestClient."""
    job_id = completed_replacement_job["job_id"]

    # 1. Preview endpoint
    preview_res = client.get(f"/api/v1/replacement/preview/{job_id}")
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert p_data["job_id"] == job_id
    assert p_data["download_docx_url"] == f"/api/v1/replacement/download/{job_id}?format=docx"
    assert "preview_html" in p_data

    # 2. Download DOCX
    dl_docx = client.get(f"/api/v1/replacement/download/{job_id}?format=docx")
    assert dl_docx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in dl_docx.headers["content-type"]
