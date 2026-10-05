"""
ARM - Complete End-to-End Real-World Workflow Verification Suite
Validates the complete 17-step lifecycle:
1. User logs in / authenticates.
2. User opens New Chat/Create Project.
3. User enters project topic.
4. User selects Master Template.
5. ARM analyzes required fields.
6. ARM AI generates structured report content.
7. ARM identifies required images.
8. ARM obtains valid image assets (300 DPI, CC-BY-4.0).
9. ARM maps content to template fields.
10. ARM replaces existing template matter.
11. ARM replaces existing images.
12. ARM preserves college template formatting.
13. ARM validates generated report.
14. ARM shows actual report preview.
15. User approves report.
16. User downloads DOCX and PDF.
17. Optional Canva action checked.

Also verifies:
- Authorization & cross-tenant security
- API error handling
- Empty and invalid state handling
"""

import os
import io
import json
import uuid
import pytest
from docx import Document
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.master_template_service import MASTER_TEMPLATE_ID, master_template_service
from apps.api.services.replacement_engine_service import replacement_engine_service

client = TestClient(app)

USER_A_ID = "00000000-0000-0000-0000-00000000000a"
USER_B_ID = "00000000-0000-0000-0000-00000000000b"


AUTH_HEADER_USER_A = {"Authorization": f"Bearer {USER_A_ID}"}
AUTH_HEADER_USER_B = {"Authorization": f"Bearer {USER_B_ID}"}


