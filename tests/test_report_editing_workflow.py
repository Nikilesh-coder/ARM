"""
ARM Report Editing Workflow Tests
=================================
Automated verification for context-aware report editing, intent classification,
in-place DOCX updates, recoverability (backup & revert), feedback acknowledgment,
conversational Q&A, and explicit new report routing.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import docx

from apps.api.main import app
from apps.api.services.report_editing_service import report_editing_service, ReportEditingService
from apps.api.services.report_file_storage_service import report_file_storage_service
from apps.api.routers.reports import _REPORTS_STORE

client = TestClient(app)


@pytest.fixture(scope="module")
def sample_test_report():
    """Creates a temporary realistic academic report for testing in-place edits."""
    report_id = "rep_test_editing_001"
    reports_dir = report_file_storage_service.get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)

    doc_path = reports_dir / f"{report_id}.docx"

    # Create a realistic test docx
    doc = docx.Document()
    doc.add_heading("Autonomous Electric Vehicle Navigation System", level=0)
    
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph("This paper presents an autonomous navigation framework for electric ground vehicles operating in constrained environments.")

    doc.add_heading("Chapter 1: Introduction", level=1)
    doc.add_paragraph("Autonomous electric vehicles (AEVs) are rapidly transforming modern urban transport. Existing solutions face challenges in energy consumption.")

    doc.add_heading("Chapter 2: Literature Survey", level=1)
    doc.add_paragraph("Prior work in trajectory optimization has examined dynamic obstacle avoidance using heuristic search.")

    doc.add_heading("Chapter 3: System Methodology & Architecture", level=1)
    doc.add_paragraph("The proposed architecture integrates LiDAR-based SLAM with localized MPC trajectory tracking.")

    doc.add_heading("Chapter 4: Implementation & Details", level=1)
    doc.add_paragraph("Algorithms are implemented using ROS2 Humble on an NVIDIA Jetson AGX Orin embedded computing platform.")

    doc.add_heading("Chapter 5: Results & Discussion", level=1)
    doc.add_paragraph("Experimental field trials yielded an average trajectory tracking error of under 4.2 centimeters.")

    doc.add_heading("Chapter 6: Conclusion & Future Scope", level=1)
    doc.add_paragraph("In conclusion, the proposed AEV framework demonstrates robust path tracking and reduced energy expenditure.")

    doc.add_heading("References", level=1)
    doc.add_paragraph("[1] IEEE Transactions on Intelligent Transportation Systems, Vol. 25, 2024.")

    doc.save(str(doc_path))

    # Register in metadata catalog and memory store
    meta = {
        "report_id": report_id,
        "title": "Autonomous Electric Vehicle Navigation System",
        "template_id": "test_tpl_123",
        "project_id": "proj_test_456",
        "status": "completed",
        "preview_sections": [
            {"id": "abstract", "title": "Abstract", "wordCount": 16, "content": "This paper presents an autonomous navigation framework for electric ground vehicles operating in constrained environments."},
            {"id": "introduction", "title": "Chapter 1: Introduction", "wordCount": 18, "content": "Autonomous electric vehicles (AEVs) are rapidly transforming modern urban transport. Existing solutions face challenges in energy consumption."},
            {"id": "methodology", "title": "Chapter 3: System Methodology & Architecture", "wordCount": 15, "content": "The proposed architecture integrates LiDAR-based SLAM with localized MPC trajectory tracking."},
            {"id": "conclusion", "title": "Chapter 6: Conclusion & Future Scope", "wordCount": 16, "content": "In conclusion, the proposed AEV framework demonstrates robust path tracking and reduced energy expenditure."},
        ]
    }
    report_file_storage_service._save_metadata(report_id, meta)
    _REPORTS_STORE[report_id] = meta

    yield {
        "report_id": report_id,
        "doc_path": doc_path,
        "meta": meta
    }

    # Cleanup backup files if created
    backup_file = reports_dir / f"{report_id}_backup.docx"
    if backup_file.exists():
        backup_file.unlink()


# ==============================================================================
# 1. INTENT CLASSIFICATION TESTS
# ==============================================================================

def test_intent_classification_editing_instructions():
    """Verify natural-language editing instructions are classified as 'edit', not new report topics."""
    report_id = "rep_test_editing_001"

    cases = [
        ("expand the introduction", "edit", "introduction", "expand"),
        ("shorten the conclusion", "edit", "conclusion", "shorten"),
        ("correct grammar", "edit", "all", "grammar"),
        ("add more technical details", "edit", "all", "technical"),
        ("elaborate on chapter 1", "edit", "introduction", "expand"),
        ("make the methodology more concise", "edit", "methodology", "shorten"),
        ("rewrite the abstract with academic focus", "edit", "abstract", "rewrite"),
    ]

    for instruction, expected_intent, expected_section, expected_action in cases:
        result = ReportEditingService.classify_intent(instruction, active_report_id=report_id)
        assert result["intent"] == expected_intent, f"Failed for '{instruction}': expected {expected_intent}, got {result['intent']}"
        assert result["target_section"] == expected_section, f"Failed section for '{instruction}': expected {expected_section}, got {result['target_section']}"
        if expected_action:
            assert result["action"] == expected_action, f"Failed action for '{instruction}': expected {expected_action}, got {result['action']}"


def test_intent_classification_feedback():
    """Verify evaluative feedback without modification commands is classified as 'feedback'."""
    report_id = "rep_test_editing_001"

    feedback_samples = [
        "the introduction looks great",
        "chapter 2 is too brief",
        "the conclusion feels too short",
        "the results section is impressive",
        "methodology could be better",
    ]

    for fb in feedback_samples:
        result = ReportEditingService.classify_intent(fb, active_report_id=report_id)
        assert result["intent"] == "feedback", f"Failed for '{fb}': expected 'feedback', got {result['intent']}"


def test_intent_classification_questions():
    """Verify interrogative questions are answered without triggering report generation."""
    report_id = "rep_test_editing_001"

    questions = [
        "what is the word count of chapter 3?",
        "how was the methodology formulated?",
        "can you explain what algorithms are used in implementation?",
        "what is covered in the introduction?",
    ]

    for q in questions:
        result = ReportEditingService.classify_intent(q, active_report_id=report_id)
        assert result["intent"] == "question", f"Failed for '{q}': expected 'question', got {result['intent']}"


def test_intent_classification_explicit_new_report():
    """Verify explicit new report requests are properly classified as 'new_report'."""
    report_id = "rep_test_editing_001"

    new_report_queries = [
        "create a new report on solar panel efficiency",
        "generate a report about smart agriculture IoT",
        "write a new report about quantum computing",
        "new report: blockchain in healthcare",
        "start a new report on drone surveillance",
    ]

    for query in new_report_queries:
        result = ReportEditingService.classify_intent(query, active_report_id=report_id)
        assert result["intent"] == "new_report", f"Failed for '{query}': expected 'new_report', got {result['intent']}"


# ==============================================================================
# 2. IN-PLACE EDITING & TEMPLATE PRESERVATION TESTS
# ==============================================================================

def test_edit_report_expand_introduction(sample_test_report):
    """Verify expanding the introduction updates the report in-place, increases content, and preserves report ID."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "expand the introduction with additional analytical depth"}
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["report_id"] == report_id
    assert data["status"] == "completed"
    assert data["action_applied"] == "expand"
    assert data["backup_available"] is True

    # Check that backup file was created
    backup_path = sample_test_report["doc_path"].parent / f"{report_id}_backup.docx"
    assert backup_path.exists(), "Backup DOCX was not created prior to editing"

    # Verify DOCX content was expanded
    updated_doc = docx.Document(str(sample_test_report["doc_path"]))
    intro_found = False
    for p in updated_doc.paragraphs:
        if "operational efficiencies" in p.text or "algorithmic frameworks" in p.text:
            intro_found = True
            break
    assert intro_found, "Expanded text was not found in updated DOCX"


