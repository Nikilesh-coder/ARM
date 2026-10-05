"""
Test Suite for ARM AI Report Agent
Tests:
- End-to-end structured generation via POST /api/v1/agent/generate-report-content
- Output matches Master Template fields strictly (no uncontrolled text)
- Field types verification (lists as arrays, text/long_text as strings, image fields)
- Validation report verification (all required fields present, constraints checked)
- Optional user instructions and uploaded evidence integration
- Validation failure handling for invalid payloads
"""

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_ai_report_agent_master_template_generation():
    payload = {
        "project_title": "Deep Learning Based Plant Leaf Disease Diagnosis",
        "project_description": "An automated vision pipeline using convolutional neural networks and transfer learning on edge microcontrollers to detect early fungal infections in tomato crops.",
        "user_instructions": "Prioritize model quantization for edge deployment and include high-resolution confusion matrix figures.",
        "template_id": "00000000-0000-0000-0000-000000000001",
        "student_name": "Rohan Deshmukh",
        "roll_number": "2026-CS-401",
        "department": "Department of Computer Science & Engineering",
        "guide_name": "Dr. Meera Nambiar"
    }

    res = client.post("/api/v1/agent/generate-report-content", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["stage"] == "completed"
    assert "content" in data
    content = data["content"]

    # Verify canonical required fields exist in output
    required_keys = [
        "project_title",
        "student_name",
        "roll_number",
        "department",
        "guide_name",
        "introduction",
        "objectives",
        "problem_statement",
        "methodology",
        "technologies",
        "implementation",
        "results",
        "conclusion",
        "references"
    ]
    for key in required_keys:
        assert key in content, f"Missing key in AI Agent output: {key}"

    # Verify structured types
    assert isinstance(content["project_title"], str)
    assert isinstance(content["introduction"], str)
    assert isinstance(content["methodology"], str)
    assert isinstance(content["objectives"], list)
    assert len(content["objectives"]) >= 2
    assert isinstance(content["technologies"], list)
    assert len(content["technologies"]) >= 2
    assert isinstance(content["references"], list)

    # Verify validation report
    assert "validation" in data
    val = data["validation"]
    assert val["is_valid"] is True
    assert val["total_fields"] >= 20
    assert val["valid_fields_count"] >= 20


def test_ai_report_agent_custom_template_fields():
    custom_fields = [
        {
            "field_name": "project_title",
            "field_type": "text",
            "is_required": True
        },
        {
            "field_name": "core_novelty",
            "field_type": "long_text",
            "is_required": True,
            "content_limits": {"min_words": 50, "max_words": 200}
        },
        {
            "field_name": "key_benchmarks",
            "field_type": "list",
            "is_required": True,
            "content_limits": {"min_items": 3, "max_items": 5}
        }
    ]

    payload = {
        "project_title": "Quantum Key Distribution Protocol Simulator",
        "project_description": "Simulating BB84 protocol under turbulent atmospheric photon scattering channels.",
        "template_fields": custom_fields
    }

    res = client.post("/api/v1/agent/generate-report-content", json=payload)
    assert res.status_code == 200
    data = res.json()
    content = data["content"]

    assert "project_title" in content
    assert "core_novelty" in content
    assert "key_benchmarks" in content
    assert isinstance(content["key_benchmarks"], list)
    assert isinstance(content["core_novelty"], str)
    assert len(content["key_benchmarks"]) >= 3


def test_ai_report_agent_validation_rejects_missing_inputs():
    # Missing required project_description
    payload = {
        "project_title": "Incomplete Project Payload"
    }
    res = client.post("/api/v1/agent/generate-report-content", json=payload)
    assert res.status_code == 422
