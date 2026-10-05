"""
ARM Diagnostic Test: Raw Template Copying Validation
Tests that the 'template-copy-test' operation performs ZERO document processing
and produces an exact byte-for-byte copy with identical file size and SHA-256 hash.
"""

import os
import io
import hashlib
import tempfile
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_template_copy_test_endpoint_preserves_exact_bytes():
    """
    Validates:
    1. Uploads original DOCX to /api/v1/templates/template-copy-test
    2. Compares original_uploaded.docx with template-copy-test-output.docx
    3. Asserts file size is IDENTICAL
    4. Asserts SHA-256 hash is IDENTICAL
    """
    # Use existing college template or generate realistic test file
    template_source = os.path.abspath(".storage/templates/master_college_template.docx")
    if not os.path.exists(template_source):
        # Fallback to any docx in storage
        template_source = "tests/test_template_sample.docx"
        os.makedirs(os.path.dirname(template_source), exist_ok=True)
        import docx
        d = docx.Document()
        d.add_paragraph("Sample College Master Template with Borders and Logo")
        d.save(template_source)

    with open(template_source, "rb") as f:
        original_bytes = f.read()

    orig_size = len(original_bytes)
    orig_sha256 = hashlib.sha256(original_bytes).hexdigest()

    response = client.post(
        "/api/v1/templates/template-copy-test",
        files={"file": ("original_uploaded.docx", original_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    assert response.status_code == 200
    copied_bytes = response.content

    copied_size = len(copied_bytes)
    copied_sha256 = hashlib.sha256(copied_bytes).hexdigest()

    # CRITICAL VALIDATION: Hashes and sizes must match 100%
    assert copied_size == orig_size, f"Size changed: original={orig_size}, copied={copied_size}"
    assert copied_sha256 == orig_sha256, f"Hash changed: original={orig_sha256}, copied={copied_sha256}"
    assert response.headers.get("X-Hashes-Match") == "True"