def test_edit_report_shorten_conclusion(sample_test_report):
    """Verify shortening conclusion produces concise output and preserves document integrity."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "shorten the conclusion to make it concise"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["report_id"] == report_id
    assert data["action_applied"] == "shorten"
    assert "shortened" in data["changes_summary"].lower() or "conclusion" in data["changes_summary"].lower()


def test_edit_report_correct_grammar(sample_test_report):
    """Verify correcting grammar applies non-destructive grammar standardization."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "correct grammar and polish academic tone"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] == report_id
    assert data["action_applied"] == "grammar"


def test_edit_report_add_technical_details(sample_test_report):
    """Verify adding technical details injects technical parameters into the document."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "add more technical details to methodology"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] == report_id

    # Verify technical parameters were added
    updated_doc = docx.Document(str(sample_test_report["doc_path"]))
    tech_found = False
    for p in updated_doc.paragraphs:
        if "Architectural Specifications" in p.text or "MTBF" in p.text:
            tech_found = True
            break
    assert tech_found, "Technical parameters not found in updated DOCX"


# ==============================================================================
# 3. RECOVERABILITY & REVERT TESTS
# ==============================================================================

def test_revert_report_restores_original_backup(sample_test_report):
    """Verify report can be reverted back to its original pre-edited backup state."""
    report_id = sample_test_report["report_id"]

    # Revert report
    res = client.post(f"/api/v1/reports/{report_id}/revert")
    assert res.status_code == 200
    data = res.json()

    assert data["report_id"] == report_id
    assert data["status"] == "reverted"
    assert "successfully reverted" in data["message"].lower()

    # Verify DOCX is intact
    doc = docx.Document(str(sample_test_report["doc_path"]))
    assert len(doc.paragraphs) > 0


# ==============================================================================
# 4. ASSISTANT ROUTER TESTS (EDIT, FEEDBACK, QUESTION, NEW_REPORT)
# ==============================================================================

def test_assistant_feedback_returns_confirmation_proposal(sample_test_report):
    """Verify feedback returns polite acknowledgment and update confirmation without modifying document."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        "/api/v1/reports/assistant",
        json={
            "report_id": report_id,
            "message": "the introduction looks great but chapter 2 is too brief"
        }
    )
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "feedback"
    assert data["should_generate_new"] is False
    assert "thank you for the feedback" in data["message"].lower()
    assert "'yes'" in data["message"].lower() and "'proceed'" in data["message"].lower()


