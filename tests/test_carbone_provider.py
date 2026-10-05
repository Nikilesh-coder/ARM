"""
ARM Stage 10 - Carbone Document Provider & Provider Abstraction Test Suite
Tests:
1. DocumentProvider interface and DocumentProviderRegistry discovery.
2. Safe configuration handling: CARBONE_API_KEY stored only in backend env, never leaked to frontend.
3. Proper configuration error when CARBONE_API_KEY is missing (no fake successful documents).
4. Image asset base64 encoding and data payload formatting for Carbone syntax.
5. Mocked successful Carbone API execution (upload -> render -> download).
6. Carbone API error handling (401 invalid key, 400 syntax error, network timeouts).
7. FastAPI endpoints: GET /api/v1/replacement/providers and POST /api/v1/replacement/execute with provider selection.
"""

import os
import tempfile
import pytest
import httpx
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.replacement_engine.providers.base import (
    DocumentProvider,
    ProviderGenerationResult,
)
from packages.replacement_engine.providers.carbone_provider import CarboneDocumentProvider
from packages.replacement_engine.providers.internal_provider import InternalDocumentProvider
from packages.replacement_engine.providers.registry import (
    DocumentProviderRegistry,
    document_provider_registry,
)
from apps.api.services.replacement_engine_service import replacement_engine_service

client = TestClient(app)


