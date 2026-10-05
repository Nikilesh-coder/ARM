"""
Test Suite for ARM's Fixed College Master Template System
Tests:
- Master Template endpoint (GET /api/v1/templates/master)
- Verification of 20 reusable college fields (types, limits, dimensions, placeholders, ordering)
- Deterministic replacement dataset generation for automation
- Template Fields list endpoint (GET /api/v1/templates/{id}/fields)
"""

from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.services.master_template_service import master_template_service

client = TestClient(app)

CANONICAL_20_FIELDS = [
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
    "advantages",
    "limitations",
    "future_scope",
    "conclusion",
    "references",
    "image_1",
    "image_2",
    "image_3",
]


def test_get_master_template_endpoint():
    res = client.get("/api/v1/templates/master")
    assert res.status_code == 200
    data = res.json()
    assert data["is_master"] is True
    assert data["fields_count"] >= 20
    assert len(data["fields"]) >= 20

    field_names = [f["field_name"] for f in data["fields"]]
    for canonical_name in CANONICAL_20_FIELDS:
        assert canonical_name in field_names, f"Missing canonical field: {canonical_name}"


def test_master_template_field_types_and_ordering():
    fields = master_template_service.get_template_fields("00000000-0000-0000-0000-000000000001")
    assert len(fields) >= 20

    field_dict = {f["field_name"]: f for f in fields}

    # Verify field types
    assert field_dict["project_title"]["field_type"] == "text"
    assert field_dict["introduction"]["field_type"] == "long_text"
    assert field_dict["technologies"]["field_type"] == "list"
    assert field_dict["references"]["field_type"] == "list"
    assert field_dict["image_1"]["field_type"] == "image"
    assert field_dict["image_2"]["field_type"] == "image"
    assert field_dict["image_3"]["field_type"] == "image"

    # Verify placeholder identifiers
    assert field_dict["project_title"]["placeholder_identifier"] == "{{PROJECT_TITLE}}"
    assert field_dict["introduction"]["placeholder_identifier"] == "{{INTRODUCTION}}"
    assert field_dict["image_1"]["placeholder_identifier"] == "{{IMAGE_1}}"

    # Verify image dimensions
    assert field_dict["image_1"]["image_dimensions"]["dpi"] == 300
    assert field_dict["image_1"]["image_dimensions"]["width"] == 800

    # Verify content limits
    assert field_dict["introduction"]["content_limits"]["max_words"] == 800
    assert field_dict["technologies"]["content_limits"]["max_items"] == 10

    # Verify sequential ordering
    orderings = [f.get("ordering", 0) for f in fields]
    assert orderings == sorted(orderings)


def test_build_replacement_dataset():
    project_data = {
        "title": "Autonomous Autonomous Robotics Platform",
        "student_name": "Alex Mercer",
        "roll_number": "CS2026-9021",
        "department": "Department of Computer Engineering",
        "guide_name": "Dr. Alan Turing",
        "abstract_summary": "Full overview of robotic locomotion and perception.",
        "problem_statement": "Robotic navigation in unstructured disaster environments.",
        "methodology": "Graph neural networks paired with LiDAR odometry.",
        "technologies": ["Python", "ROS2", "PyTorch", "OpenCV"],
        "future_scope": "Integration with aerial drone swarms.",
    }
    evidence_assets = [
        {"id": "ev_1", "caption": "LiDAR point cloud scan", "storage_path": "/storage/img1.png"},
        {"id": "ev_2", "caption": "Chassis prototype", "storage_path": "/storage/img2.png"},
    ]

    dataset = master_template_service.build_replacement_dataset(
        project_data=project_data,
        evidence_assets=evidence_assets,
    )

    assert dataset["project_title"] == "Autonomous Autonomous Robotics Platform"
    assert dataset["student_name"] == "Alex Mercer"
    assert dataset["roll_number"] == "CS2026-9021"
    assert dataset["department"] == "Department of Computer Engineering"
    assert dataset["guide_name"] == "Dr. Alan Turing"
    assert "Graph neural networks" in dataset["methodology"]
    assert dataset["technologies"] == ["Python", "ROS2", "PyTorch", "OpenCV"]
    assert dataset["image_1"] == "/storage/img1.png"
    assert dataset["image_2"] == "/storage/img2.png"
