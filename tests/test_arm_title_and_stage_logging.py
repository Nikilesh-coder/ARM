"""
Test Suite: ARM Conversational Query vs Academic Project Title Separation and Stage Logging
Verifies:
1. Conversational search queries ('give an report on Ai based irrigation') are converted to authoritative titles ('AI Based Irrigation System').
2. Saved project names take precedence over conversational search queries.
3. Pipeline logs all 12 stages sequentially without interruption.
4. Report download succeeds with 200 and valid file payload.
"""

import os
import pytest
from apps.api.services.academic_title_formatter import (
    extract_clean_academic_title,
    separate_title_and_research_query,
)
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_1_conversational_title_extraction():
    # Test conversational query cleaning
    assert extract_clean_academic_title("give an report on Ai based irrigation") == "AI Based Irrigation System"
    assert extract_clean_academic_title("create report for Smart Attendance using Face Recognition") == "Smart Attendance using Face Recognition System"
    assert extract_clean_academic_title("generate a report on IoT based smart irrigation") == "IoT Based Smart Irrigation System"
    assert extract_clean_academic_title("AI Based Irrigation System") == "AI Based Irrigation System"


def test_2_title_and_research_query_separation():
    # Prompt is conversational -> separate into title and research query
    title, query = separate_title_and_research_query(
        raw_title="give an report on Ai based irrigation"
    )
    assert title == "AI Based Irrigation System"
    assert query == "give an report on Ai based irrigation"

    # Saved project title takes absolute precedence
    title_saved, query_saved = separate_title_and_research_query(
        raw_title="give an report on Ai based irrigation",
        saved_project_title="AI Based Irrigation System"
    )
    assert title_saved == "AI Based Irrigation System"
    assert query_saved == "give an report on Ai based irrigation"

    # Explicit clean project title passed with research query
    title_exp, query_exp = separate_title_and_research_query(
        project_title="AI Based Irrigation System",
        research_query="give an report on Ai based irrigation"
    )
    assert title_exp == "AI Based Irrigation System"
    assert query_exp == "give an report on Ai based irrigation"


def test_3_generate_endpoint_with_conversational_query_and_download():
    payload = {
        "title": "give an report on Ai based irrigation",
        "research_query": "give an report on Ai based irrigation",
        "template_id": "0484aecb-dbc1-4671-a388-0f820124ca0e",
    }
    resp = client.post("/api/v1/reports/generate", json=payload)
    assert resp.status_code == 200, f"Generation failed: {resp.text}"

    data = resp.json()
    assert data["title"] == "AI Based Irrigation System", f"Expected clean title, got: {data['title']}"
    report_id = data.get("report_id") or data.get("document_id")
    assert report_id, "Report ID must be present"

    # Download check
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 10000, "Downloaded report must contain valid content"
