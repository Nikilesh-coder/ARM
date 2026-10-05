"""
Test Foundation Services: Storage, AI, Document Service, and Error Handling
"""

import tempfile
from pydantic import BaseModel
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.services.storage.local import LocalStorageProvider
from apps.api.services.ai import get_ai_provider
from apps.api.services.document import get_document_service

client = TestClient(app)


class SampleStructuredModel(BaseModel):
    summary: str
    confidence: float


def test_storage_abstraction_local():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageProvider(base_dir=tmp_dir)
        test_data = b"ReportForge AI Sample Evidence Document Content"
        bucket = "evidence"
        file_path = "projects/test_proj/file.txt"

        # 1. Upload
        uri = storage.upload_file(bucket, file_path, test_data)
        assert uri is not None
        assert storage.exists(bucket, file_path) is True

        # 2. Download
        downloaded = storage.download_file(bucket, file_path)
        assert downloaded == test_data

        # 3. Signed URL
        signed_url = storage.get_signed_url(bucket, file_path)
        assert "evidence/projects/test_proj/file.txt" in signed_url

        # 4. Delete
        assert storage.delete_file(bucket, file_path) is True
        assert storage.exists(bucket, file_path) is False


def test_ai_provider_abstraction():
    ai = get_ai_provider()
    assert ai is not None

    # Test text generation
    text = ai.generate_text("Summarize the project problem statement.")
    assert isinstance(text, str)
    assert len(text) > 0

    # Test structured generation
    structured = ai.generate_structured("Generate summary", SampleStructuredModel)
    assert isinstance(structured, SampleStructuredModel)
    assert hasattr(structured, "summary")
    assert hasattr(structured, "confidence")


def test_document_service_abstraction():
    doc_service = get_document_service()
    assert doc_service is not None
    assert hasattr(doc_service, "parse_template")
    assert hasattr(doc_service, "assemble_report")
    assert hasattr(doc_service, "convert_to_pdf")


def test_error_handling_standardized_json():
    # Calling non-existent endpoint
    response = client.get("/api/v1/projects/non_existent_id_999999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "error" in data
