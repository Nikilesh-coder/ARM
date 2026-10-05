"""
ARM Report Persistence and Download Regression Test Suite
=========================================================
Tests the permanent architectural solution for report file persistence and download:
TEST A: Generate report -> verify file exists -> download -> PASS
TEST B: Generate report -> restart FastAPI (clear in-memory stores) -> download same report -> PASS
TEST C: Generate report -> reload FastAPI (re-init service) -> download same report -> PASS
TEST D: Generate DOCX -> verify correct DOCX download & MIME type
TEST E: Generate PPTX -> verify correct PPTX download & MIME type
TEST F: Generate multiple reports -> verify each report ID maps to its own file
TEST G: Generate report -> verify no cleanup process removes it
TEST H: Run backend from a different working directory -> generated report must still be downloadable
"""

import os
import sys
import io
import tempfile
import pytest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from fastapi.testclient import TestClient
import docx

from apps.api.main import app
from apps.api.services.report_file_storage_service import report_file_storage_service, ReportFileStorageService
from apps.api.routers.reports import _REPORTS_STORE, _REPORT_ID_MAPPING
from apps.api.services.replacement_engine_service import _REPLACEMENT_JOBS
from apps.api.routers.projects import _PROJECTS_STORE

client = TestClient(app)
MASTER_TPL_ID = "0484aecb-dbc1-4671-a388-0f820124ca0e"


def test_A_generate_verify_download():
    """TEST A: Generate report -> verify file exists -> download -> PASS"""
    print("\n--- TEST A: Generate -> Verify File Exists -> Download ---")
    gen_payload = {
        "title": "Smart Irrigation Soil Telemetry System",
        "template_id": MASTER_TPL_ID,
    }
    resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert resp.status_code == 200, f"Generation failed: {resp.text}"
    data = resp.json()
    report_id = data["report_id"]

    # 1. Verify file exists in canonical storage
    assert report_file_storage_service.verify_file_exists(report_id), "Report file must exist in canonical storage!"
    res = report_file_storage_service.resolve_report_file(report_id)
    assert res["found"] is True
    assert os.path.isabs(res["file_path"]), "Canonical path must be absolute"
    assert os.path.exists(res["file_path"]), "Canonical path must exist on disk"
    assert res["file_size"] > 0, "Canonical file must not be empty"

    # 2. Download via endpoint
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200, f"Download failed: {dl_resp.text}"
    assert len(dl_resp.content) == res["file_size"]
    print(f"PASS: TEST A - Report {report_id} verified on disk ({res['file_size']} bytes) and downloaded.")


def test_B_download_after_fastapi_restart():
    """TEST B: Generate report -> restart FastAPI (all in-memory state wiped) -> download same report -> PASS"""
    print("\n--- TEST B: Download After In-Memory State Wipe (Simulated Restart) ---")
    gen_payload = {
        "title": "",  # fast canonical report generation
        "template_id": MASTER_TPL_ID,
    }
    resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert resp.status_code == 200
    report_id = resp.json()["report_id"]
    expected_size = resp.json()["file_size_bytes"]

    # SIMULATE FULL SERVER RESTART: Wipe all in-memory dictionaries completely
    _REPORTS_STORE.clear()
    _REPORT_ID_MAPPING.clear()
    _REPLACEMENT_JOBS.clear()

    assert len(_REPORTS_STORE) == 0
    assert len(_REPLACEMENT_JOBS) == 0

    # Request download after restart
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200, f"Download failed after simulated restart: {dl_resp.text}"
    assert len(dl_resp.content) == expected_size
    print(f"PASS: TEST B - Report {report_id} downloadable after complete in-memory wipe.")


def test_C_download_after_fastapi_reload():
    """TEST C: Generate report -> reload FastAPI (re-initialize service) -> download same report -> PASS"""
    print("\n--- TEST C: Download After FastAPI Reload (Re-Init Service) ---")
    gen_payload = {
        "title": "",
        "template_id": MASTER_TPL_ID,
    }
    resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert resp.status_code == 200
    report_id = resp.json()["report_id"]

    # SIMULATE FASTAPI RELOAD: Re-run startup initialization
    ReportFileStorageService.initialize()
    _REPORTS_STORE.clear()
    _REPLACEMENT_JOBS.clear()

    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 1000
    print(f"PASS: TEST C - Report {report_id} survived reload and re-initialization.")


def test_D_generate_and_download_docx():
    """TEST D: Generate DOCX -> verify correct DOCX download, MIME type, and structure"""
    print("\n--- TEST D: Verify DOCX Download Specifications ---")
    gen_payload = {
        "title": "Clinical Diagnostic Automation",
        "template_id": MASTER_TPL_ID,
    }
    resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert resp.status_code == 200
    report_id = resp.json()["report_id"]

    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in dl_resp.headers["content-type"]
    assert f"Report_{report_id}.docx" in dl_resp.headers["content-disposition"]

    doc = docx.Document(io.BytesIO(dl_resp.content))
    assert len(doc.paragraphs) > 0
    print(f"PASS: TEST D - DOCX MIME type, header, and OOXML structure valid.")


