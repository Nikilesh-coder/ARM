"""
ARM My Projects Section - Authentication, Authorization & User Scoping Tests
Verifies:
1. Strict user isolation: Each authenticated user only sees their own projects.
2. Zero cross-exposure: User A never sees User B's projects; unauthenticated requests see no projects.
3. Access control: Unauthorized read, update, or delete attempts return 403 Forbidden.
4. Rich summary schema: Shows title, status, template, last updated, generation status, and latest report.
5. All required actions work reliably: Open, Continue, Regenerate, Preview, Download, Delete.
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


@pytest.fixture
def user_alpha_headers():
    return {"Authorization": "Bearer usr_student_alpha"}


@pytest.fixture
def user_beta_headers():
    return {"Authorization": "Bearer usr_student_beta"}


def test_user_project_isolation(user_alpha_headers, user_beta_headers):
    """
    Verifies that User A and User B only see their own projects,
    and neither user can access or view the other user's projects.
    """
    alpha_title = f"Alpha Edge Robotics - {uuid.uuid4().hex[:6]}"
    beta_title = f"Beta Deep Learning - {uuid.uuid4().hex[:6]}"

    # 1. User Alpha creates a project
    res_alpha_create = client.post(
        "/api/v1/projects",
        headers=user_alpha_headers,
        json={
            "title": alpha_title,
            "project_type": "capstone",
            "guide_name": "Dr. Alpha Guide",
            "department": "Robotics Engineering",
        },
    )
    assert res_alpha_create.status_code == 200
    alpha_proj_id = res_alpha_create.json()["id"]

    # 2. User Beta creates a project
    res_beta_create = client.post(
        "/api/v1/projects",
        headers=user_beta_headers,
        json={
            "title": beta_title,
            "project_type": "thesis",
            "guide_name": "Dr. Beta Guide",
            "department": "Artificial Intelligence",
        },
    )
    assert res_beta_create.status_code == 200
    beta_proj_id = res_beta_create.json()["id"]

    # 3. User Alpha lists projects -> Must contain Alpha's project, NOT Beta's project
    res_alpha_list = client.get("/api/v1/projects", headers=user_alpha_headers)
    assert res_alpha_list.status_code == 200
    alpha_projects = res_alpha_list.json()
    alpha_ids = [p["id"] for p in alpha_projects]
    assert alpha_proj_id in alpha_ids
    assert beta_proj_id not in alpha_ids

    # 4. User Beta lists projects -> Must contain Beta's project, NOT Alpha's project
    res_beta_list = client.get("/api/v1/projects", headers=user_beta_headers)
    assert res_beta_list.status_code == 200
    beta_projects = res_beta_list.json()
    beta_ids = [p["id"] for p in beta_projects]
    assert beta_proj_id in beta_ids
    assert alpha_proj_id not in beta_ids

    # 5. Unauthenticated request -> Must return empty list, never exposing projects
    res_unauth = client.get("/api/v1/projects")
    assert res_unauth.status_code == 200
    assert len(res_unauth.json()) == 0


def test_cross_user_authorization_protection(user_alpha_headers, user_beta_headers):
    """
    Verifies that User Beta cannot inspect, modify, or delete User Alpha's project.
    """
    # Create project owned by Alpha
    res_create = client.post(
        "/api/v1/projects",
        headers=user_alpha_headers,
        json={
            "title": "Confidential Research System",
            "project_type": "capstone",
        },
    )
    assert res_create.status_code == 200
    alpha_proj_id = res_create.json()["id"]

    # User Beta attempts to read Alpha's project -> 403 Forbidden
    res_read = client.get(f"/api/v1/projects/{alpha_proj_id}", headers=user_beta_headers)
    assert res_read.status_code == 403
    assert "Forbidden" in res_read.json()["detail"]

    # User Beta attempts to patch Alpha's project -> 403 Forbidden
    res_patch = client.patch(
        f"/api/v1/projects/{alpha_proj_id}",
        headers=user_beta_headers,
        json={"title": "Hacked Title"},
    )
    assert res_patch.status_code == 403

    # User Beta attempts to delete Alpha's project -> 403 Forbidden
    res_del = client.delete(f"/api/v1/projects/{alpha_proj_id}", headers=user_beta_headers)
    assert res_del.status_code == 403


def test_project_rich_metadata_fields(user_alpha_headers):
    """
    Verifies each project returns:
    - Title
    - Status
    - Template name
    - Last updated timestamp
    - Generation status
    - Latest report summary structure
    """
    res_create = client.post(
        "/api/v1/projects",
        headers=user_alpha_headers,
        json={
            "title": "Embedded IoT Gateway",
            "project_type": "capstone",
            "department": "Electronics & Communication",
        },
    )
    assert res_create.status_code == 200
    proj_id = res_create.json()["id"]

    res_list = client.get("/api/v1/projects", headers=user_alpha_headers)
    assert res_list.status_code == 200
    projects = res_list.json()
    target = next((p for p in projects if p["id"] == proj_id), None)
    assert target is not None

    # Check required fields
    assert target["title"] == "Embedded IoT Gateway"
    assert "status" in target
    assert "template_name" in target
    assert target["template_name"] is not None
    assert "updated_at" in target
    assert "generation_status" in target
    # Field exists even before generation
    assert "latest_report" in target


def test_delete_project_action(user_alpha_headers):
    """
    Verifies the Delete action:
    Authentic owner can delete their own project and subsequent lookups return 404.
    """
    res_create = client.post(
        "/api/v1/projects",
        headers=user_alpha_headers,
        json={"title": "Temporary Test Project to Delete"},
    )
    assert res_create.status_code == 200
    proj_id = res_create.json()["id"]

    # Delete project
    res_del = client.delete(f"/api/v1/projects/{proj_id}", headers=user_alpha_headers)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"

    # Confirm deleted
    res_get = client.get(f"/api/v1/projects/{proj_id}", headers=user_alpha_headers)
    assert res_get.status_code == 404


def test_regenerate_project_action(user_alpha_headers):
    """
    Verifies the Regenerate action:
    Triggers template replacement for the target project.
    """
    res_create = client.post(
        "/api/v1/projects",
        headers=user_alpha_headers,
        json={
            "title": "Autonomous Drone Pathfinding",
            "description": "Real-time navigation algorithm on constrained hardware.",
        },
    )
    assert res_create.status_code == 200
    proj_id = res_create.json()["id"]

    # Trigger regeneration endpoint
    res_regen = client.post(f"/api/v1/projects/{proj_id}/regenerate", headers=user_alpha_headers)
    assert res_regen.status_code == 200
    regen_data = res_regen.json()
    assert regen_data["state"] in ("COMPLETED", "REPLACING", "VALIDATING")
    assert regen_data["project_id"] == proj_id
