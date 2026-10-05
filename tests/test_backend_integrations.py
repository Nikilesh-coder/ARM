"""
ARM Integration Configuration & Validation Test Suite
Tests:
1. Secret Isolation: Verify that NO secrets, keys, or tokens are returned by any integration endpoint.
2. Configuration Validation: Verify validation for all 4 categories (ai, image, document, canva).
3. Graceful Error Handling & Fallback: Verify that unavailable APIs produce meaningful errors, do not fabricate results, and permit ARM to continue.
4. Canva Integration: Verify that unconfigured Canva calls return clear errors without fabricated exports.
5. Image Provider Fallback: Verify native visual engine fallback when external APIs are unconfigured.
6. Document Provider: Verify that Carbone and Internal engines report accurate configuration state.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.core.config import settings
from apps.api.services.integration_service import integration_service
from apps.api.services.image_system import ImageAcquisitionEngine, ImageRequirementDTO

client = TestClient(app)


def test_secret_isolation_in_status_endpoints():
    """Verify that NO API keys or secrets are exposed in API responses."""
    resp = client.get("/api/v1/integrations/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "integrations" in data
    assert len(data["integrations"]) == 4

    response_text = resp.text.lower()
    # Confirm secret names may exist in required_env_vars, but actual secret values must NEVER appear
    if settings.ai.gemini_api_key and len(settings.ai.gemini_api_key) > 8:
        assert settings.ai.gemini_api_key not in response_text
    if settings.database.supabase_service_role_key:
        assert settings.database.supabase_service_role_key not in response_text

    for item in data["integrations"]:
        assert item["id"] in ("ai", "image", "document", "canva")
        assert "status" in item
        assert "required_env_vars" in item
        # Ensure values are not in item dictionary
        assert "api_key" not in item
        assert "secret_key" not in item
        assert "client_secret" not in item


def test_get_single_integration_status():
    """Verify single integration status lookup."""
    for int_id in ["ai", "image", "document", "canva"]:
        resp = client.get(f"/api/v1/integrations/{int_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == int_id
        assert "name" in data
        assert "fallback_available" in data

    # Unknown integration should 404
    resp_404 = client.get("/api/v1/integrations/nonexistent")
    assert resp_404.status_code == 404


def test_validate_ai_integration_missing_key():
    """When AI key is missing/unconfigured, verify meaningful error and no fabrication."""
    with patch.object(settings.ai, "gemini_api_key", None), \
         patch.object(settings.ai, "default_provider", "gemini"):
        res = integration_service.validate("ai")
        assert res.is_valid is False
        assert res.status == "unconfigured"
        assert "GEMINI_API_KEY" in res.error
        assert "remediation" in res.model_dump()
        assert res.can_continue_with_arm is True


def test_validate_image_integration_native_ready():
    """Native image provider should report ready with zero external API dependencies."""
    with patch.object(settings.image_provider, "default_provider", "native"):
        res = integration_service.validate("image")
        assert res.is_valid is True
        assert res.status == "ready"
        assert res.can_continue_with_arm is True
        assert "300 DPI" in res.message


def test_validate_image_integration_unsplash_fallback():
    """When external image API is unconfigured, verify fallback is indicated."""
    with patch.object(settings.image_provider, "default_provider", "unsplash"), \
         patch.object(settings.image_provider, "unsplash_access_key", None), \
         patch.object(settings.image_provider, "fallback_to_native", True):
        res = integration_service.validate("image")
        assert res.status == "degraded"
        assert res.fallback_active is True
        assert res.can_continue_with_arm is True
        assert "UNSPLASH_ACCESS_KEY" in res.message


def test_image_acquisition_engine_fallback_behavior():
    """Image acquisition engine should fall back gracefully rather than crash when API key is missing."""
    req = ImageRequirementDTO(
        template_field="image_1",
        section_key="Methodology",
        field_label="Architecture",
        asset_type="architecture_diagram",
        title="Test System",
        description="Test Architecture",
        suggested_prompt="Draw architecture",
        target_dimensions={"width": 800, "height": 500, "dpi": 300},
        acquisition_mode="diagram_engine",
        license_type="CC-BY-4.0",
        attribution="ARM Visual Engine",
    )
    with patch.object(settings.image_provider, "fallback_to_native", True), \
         patch.dict(os.environ, {}, clear=False):
        # Even if unsplash is preferred, missing key will gracefully fall back to native diagram
        img_bytes, mime, src, attr = ImageAcquisitionEngine.acquire_image(
            requirement=req,
            project_title="Cloud Orchestration Engine",
            project_description="Scalable container pipeline",
            preferred_provider="unsplash",
        )
        assert len(img_bytes) > 0
        assert mime == "image/png"
        assert src == "diagram_engine"
        assert "ARM Technical Diagram Engine" in attr


def test_document_integration_validation():
    """Internal document engine reports ready, while Carbone reports unconfigured if no key."""
    # Internal engine check
    with patch.object(settings.document_provider, "default_provider", "internal"):
        res = integration_service.validate("document")
        assert res.is_valid is True
        assert res.status == "ready"
        assert "OpenXML" in res.message

    # Carbone unconfigured check
    with patch.object(settings.document_provider, "default_provider", "carbone"), \
         patch.object(settings.document_provider, "carbone_api_key", None), \
         patch.object(settings.document_provider, "fallback_to_internal", True):
        res_carbone = integration_service.validate("document")
        assert res_carbone.status == "degraded"
        assert res_carbone.fallback_active is True
        assert res_carbone.can_continue_with_arm is True
        assert "CARBONE_API_KEY" in res_carbone.message


def test_canva_integration_unconfigured_error():
    """Optional Canva integration should report unconfigured and reject export without fabricating results."""
    with patch.object(settings.canva, "client_id", None), \
         patch.object(settings.canva, "client_secret", None), \
         patch.object(settings.canva, "api_key", None):
        # Validation endpoint
        val_res = integration_service.validate("canva")
        assert val_res.is_valid is False
        assert val_res.status == "unconfigured"
        assert val_res.can_continue_with_arm is True

        # Export endpoint
        resp = client.post(
            "/api/v1/integrations/canva/export",
            json={"project_id": "proj-123", "design_type": "presentation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unconfigured"
        assert "CANVA_CLIENT_ID" in data["error"]
        assert data["export_url"] is None  # Never fabricates export URL


def test_validate_all_endpoint():
    """Test POST /api/v1/integrations/validate-all returns all 4 validated items."""
    resp = client.post("/api/v1/integrations/validate-all")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 4
    ids = {r["integration_id"] for r in results}
    assert ids == {"ai", "image", "document", "canva"}
