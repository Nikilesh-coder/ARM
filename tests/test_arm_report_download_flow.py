"""
ARM Comprehensive Test Suite: Report Download Flow & ID Consistency
===================================================================
Verifies:
1. Generation returns consistent report_id, job_id, and document_id.
2. Download using the EXACT returned ID succeeds.
3. Downloaded file exists, is non-empty, and is a valid DOCX file.
4. Resilient resolution across aliases and storage lookups.
5. Missing file returns detailed diagnostic 404 error without masking.
6. PDF download returns intentional 400 for DOCX-first architecture.
"""

import os
import io
import pytest
from fastapi.testclient import TestClient
import docx

from apps.api.main import app
from apps.api.routers.projects import _PROJECTS_STORE

client = TestClient(app)

JAGADEESH_TPL_ID = "0484aecb-dbc1-4671-a388-0f820124ca0e"


def test_1_zero_change_generation_and_download_flow():
    """
    Test 1: Zero-change generation returns exact template copy and valid report_id.
    Downloading with the exact returned ID yields a valid, non-empty DOCX.
    """
    print("\n--- TEST 1: Zero-Change Generation & Download Flow ---")
    gen_payload = {
        "title": "",  # zero change intent
        "template_id": JAGADEESH_TPL_ID,
    }
    gen_resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert gen_resp.status_code == 200, f"Generation failed: {gen_resp.text}"
    gen_data = gen_resp.json()

    # 1. Verify ID consistency
    report_id = gen_data.get("report_id")
    job_id = gen_data.get("job_id")
    doc_id = gen_data.get("document_id")

    assert report_id and len(report_id) > 3, "Missing report_id"
    assert job_id == report_id, f"job_id ({job_id}) must match report_id ({report_id})"
    assert doc_id == report_id, f"document_id ({doc_id}) must match report_id ({report_id})"
    print(f"  Returned Report ID: {report_id}")

    # 2. Request download using the EXACT returned ID
    download_url = f"/api/v1/reports/{report_id}/download"
    dl_resp = client.get(download_url)
    assert dl_resp.status_code == 200, f"Download failed: {dl_resp.text}"

    # 3. Verify content
    content_bytes = dl_resp.content
    assert len(content_bytes) > 10000, f"Downloaded file is too small ({len(content_bytes)} bytes)"

    # 4. Verify valid DOCX
    bio = io.BytesIO(content_bytes)
    doc = docx.Document(bio)
    assert len(doc.paragraphs) > 0, "DOCX has no paragraphs"

    # 5. Verify Content-Disposition filename
    cd_header = dl_resp.headers.get("content-disposition", "")
    assert f"Report_{report_id}.docx" in cd_header or f"{report_id}" in cd_header
    print(f"PASS: TEST 1 - Downloaded valid DOCX ({len(content_bytes)} bytes) using exact ID {report_id}")


def test_2_full_ai_irrigation_generation_and_download_flow():
    """
    Test 2: Full report replacement for 'AI Based Irrigation System'.
    Verifies that the returned ID allows immediate, reliable DOCX download.
    """
    print("\n--- TEST 2: AI Irrigation Generation & Download Flow ---")
    proj_id = "proj_test_download_e2e"
    _PROJECTS_STORE[proj_id] = {
        "id": proj_id,
        "title": "AI Based Irrigation System",
        "project_name": "AI Based Irrigation System",
        "report_title": "AI Based Irrigation System",
        "template_id": JAGADEESH_TPL_ID,
        "description": "Smart precision irrigation with closed loop sensors and edge inference.",
    }

    gen_payload = {
        "title": "AI Based Irrigation System",
        "project_id": proj_id,
        "template_id": JAGADEESH_TPL_ID,
        "problem_statement": "Manual irrigation wastes water and stresses crops.",
        "proposed_solution": "Edge IoT sensor telemetry and automated solenoid regulation.",
    }

    gen_resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert gen_resp.status_code == 200, f"Generation failed: {gen_resp.text}"
    gen_data = gen_resp.json()

    report_id = gen_data.get("report_id")
    assert report_id, "Missing report_id"
    print(f"  Generated Report ID: {report_id}")

    # Download using exact returned report_id
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200, f"Download failed: {dl_resp.text}"

    content_bytes = dl_resp.content
    assert len(content_bytes) > 20000, f"Downloaded file too small ({len(content_bytes)} bytes)"

    # Verify DOCX readability
    bio = io.BytesIO(content_bytes)
    doc = docx.Document(bio)
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "AI Based Irrigation System" in full_text
    print(f"PASS: TEST 2 - Successfully downloaded valid AI Irrigation DOCX ({len(content_bytes)} bytes)")


def test_3_id_resolution_across_aliases():
    """
    Test 3: Download endpoint resolves job_id, document_id, and doc- prefixed aliases.
    """
    print("\n--- TEST 3: ID Resolution Across Aliases ---")
    gen_payload = {
        "title": "Smart Irrigation Telemetry",
        "template_id": JAGADEESH_TPL_ID,
    }
    gen_resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    report_id = gen_data["report_id"]

    # Test downloading via alias f"doc-{report_id}"
    dl_alias = client.get(f"/api/v1/reports/doc-{report_id}/download")
    assert dl_alias.status_code == 200, f"Alias download failed: {dl_alias.text}"
    assert len(dl_alias.content) > 10000

    # Test downloading via replacement router: /api/v1/replacement/download/{job_id}
    dl_repl = client.get(f"/api/v1/replacement/download/{report_id}?format=docx")
    assert dl_repl.status_code == 200
    assert len(dl_repl.content) > 10000
    print("PASS: TEST 3 - Both /reports/ and /replacement/ resolved aliases cleanly.")


def test_4_nonexistent_id_returns_diagnostic_404_without_masking():
    """
    Test 4: Nonexistent report ID returns 404 with full diagnostic error details.
    """
    print("\n--- TEST 4: Nonexistent ID Returns Diagnostic 404 ---")
    bogus_id = "nonexistent_rep_9999999"
    dl_resp = client.get(f"/api/v1/reports/{bogus_id}/download")
    assert dl_resp.status_code == 404
    error_text = dl_resp.text
    print(f"  Received 404 error detail: {error_text}")

    # Must contain diagnostic info
    assert "not found" in error_text.lower()
    assert bogus_id in error_text
    assert "Requested ID" in error_text or "requested_id" in error_text
    print("PASS: TEST 4 - Diagnostic 404 returned without masking.")


def test_5_pdf_download_returns_explicit_400():
    """
    Test 5: PDF download requests return HTTP 400 guiding user to DOCX.
    """
    print("\n--- TEST 5: PDF Download Request Handling ---")
    resp = client.get("/api/v1/reports/any_id/download-pdf")
    assert resp.status_code == 400
    assert "DOCX" in resp.json().get("detail", "")
    print("PASS: TEST 5 - PDF download correctly returns HTTP 400 informing user.")


if __name__ == "__main__":
    test_1_zero_change_generation_and_download_flow()
    test_2_full_ai_irrigation_generation_and_download_flow()
    test_3_id_resolution_across_aliases()
    test_4_nonexistent_id_returns_diagnostic_404_without_masking()
    test_5_pdf_download_returns_explicit_400()
    print("\n===========================================================")
    print("ALL 5 DOWNLOAD FLOW TESTS PASSED!")