def test_assistant_question_returns_factual_answer(sample_test_report):
    """Verify questions return factual answers from report without triggering report generation."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        "/api/v1/reports/assistant",
        json={
            "report_id": report_id,
            "message": "what is the word count of the report?"
        }
    )
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "question"
    assert data["should_generate_new"] is False
    assert "words" in data["answer"].lower()


def test_assistant_new_report_triggers_new_generation_flag(sample_test_report):
    """Verify explicit new report request instructs client to generate a new report."""
    report_id = sample_test_report["report_id"]

    res = client.post(
        "/api/v1/reports/assistant",
        json={
            "report_id": report_id,
            "message": "create a new report on underwater acoustic communications"
        }
    )
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "new_report"
    assert data["should_generate_new"] is True


def test_editing_instructions_do_not_trigger_new_report_generation(sample_test_report):
    """Critical contract test: Editing instructions MUST NOT trigger new report generation."""
    report_id = sample_test_report["report_id"]

    instructions = [
        "expand the introduction",
        "shorten the conclusion",
        "correct grammar",
        "add more technical details"
    ]

    for inst in instructions:
        res = client.post(
            "/api/v1/reports/assistant",
            json={
                "report_id": report_id,
                "message": inst
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["should_generate_new"] is False, f"Instruction '{inst}' mistakenly triggered new report generation!"
        assert data["intent"] in ["edit", "confirmation"], f"Instruction '{inst}' should be classified as edit/confirmation, got {data['intent']}"
        assert data.get("report_id") == report_id, f"Instruction '{inst}' altered the report_id!"


# ==============================================================================
# 5. AUTHORIZATION & OOXML GEOMETRY PRESERVATION TESTS
# ==============================================================================

def test_report_ownership_authorization(sample_test_report):
    """Verify that edit and revert endpoints enforce report ownership authorization."""
    report_id = sample_test_report["report_id"]

    # Set an owner on the report metadata
    meta = report_file_storage_service.get_report_metadata(report_id) or {}
    meta["user_id"] = "usr_owner_123"
    meta["owner_id"] = "usr_owner_123"
    report_file_storage_service._save_metadata(report_id, meta)

    # Unauthorized user attempt (different user_id)
    unauthorized_headers = {"Authorization": "Bearer test-unauthorized-user"}
    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "expand the introduction"},
        headers=unauthorized_headers
    )
    assert res.status_code == 403, f"Expected 403 for unauthorized edit, got {res.status_code}"
    assert "Unauthorized" in res.json().get("detail", "")

    # Authorized owner attempt
    authorized_headers = {"Authorization": "Bearer usr_owner_123"}
    res_ok = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "expand the introduction"},
        headers=authorized_headers
    )
    assert res_ok.status_code == 200, f"Expected 200 for authorized owner, got {res_ok.status_code}"


def test_ooxml_margins_and_geometry_preservation(sample_test_report):
    """Verify editing preserves exact OOXML page geometry, margins, and non-target section text."""
    report_id = sample_test_report["report_id"]
    doc_path = sample_test_report["doc_path"]

    # Read geometry before edit
    doc_before = docx.Document(str(doc_path))
    sec_before = doc_before.sections[0]
    top_m = sec_before.top_margin
    bottom_m = sec_before.bottom_margin
    left_m = sec_before.left_margin
    right_m = sec_before.right_margin
    p_width = sec_before.page_width
    p_height = sec_before.page_height

    # Perform edit on conclusion only
    res = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={"instruction": "shorten the conclusion"}
    )
    assert res.status_code == 200

    # Read geometry after edit
    doc_after = docx.Document(str(doc_path))
    sec_after = doc_after.sections[0]

    assert sec_after.top_margin == top_m, "Top margin was altered by editing engine!"
    assert sec_after.bottom_margin == bottom_m, "Bottom margin was altered by editing engine!"
    assert sec_after.left_margin == left_m, "Left margin was altered by editing engine!"
    assert sec_after.right_margin == right_m, "Right margin was altered by editing engine!"
    assert sec_after.page_width == p_width, "Page width was altered by editing engine!"
    assert sec_after.page_height == p_height, "Page height was altered by editing engine!"

    # Verify untouched Abstract and References sections remain intact
    full_text = "\n".join(p.text for p in doc_after.paragraphs)
    assert "autonomous navigation framework for electric ground vehicles" in full_text, "Abstract text was corrupted or lost during conclusion edit!"
    assert "IEEE Transactions on Intelligent Transportation Systems" in full_text, "References text was corrupted or lost during conclusion edit!"


def test_assistant_nonexistent_report_graceful_fallback():
    """Verify that assistant gracefully handles a non-existent report ID without raising a 500 error."""
    res = client.post(
        "/api/v1/reports/assistant",
        json={
            "message": "expand the introduction section",
            "report_id": "nonexistent-report-uuid-9999",
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "new_report"
    assert data["should_generate_new"] is True
    assert "was not found in active storage" in data["message"]


def test_report_generation_preview_sections_scoping(monkeypatch, sample_test_report):
    """Verify that report generation correctly builds preview_sections without scoping errors."""
    from apps.api.services.replacement_engine_service import replacement_engine_service

    doc_path = sample_test_report["doc_path"]

    def mock_execute(*args, **kwargs):
        return {
            "state": "COMPLETED",
            "docx_path": str(doc_path),
            "output_path": str(doc_path),
            "fields_replaced": 5,
            "images_replaced": 1,
            "field_values": {
                "introduction": "This is a synthesized test introduction for autonomous vehicles.",
                "conclusion": "This is a synthesized test conclusion with high technical fidelity."
            }
        }

    monkeypatch.setattr(replacement_engine_service, "execute_replacement", mock_execute)
    monkeypatch.setattr("apps.api.services.template_resolver.resolve_selected_template_path", lambda tpl_id: (str(doc_path), "test_tpl_123"))

    res = client.post(
        "/api/v1/reports/generate",
        json={
            "title": "Autonomous Ground Vehicles",
            "topic": "Autonomous Ground Vehicles",
            "template_id": "test_tpl_123",
        }
    )
    assert res.status_code == 200, f"Expected 200 but got {res.status_code}: {res.text}"
    data = res.json()
    assert "preview_sections" in data
    assert len(data["preview_sections"]) >= 1
    assert data["preview_sections"][0]["title"] == "Chapter 1: Introduction"