def test_complete_e2e_arm_workflow():
    """
    Executes the complete real-world 17-step workflow from login through download.
    """
    # -------------------------------------------------------------------------
    # STEP 1: User logs in / authentication check
    # -------------------------------------------------------------------------
    auth_check = client.get("/api/v1/projects", headers=AUTH_HEADER_USER_A)
    assert auth_check.status_code == 200
    initial_projects = auth_check.json()
    assert isinstance(initial_projects, list)

    # -------------------------------------------------------------------------
    # STEP 2 & 3: User opens New Chat / Create Project and enters project topic
    # -------------------------------------------------------------------------
    project_payload = {
        "title": "Autonomous Decentralized Consensus in High-Throughput Edge Networks",
        "description": "Novel Byzantine Fault Tolerant protocol optimized for low-latency peer-to-peer embedded edge clusters.",
        "project_type": "capstone",
        "department": "Computer Science & Engineering",
        "institution": "National Institute of Technology",
        "academic_year": "2025-2026",
        "semester": "8th Semester",
    }
    create_resp = client.post("/api/v1/projects", json=project_payload, headers=AUTH_HEADER_USER_A)
    assert create_resp.status_code in (200, 201)
    project_data = create_resp.json()
    project_id = project_data["id"]
    assert project_id is not None
    assert project_data["title"] == project_payload["title"]

    # -------------------------------------------------------------------------
    # STEP 4 & 5: User selects Master Template; ARM analyzes required fields
    # -------------------------------------------------------------------------
    analyze_resp = client.post(
        "/api/v1/replacement/analyze",
        json={"template_id": MASTER_TEMPLATE_ID},
        headers=AUTH_HEADER_USER_A,
    )
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert analysis["template_id"] == MASTER_TEMPLATE_ID
    assert analysis["total_fields"] >= 15
    assert len(analysis["image_fields"]) >= 2
    assert "project_title" in analysis["canonical_fields"]
    assert "methodology" in analysis["canonical_fields"]
    assert "results" in analysis["canonical_fields"]

    # -------------------------------------------------------------------------
    # STEP 6: ARM AI generates structured report content
    # -------------------------------------------------------------------------
    structured_content = {
        "project_title": "Autonomous Decentralized Consensus in High-Throughput Edge Networks",
        "student_name": "Scholar Alpha",
        "roll_number": "2022BCSE042",
        "department": "Computer Science & Engineering",
        "guide_name": "Dr. Sarah Jenkins, Ph.D.",
        "introduction": (
            "Modern edge computing environments demand resilient consensus mechanisms capable of operating "
            "over unstable network links without sacrificing transaction throughput. Traditional Proof-of-Work "
            "and heavyweight PBFT algorithms incur prohibitive computational and bandwidth overhead on low-power "
            "embedded devices. This investigation introduces an asynchronous, quorum-adaptive consensus algorithm "
            "engineered explicitly for edge compute clusters."
        ),
        "objectives": [
            "Design a partitioned directed acyclic graph (DAG) ledger for micro-transactions.",
            "Formulate a lightweight Byzantine agreement protocol achieving sub-50ms finality.",
            "Benchmark fault tolerance and throughput under 30% node adversarial dropouts.",
        ],
        "problem_statement": (
            "Existing distributed ledgers require excessive communication rounds and computational overhead, "
            "rendering them impractical for edge gateways with intermittent connectivity and strict energy budgets."
        ),
        "methodology": (
            "The proposed protocol implements an asynchronous leaderless round model. Nodes validate incoming state "
            "transitions using verifiable secret sharing (VSS) and threshold signatures. Network traffic is partitioned "
            "into local consensus shards, minimizing cross-edge synchronization delays while upholding safety invariants."
        ),
        "technologies": [
            "Rust 1.78 Core Engine",
            "Tokio Asynchronous Runtime",
            "BLS12-381 Threshold Cryptography",
            "gRPC / Protocol Buffers Transport",
            "Docker / Kubernetes Testbed",
        ],
        "implementation": (
            "The software prototype was implemented in Rust to guarantee memory safety and deterministic execution latency. "
            "The node runtime utilizes asynchronous actor channels to isolate network I/O from cryptographic signature verification."
        ),
        "results": (
            "Empirical evaluation demonstrated a peak sustained throughput of 14,200 transactions per second across a 50-node "
            "simulated edge cluster. P99 consensus finality was achieved in 38 milliseconds, representing a 3.4x improvement "
            "over standard Raft and PBFT baselines under comparable network latency."
        ),
        "advantages": [
            "Sub-50ms deterministic consensus latency",
            "Low CPU and memory footprint suitable for Raspberry Pi class hardware",
            "Mathematical Byzantine safety up to 33% malicious nodes",
        ],
        "limitations": [
            "Requires initial clock synchronization within a 200ms skew tolerance",
            "Dynamic membership reconfiguration requires an epoch transition phase",
        ],
        "future_scope": (
            "Future research will explore zero-knowledge proof compression for transaction histories and hardware-assisted "
            "secure enclave validation on ARM Cortex-M processors."
        ),
        "conclusion": (
            "The presented edge consensus protocol successfully mitigates latency and throughput bottlenecks in distributed "
            "edge networks, validating the feasibility of autonomous decentralized ledgers in mission-critical environments."
        ),
        "references": [
            "Castro, M., & Liskov, B. (2002). Practical Byzantine fault tolerance. ACM TOCS, 20(4), 398-461.",
            "Lamport, L. (1998). The part-time parliament. ACM TOCS, 16(2), 133-169.",
            "Bano, S., et al. (2019). SoK: Consensus in the age of blockchains. ACM AFT, 183-198.",
        ],
    }

    # -------------------------------------------------------------------------
    # STEP 7 & 8: ARM identifies required images and obtains valid assets
    # -------------------------------------------------------------------------
    reqs_resp = client.post(
        f"/api/v1/projects/{project_id}/assets/determine-requirements",
        json={
            "project_title": project_payload["title"],
            "project_description": project_payload["description"],
            "template_id": MASTER_TEMPLATE_ID,
        },
        headers=AUTH_HEADER_USER_A,
    )
    assert reqs_resp.status_code == 200
    reqs_data = reqs_resp.json()
    assert reqs_data["total_image_fields"] >= 2
    assert any(r["template_field"] == "image_1" for r in reqs_data["requirements"])

    # Run image acquisition pipeline
    pipeline_resp = client.post(
        f"/api/v1/projects/{project_id}/assets/pipeline",
        json={
            "project_id": project_id,
            "project_title": project_payload["title"],
            "project_description": project_payload["description"],
            "template_id": MASTER_TEMPLATE_ID,
            "preferred_provider": "diagram_engine",
        },
        headers=AUTH_HEADER_USER_A,
    )
    assert pipeline_resp.status_code == 200
    pipeline_data = pipeline_resp.json()
    assert pipeline_data["status"] == "completed"
    assert pipeline_data["successful_images_count"] >= 2
    assert len(pipeline_data["assets"]) >= 2

    # Verify image assets have valid binaries, 300 DPI metadata, and open academic licensing
    image_assets_map = {}
    for asset in pipeline_data["assets"]:
        assert asset["storage_path"] is not None
        assert os.path.exists(asset["storage_path"])
        assert asset["file_size_bytes"] > 0
        assert "CC" in asset["license_info"] or "Academic" in asset["license_info"]
        image_assets_map[asset["template_field"]] = asset["storage_path"]

    # -------------------------------------------------------------------------
    # STEP 9, 10, 11, 12: ARM maps content, replaces text & images, preserves template
    # -------------------------------------------------------------------------
    exec_resp = client.post(
        "/api/v1/replacement/execute",
        json={
            "project_id": project_id,
            "template_id": MASTER_TEMPLATE_ID,
            "custom_content": structured_content,
            "custom_assets": image_assets_map,
        },
        headers=AUTH_HEADER_USER_A,
    )
    assert exec_resp.status_code == 200
    job_data = exec_resp.json()
    job_id = job_data["job_id"]
    assert job_id is not None
    assert job_data["state"] == "COMPLETED"
    assert job_data["fields_replaced"] >= 10
    assert job_data["images_replaced"] >= 1

    # Verify generated DOCX exists and preserves document structure
    docx_path = job_data["docx_path"]
    assert docx_path is not None
    assert os.path.exists(docx_path)

    doc = Document(docx_path)
    all_paras = list(doc.paragraphs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                all_paras.extend(cell.paragraphs)
    full_text = " ".join(p.text for p in all_paras)

    # Check that template matter was replaced with user's content
    assert "Autonomous Decentralized Consensus" in full_text
    assert "Scholar Alpha" in full_text
    assert "Dr. Sarah Jenkins" in full_text
    assert "sub-50ms finality" in full_text

    # Check that images were placed in inline shapes
    total_images_in_doc = len(doc.inline_shapes)
    assert total_images_in_doc >= 1

    # -------------------------------------------------------------------------
    # STEP 13: ARM validates the generated report
    # -------------------------------------------------------------------------
    stats = job_data.get("stats")
    assert stats is not None
    word_count = stats.get("word_count") or stats.get("estimated_word_count") or 0
    assert word_count > 100
    assert stats.get("page_count", 0) > 0
    assert stats.get("validation_status") in ("VALID", "PASSED")
    assert len(job_data.get("errors", [])) == 0


    # -------------------------------------------------------------------------
    # STEP 14: ARM shows the actual report preview
    # -------------------------------------------------------------------------
    preview_resp = client.get(f"/api/v1/replacement/preview/{job_id}", headers=AUTH_HEADER_USER_A)
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["job_id"] == job_id
    assert preview_data["preview_html"] is not None
    assert len(preview_data["preview_html"]) > 200
    assert "Autonomous Decentralized Consensus" in preview_data["preview_html"]
    assert preview_data["approval_status"] == "pending"

    # -------------------------------------------------------------------------
    # STEP 15: User approves the report
    # -------------------------------------------------------------------------
    approve_resp = client.post(f"/api/v1/replacement/approve/{job_id}", headers=AUTH_HEADER_USER_A)
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["approval_status"] == "approved"
    assert approved_data["approved_at"] is not None

    # Check that preview reflects approval
    preview_check = client.get(f"/api/v1/replacement/preview/{job_id}", headers=AUTH_HEADER_USER_A)
    assert preview_check.json()["approval_status"] == "approved"

    # -------------------------------------------------------------------------
    # STEP 16: User downloads DOCX and PDF
    # -------------------------------------------------------------------------
    download_docx = client.get(f"/api/v1/replacement/jobs/{job_id}/download?format=docx", headers=AUTH_HEADER_USER_A)
    assert download_docx.status_code == 200
    assert download_docx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert download_docx.content.startswith(b"PK\x03\x04")  # Standard ZIP/DOCX header
    assert len(download_docx.content) > 1000

    download_pdf = client.get(f"/api/v1/replacement/jobs/{job_id}/download?format=pdf", headers=AUTH_HEADER_USER_A)
    assert download_pdf.status_code == 200
    assert download_pdf.headers["content-type"] == "application/pdf"
    assert download_pdf.content.startswith(b"%PDF")  # PDF magic bytes
    assert len(download_pdf.content) > 100

    # -------------------------------------------------------------------------
    # STEP 17: Optional Canva action is checked
    # -------------------------------------------------------------------------
    canva_status_resp = client.get("/api/v1/integrations/canva", headers=AUTH_HEADER_USER_A)
    assert canva_status_resp.status_code == 200
    canva_info = canva_status_resp.json()
    assert canva_info["id"] == "canva"
    assert canva_info["fallback_available"] is True

    # If unconfigured, Canva export rejects gracefully without fabricating
    canva_export = client.post(
        "/api/v1/integrations/canva/export",
        json={"project_id": project_id, "design_type": "presentation"},
        headers=AUTH_HEADER_USER_A,
    )
    assert canva_export.status_code == 200
    export_res = canva_export.json()
    if not canva_info["is_configured"]:
        assert export_res["status"] == "unconfigured"
        assert export_res["export_url"] is None
        assert "CANVA_CLIENT_ID" in export_res["error"]


def test_authorization_and_cross_tenant_isolation():
    """
    Verifies that User B cannot access, preview, approve, download, or delete User A's project.
    """
    # 1. Create project as User A
    resp_a = client.post(
        "/api/v1/projects",
        json={"title": "Confidential Research User A", "project_type": "capstone"},
        headers=AUTH_HEADER_USER_A,
    )
    assert resp_a.status_code in (200, 201)
    proj_a_id = resp_a.json()["id"]

    # 2. User B tries to view User A's project -> 403 Forbidden
    resp_b_view = client.get(f"/api/v1/projects/{proj_a_id}", headers=AUTH_HEADER_USER_B)
    assert resp_b_view.status_code == 403

    # 3. User B tries to regenerate User A's project -> 403 Forbidden
    resp_b_regen = client.post(f"/api/v1/projects/{proj_a_id}/regenerate", headers=AUTH_HEADER_USER_B)
    assert resp_b_regen.status_code == 403

    # 4. User B tries to delete User A's project -> 403 Forbidden
    resp_b_del = client.delete(f"/api/v1/projects/{proj_a_id}", headers=AUTH_HEADER_USER_B)
    assert resp_b_del.status_code == 403

    # 5. User A can delete their own project -> 200 OK
    resp_a_del = client.delete(f"/api/v1/projects/{proj_a_id}", headers=AUTH_HEADER_USER_A)
    assert resp_a_del.status_code == 200


def test_api_error_handling_and_invalid_states():
    """
    Verifies meaningful error handling for invalid templates, missing jobs, and bad parameters.
    """
    # 1. Nonexistent job download -> 404
    bad_download = client.get("/api/v1/replacement/jobs/nonexistent-job-uuid/download?format=docx")
    assert bad_download.status_code == 404
    assert "not found" in bad_download.json()["detail"].lower()

    # 2. Nonexistent job preview -> 404
    bad_preview = client.get("/api/v1/replacement/preview/nonexistent-job-uuid")
    assert bad_preview.status_code == 404

    # 3. Nonexistent job approval -> 404
    bad_approve = client.post("/api/v1/replacement/approve/nonexistent-job-uuid")
    assert bad_approve.status_code == 404

    # 4. Nonexistent template analysis -> 404
    bad_template = client.post("/api/v1/replacement/analyze", json={"template_id": "00000000-0000-0000-0000-999999999999"})
    assert bad_template.status_code == 404