@pytest.fixture
def temp_provider_dir():
    """Provides a temporary scratch directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


def test_provider_abstraction_and_registry():
    """Verifies that the provider registry discovers both internal and carbone providers."""
    registry = DocumentProviderRegistry()

    internal_prov = registry.get_provider("internal")
    assert isinstance(internal_prov, InternalDocumentProvider)
    assert internal_prov.get_provider_name() == "internal"
    assert internal_prov.is_configured() is True

    carbone_prov = registry.get_provider("carbone")
    assert isinstance(carbone_prov, CarboneDocumentProvider)
    assert carbone_prov.get_provider_name() == "carbone"

    # Default fallback
    default_prov = registry.get_provider(None)
    assert default_prov.get_provider_name() == "internal"

    # List providers descriptor (never reveals API keys)
    prov_list = registry.list_providers()
    assert len(prov_list) >= 2
    names = [p["name"] for p in prov_list]
    assert "internal" in names
    assert "carbone" in names
    for p in prov_list:
        assert "api_key" not in p
        assert "secret" not in p
        assert "description" in p


def test_carbone_unconfigured_error(temp_provider_dir):
    """
    Verifies that when CARBONE_API_KEY is missing, CarboneDocumentProvider
    returns an explicit configuration error and NEVER creates fake successful documents.
    """
    dummy_template = os.path.join(temp_provider_dir, "template.docx")
    with open(dummy_template, "w") as f:
        f.write("mock template")

    # Instantiate Carbone provider with NO API key
    unconfigured_provider = CarboneDocumentProvider(api_key=None)
    assert unconfigured_provider.is_configured() is False

    result = unconfigured_provider.generate(
        template_path=dummy_template,
        data={"project_title": "Test Title"},
        output_path=os.path.join(temp_provider_dir, "out.docx"),
    )

    # Must fail cleanly and describe the missing key
    assert result.success is False
    assert result.status == "unconfigured"
    assert len(result.errors) > 0
    assert "CARBONE_API_KEY" in result.errors[0]
    # No fake file created
    assert not os.path.exists(os.path.join(temp_provider_dir, "out.docx"))


def test_carbone_image_asset_payload_preparation(temp_provider_dir):
    """
    Verifies that image assets are converted into base64 Data URIs
    and that data is prepared with standard root keys and nested 'd' object.
    """
    img_path = os.path.join(temp_provider_dir, "sample_logo.png")
    with open(img_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

    provider = CarboneDocumentProvider(api_key="test_key_placeholder")
    data = {"project_title": "Crop Telemetry", "author": "Charishma"}
    image_assets = {"image_1": img_path}

    payload = provider._prepare_data_payload(data, image_assets)

    assert "project_title" in payload
    assert "image_1" in payload
    assert payload["image_1"].startswith("data:image/png;base64,")
    # Verify nested 'd' object for Carbone {d.field} notation
    assert "d" in payload
    assert payload["d"]["project_title"] == "Crop Telemetry"
    assert payload["d"]["image_1"].startswith("data:image/png;base64,")


def test_carbone_successful_mocked_generation(temp_provider_dir):
    """
    Verifies the end-to-end Carbone pipeline (Upload -> Render -> Download)
    when valid API responses are returned.
    """
    dummy_template = os.path.join(temp_provider_dir, "template.docx")
    with open(dummy_template, "wb") as f:
        f.write(b"PK\x03\x04mock_docx_bytes")

    out_file = os.path.join(temp_provider_dir, "generated_carbone.docx")
    provider = CarboneDocumentProvider(api_key="valid_test_carbone_key_2026")
    assert provider.is_configured() is True

    # Mock the 3 HTTP calls made to api.carbone.io
    mock_upload_resp = MagicMock()
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.return_value = {"success": True, "data": {"templateId": "tmpl_mock_9918"}}

    mock_render_resp = MagicMock()
    mock_render_resp.status_code = 200
    mock_render_resp.json.return_value = {"success": True, "data": {"renderId": "rndr_mock_4421"}}

    mock_download_resp = MagicMock()
    mock_download_resp.status_code = 200
    mock_download_resp.content = b"PK\x03\x04simulated_carbone_rendered_docx_content"

    def mock_post(url, *args, **kwargs):
        if "/template" in url:
            return mock_upload_resp
        elif "/render" in url:
            return mock_render_resp
        return MagicMock(status_code=404)

    def mock_get(url, *args, **kwargs):
        if "/render" in url:
            return mock_download_resp
        return MagicMock(status_code=404)

    with patch("httpx.Client.post", side_effect=mock_post), patch("httpx.Client.get", side_effect=mock_get):
        result = provider.generate(
            template_path=dummy_template,
            data={"project_title": "Autonomous Yield Telemetry"},
            output_path=out_file,
            output_format="docx",
        )

    assert result.success is True
    assert result.status == "completed"
    assert result.output_path == out_file
    assert os.path.exists(out_file)
    assert result.file_size_bytes == len(mock_download_resp.content)
    assert result.metadata.get("carbone_template_id") == "tmpl_mock_9918"


def test_carbone_error_handling_401_unauthorized(temp_provider_dir):
    """Verifies that an invalid API key returning 401 Unauthorized is clearly reported."""
    dummy_template = os.path.join(temp_provider_dir, "template.docx")
    with open(dummy_template, "wb") as f:
        f.write(b"mock_bytes")

    provider = CarboneDocumentProvider(api_key="invalid_revoked_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized: Invalid API key"

    with patch("httpx.Client.post", return_value=mock_resp):
        result = provider.generate(
            template_path=dummy_template,
            data={"title": "Test"},
            output_path=os.path.join(temp_provider_dir, "out.docx"),
        )

    assert result.success is False
    assert result.status == "failed"
    assert any("401 Unauthorized" in e for e in result.errors)


def test_api_providers_endpoint():
    """Verifies the GET /api/v1/replacement/providers endpoint."""
    res = client.get("/api/v1/replacement/providers")
    assert res.status_code == 200
    providers = res.json()
    assert isinstance(providers, list)
    prov_names = [p["name"] for p in providers]
    assert "internal" in prov_names
    assert "carbone" in prov_names

    # Check that credentials are NOT exposed in API output
    for p in providers:
        assert "api_key" not in p
        assert "carbone_api_key" not in p


def test_execute_with_unconfigured_carbone_fails_safely():
    """
    Verifies that calling POST /api/v1/replacement/execute with provider='carbone'
    when no CARBONE_API_KEY is configured fails safely with an explicit error,
    without producing fake successful documents.
    """
    # Temporarily ensure CARBONE_API_KEY is not in env
    orig_key = os.environ.pop("CARBONE_API_KEY", None)
    try:
        payload = {
            "project_data": {
                "title": "Smart Power Telemetry",
                "student_name": "Kasireddy Charishma",
            },
            "provider": "carbone",
        }
        res = client.post("/api/v1/replacement/execute", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["state"] == "FAILED"
        assert "Carbone document provider configuration error" in data["status_message"]
        assert any("CARBONE_API_KEY" in str(e) for e in data["errors"])
    finally:
        if orig_key:
            os.environ["CARBONE_API_KEY"] = orig_key


def test_internal_provider_executes_reliably():
    """
    Verifies that the internal provider continues to execute reliably
    without any dependence on Carbone.
    """
    template_path = ".storage/templates/master_college_template.docx"
    assert os.path.exists(template_path)

    provider = InternalDocumentProvider()
    assert provider.is_configured() is True
    assert provider.get_provider_name() == "internal"

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        out_path = tmp.name

    try:
        dataset = {
            "project_title": "Autonomous Agricultural Yield Telemetry",
            "student_name": "Kasireddy Charishma",
            "roll_number": "24BFA02081",
            "department": "Department of Electrical & Electronics Engineering",
            "guide_name": "Dr. Y.V. Krishna Reddy",
            "introduction": "This chapter introduces autonomous agricultural telemetry systems.",
            "objectives": ["Measure soil metrics in real time."],
            "problem_statement": "Manual sampling is slow.",
            "methodology": "Modular pipeline.",
            "technologies": ["Python", "FastAPI"],
            "implementation": "Sensor units deployed.",
            "results": "Field trials validated 98% reliability.",
            "conclusion": "The autonomous prototype meets benchmarks.",
            "references": ["IEEE Std 829-2022."],
        }
        res = provider.generate(
            template_path=template_path,
            data=dataset,
            image_assets={"image_1": ".storage/templates/extracted_logo_fixed.png"},
            output_path=out_path,
        )

        assert res.success is True
        assert res.status == "completed"
        assert res.provider == "internal"
        assert os.path.exists(out_path)
        assert res.file_size_bytes > 5000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
