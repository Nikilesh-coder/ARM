"""
Test Health & Root API
"""

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ReportForge AI"
    assert data["status"] == "operational"
    assert "documentation" in data


def test_required_health_endpoint():
    """Specifically verifies GET /health returns exact {"status": "healthy"}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_detailed_v1_health_endpoint():
    """Verifies GET /api/v1/health provides subsystem readiness."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "reportforge-api"
    assert "subsystems" in data
    assert "database" in data["subsystems"]
    assert "storage" in data["subsystems"]
    assert "ai" in data["subsystems"]