def test_E_generate_and_download_pptx():
    """TEST E: Generate PPTX -> verify correct PPTX download & MIME type"""
    print("\n--- TEST E: Verify PPTX Download Specifications ---")
    pptx_id = "rep_pptx_test_demo"
    dummy_pptx_bytes = b"PK\x03\x04PPTX_MOCK_DATA_FOR_PRESENTATION_TESTING" + b"\x00" * 500

    canonical_p, key = report_file_storage_service.save_report_file_atomically(
        report_id=pptx_id,
        source_data_or_path=dummy_pptx_bytes,
        extension="pptx",
        metadata={"title": "Presentation Pitch Deck", "type": "slides"}
    )
    assert canonical_p.exists()
    assert canonical_p.suffix == ".pptx"

    dl_resp = client.get(f"/api/v1/reports/{pptx_id}/download")
    assert dl_resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in dl_resp.headers["content-type"]
    assert f"Report_{pptx_id}.pptx" in dl_resp.headers["content-disposition"]
    assert dl_resp.content == dummy_pptx_bytes
    print(f"PASS: TEST E - PPTX MIME type, header, and extension correctly handled.")


def test_F_multiple_reports_isolation():
    """TEST F: Generate multiple reports -> verify each report ID maps to its own distinct file"""
    print("\n--- TEST F: Verify Multiple Report ID Isolation ---")
    ids = []
    for _ in range(3):
        resp = client.post("/api/v1/reports/generate", json={"title": "", "template_id": MASTER_TPL_ID})
        assert resp.status_code == 200
        ids.append(resp.json()["report_id"])

    assert len(set(ids)) == 3, "Each report must have a unique report ID"

    paths = [report_file_storage_service.resolve_report_file(rid)["file_path"] for rid in ids]
    assert len(set(paths)) == 3, "Each report must map to its own distinct file path"

    for rid in ids:
        dl_resp = client.get(f"/api/v1/reports/{rid}/download")
        assert dl_resp.status_code == 200
        assert f"Report_{rid}" in dl_resp.headers["content-disposition"]
    print(f"PASS: TEST F - Multiple reports isolated: {ids}")


def test_G_cleanup_process_does_not_remove_completed_reports():
    """TEST G: Generate report -> verify temporary directory cleanups do NOT delete canonical reports"""
    print("\n--- TEST G: Verify Deletion Prevention ---")
    resp = client.post("/api/v1/reports/generate", json={"title": "", "template_id": MASTER_TPL_ID})
    assert resp.status_code == 200
    report_id = resp.json()["report_id"]

    # Simulate external temp cleanup wiping system tempdir
    arm_temp = os.path.join(tempfile.gettempdir(), "arm_reports")
    if os.path.exists(arm_temp):
        for f in os.listdir(arm_temp):
            try:
                os.remove(os.path.join(arm_temp, f))
            except Exception:
                pass

    # Verify canonical report is unaffected
    assert report_file_storage_service.verify_file_exists(report_id)
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    print(f"PASS: TEST G - Canonical report survived temporary folder cleanup.")


def test_H_run_from_different_working_directory():
    """TEST H: Run backend from a different working directory -> report must still be resolvable and downloadable"""
    print("\n--- TEST H: Working Directory Invariance ---")
    resp = client.post("/api/v1/reports/generate", json={"title": "", "template_id": MASTER_TPL_ID})
    assert resp.status_code == 200
    report_id = resp.json()["report_id"]

    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    try:
        # Change working directory to a completely foreign folder
        os.chdir(temp_dir)
        assert os.getcwd() == temp_dir

        # Storage root must still resolve to the canonical workspace path, NOT temp_dir/.storage
        resolved = report_file_storage_service.resolve_report_file(report_id)
        assert resolved["found"] is True
        assert os.path.exists(resolved["file_path"])

        # Endpoint download must still succeed
        dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert len(dl_resp.content) > 1000
        print(f"PASS: TEST H - Report downloadable even when CWD changed to: {temp_dir}")
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    test_A_generate_verify_download()
    test_B_download_after_fastapi_restart()
    test_C_download_after_fastapi_reload()
    test_D_generate_and_download_docx()
    test_E_generate_and_download_pptx()
    test_F_multiple_reports_isolation()
    test_G_cleanup_process_does_not_remove_completed_reports()
    test_H_run_from_different_working_directory()
    print("\nALL 8 REGRESSION TESTS PASSED SUCCESSFULLY!")
