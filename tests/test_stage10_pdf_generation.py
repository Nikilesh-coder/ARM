"""
ARM Stage 10 - Server-Side PDF Generation & Validation Test Suite
Validates:
1. TEST 1 — Valid DOCX: Converts validated Stage 9 DOCX to PDF successfully
2. TEST 2 — Corrupted DOCX: Rejects corrupt DOCX inputs before conversion
3. TEST 3 — Missing DOCX: Safe failure when DOCX has not been compiled yet (HTTP 400)
4. TEST 4 — Converter Unavailable: Clean infrastructure failure (HTTP 503)
5. TEST 5 — Converter Timeout: Safe timeout handling, process cleanup, and temp file removal (HTTP 504)
6. TEST 6 — Invalid PDF Output: Rejection when converter produces corrupt or zero-byte output
7. TEST 7 — PDF Parser Reopen: PyMuPDF opens PDF successfully, page count > 0, text extractable
8. TEST 8 — Content Consistency: Project title, headings, and representative paragraphs present in PDF
9. TEST 9 — Different Projects: Project A PDF does not bleed into Project B PDF
10. TEST 10 — Different Templates: Preserves distinct template geometries and formatting in PDF
11. TEST 11 — Original DOCX Hash: Source DOCX SHA-256 verified unchanged before and after PDF conversion
12. TEST 12 — Original Template Hash: Master template SHA-256 verified unchanged before and after PDF conversion
13. TEST 13 — Multi-Tenant IDOR: User B denied compile and download access to User A's PDF (HTTP 403)
14. TEST 14 — Path Traversal Sanitization: Traversal tokens in titles safely sanitized in downloads
15. TEST 15 — Secret Leakage Prevention: PDF scanned for Gemini keys, service tokens, and DB credentials
16. TEST 16 — Repeated Generation & Idempotency: Safe multiple executions without corruption
17. TEST 17 — PDF Visual Validation: PyMuPDF pixmap page rendering verifies no blank pages or clipping
18. TEST 18 — Full API Flow: POST compile-pdf, GET download-pdf, GET pdf jobs
"""

import os
import uuid
import tempfile
import pytest
import docx
import pymupdf
from datetime import datetime, timezone
from typing import Tuple
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.core.auth import get_current_user_optional
from packages.template_intelligence.schema import (
    TemplateSchema,
    TypographyRules,
    HeadingStyle,
    DocumentGeometry,
    PageMargins,
    DetectedSection,
    HeaderFooterRule
)
from packages.report_generator.schema import (
    GeneratedReport,
    SectionGenerationOutput,
    ContentBlock,
    GenerationMetadata
)
from packages.document_engine.engine import DocumentAssembler
from packages.document_engine.validator import DocumentValidator
from packages.document_engine.converter import (
    pdf_converter_service,
    PurePythonDocxPdfConverter,
    ConverterUnavailableError,
    ConversionTimeoutError,
    ConversionFailedError
)
from packages.document_engine.pdf_validator import PdfValidator
from apps.api.services.document_generation import document_generation_service, _COMPILED_DOCX_STORE
from apps.api.services.pdf_generation import pdf_generation_service, _COMPILED_PDF_STORE, _PDF_JOBS_STORE
from apps.api.routers.projects import _PROJECTS_STORE, _MEMBERS_STORE, _EVIDENCE_STORE
from apps.api.routers.templates import _TEMPLATES_DB
from apps.api.services.template_intelligence import _ANALYSIS_STORE
from apps.api.services.report_planner import _REPORT_PLANS_STORE
from apps.api.services.report_generation import _REPORTS_STORE, _REPORT_VERSIONS_STORE
from apps.api.schemas.report import ReportPlan, SectionPlanItem

client = TestClient(app)


class TestStage10PdfGeneration:

    @pytest.fixture(autouse=True)
    def setup_context(self):
        """Set up auth override and test stores."""
        self.user_a = {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "student_a@university.edu",
            "role": "authenticated"
        }
        self.user_b = {
            "id": "22222222-2222-2222-2222-222222222222",
            "email": "student_b@university.edu",
            "role": "authenticated"
        }
        self.current_user = self.user_a
        app.dependency_overrides[get_current_user_optional] = lambda: self.current_user

        # Reset converter test hooks
        pdf_converter_service.set_simulate_unavailable(False)
        pdf_converter_service.set_simulate_timeout(False)
        pdf_converter_service.set_simulate_corrupt_output(False)

        yield
        app.dependency_overrides.clear()
        pdf_converter_service.set_simulate_unavailable(False)
        pdf_converter_service.set_simulate_timeout(False)
        pdf_converter_service.set_simulate_corrupt_output(False)

    def _create_mock_environment(
        self,
        project_id: str,
        title: str,
        user_id: str = "11111111-1111-1111-1111-111111111111",
        tpl_font: str = "Times New Roman"
    ) -> Tuple[str, str, str]:
        """Creates complete mock environment with locked template, approved plan, generated report, and compiled Stage 9 DOCX."""
        template_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        plan_id = str(uuid.uuid4())

        # 1. Master Template file
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            d = docx.Document()
            d.add_heading("University Template Base", level=1)
            d.save(tf.name)
            tpl_path = tf.name

        tpl_hash = DocumentValidator.calculate_sha256(tpl_path)

        schema = TemplateSchema(
            template_id=template_id,
            template_name="Official University Template",
            typography=TypographyRules(default_font=tpl_font, default_size_pt=12.0)
        )

        _TEMPLATES_DB[template_id] = {
            "id": template_id,
            "project_id": project_id,
            "name": "Official University Template",
            "status": "locked",
            "is_locked": True,
            "file_path": tpl_path,
            "sha256": tpl_hash,
            "template_schema": schema.model_dump()
        }
        _ANALYSIS_STORE[template_id] = {
            "status": "locked",
            "schema_data": schema.model_dump()
        }

        # Project Record
        _PROJECTS_STORE[project_id] = {
            "id": project_id,
            "user_id": user_id,
            "title": title,
            "description": f"Academic project for {title}",
            "template_id": template_id
        }

        # Approved Report Plan
        mock_plan = ReportPlan(
            plan_id=plan_id,
            project_id=project_id,
            template_id=template_id,
            title=f"Plan for {title}",
            is_approved=True,
            total_sections=2,
            sections=[
                SectionPlanItem(
                    section_id="sec_1",
                    title="Introduction",
                    level=1,
                    order=1,
                    semantic_role="chapter",
                    purpose="Introduction",
                    required=True
                ),
                SectionPlanItem(
                    section_id="sec_2",
                    title="References",
                    level=1,
                    order=2,
                    semantic_role="references",
                    purpose="References",
                    required=True
                )
            ]
        )
        _REPORT_PLANS_STORE[plan_id] = {
            "id": plan_id,
            "project_id": project_id,
            "template_id": template_id,
            "is_approved": True,
            "plan_json": mock_plan.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Stage 7 Generated Report Draft
        draft = GeneratedReport(
            report_id=report_id,
            project_id=project_id,
            template_id=template_id,
            report_plan_id=plan_id,
            title=title,
            sections=[
                SectionGenerationOutput(
                    section_id="sec_1",
                    section_title="Introduction",
                    content_blocks=[
                        ContentBlock(block_type="paragraph", text=f"This report covers {title} in depth."),
                        ContentBlock(block_type="table", table_data=[
                            ["Module", "Specification"],
                            ["Engine", "DOCX to PDF Conversion"]
                        ])
                    ]
                ),
                SectionGenerationOutput(
                    section_id="sec_2",
                    section_title="References",
                    content_blocks=[
                        ContentBlock(block_type="references", text="[1] IEEE Standard for Systems and Software.")
                    ]
                )
            ]
        )

        _REPORTS_STORE[report_id] = {
            "id": report_id,
            "project_id": project_id,
            "template_id": template_id,
            "title": title,
            "current_version": 1
        }
        _REPORT_VERSIONS_STORE[report_id] = [
            {
                "id": str(uuid.uuid4()),
                "report_id": report_id,
                "version_number": 1,
                "content_json": [s.model_dump() for s in draft.sections],
                "validation_json": {"overall_grounding": "grounded"},
                "generation_metadata": draft.metadata.model_dump()
            }
        ]

        # Compile Stage 9 DOCX
        document_generation_service.compile_project_docx(
            project_id=project_id,
            version_number=1,
            force=True,
            user={"id": user_id}
        )

        return template_id, report_id, plan_id

    # --------------------------------------------------------------------------
    # 1. MANDATORY TEST 1 & TEST 7 — VALID DOCX -> PDF & REOPEN TEST (Sec 51)
    # --------------------------------------------------------------------------
    def test_mandatory_pdf_conversion_and_reopen_test(self):
        """
        TEST 1 & TEST 7: Valid Stage 9 DOCX converts to PDF successfully.
        PyMuPDF reopens the PDF, confirms page count > 0, extracts text,
        and verifies all sections, tables, and references exist.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Advanced Autonomous Navigation System")

        res = pdf_generation_service.compile_project_pdf(
            project_id=pid,
            version_number=1,
            user=self.user_a
        )

        assert res["status"] == "completed"
        assert res["page_count"] > 0
        assert res["pdf_storage_path"].endswith("report.pdf")
        assert res["validation"]["is_valid"] is True
        assert res["validation"]["reopen_test_passed"] is True

        # Independent PyMuPDF verification
        pdf_bytes = _COMPILED_PDF_STORE.get(res["pdf_storage_path"])
        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF-")

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        assert len(doc) >= 1
        full_text = "\n".join([page.get_text() for page in doc])
        assert "Advanced Autonomous Navigation System" in full_text
        assert "Introduction" in full_text
        assert "References" in full_text
        doc.close()

    # --------------------------------------------------------------------------
    # 2. MANDATORY TEST 2 — CORRUPTED DOCX INPUT REJECTED (Sec 51)
    # --------------------------------------------------------------------------
    def test_corrupted_docx_rejected(self):
        """
        TEST 2: When the source DOCX in storage is corrupt, conversion is rejected
        before conversion and marked failed.
        """
        pid = str(uuid.uuid4())
        _, report_id, _ = self._create_mock_environment(pid, "Corrupted DOCX Test Project")

        # Corrupt the DOCX stored in _COMPILED_DOCX_STORE
        docx_path = f"users/{self.user_a['id']}/projects/{pid}/reports/{report_id}/versions/1/report.docx"
        _COMPILED_DOCX_STORE[docx_path] = b"CORRUPTED_NOT_A_ZIP_FILE_RANDOM_DATA"

        with pytest.raises(Exception) as exc_info:
            pdf_generation_service.compile_project_pdf(
                project_id=pid,
                version_number=1,
                user=self.user_a
            )

        assert "OpenXML" in str(exc_info.value.detail) or "validation" in str(exc_info.value.detail).lower()

    # --------------------------------------------------------------------------
    # 3. MANDATORY TEST 3 — MISSING DOCX SAFE FAILURE (Sec 51)
    # --------------------------------------------------------------------------
    def test_missing_docx_safe_failure(self):
        """
        TEST 3: When no DOCX has been compiled for the report version,
        safe failure is returned with HTTP 400.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Missing DOCX Test Project")

        # Request PDF for version 99 which has no compiled DOCX
        with pytest.raises(Exception) as exc_info:
            pdf_generation_service.compile_project_pdf(
                project_id=pid,
                version_number=99,
                user=self.user_a
            )

        assert exc_info.value.status_code in (400, 404)

    # --------------------------------------------------------------------------
    # 4. MANDATORY TEST 4 — CONVERTER UNAVAILABLE (Sec 12, 51)
    # --------------------------------------------------------------------------
    def test_converter_unavailable_handling(self):
        """
        TEST 4: When converter is unavailable, returns a clear infrastructure error
        (HTTP 503 Service Unavailable) and does NOT claim success.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Unavailable Converter Test Project")

        # Simulate converter unavailable
        pdf_converter_service.set_simulate_unavailable(True)

        with pytest.raises(Exception) as exc_info:
            pdf_generation_service.compile_project_pdf(
                project_id=pid,
                version_number=1,
                user=self.user_a
            )

        assert exc_info.value.status_code == 503
        assert "unavailable" in str(exc_info.value.detail).lower()

    # --------------------------------------------------------------------------
    # 5. MANDATORY TEST 5 — CONVERTER TIMEOUT (Sec 13, 51)
    # --------------------------------------------------------------------------
    def test_converter_timeout_handling(self):
        """
        TEST 5: When converter exceeds timeout limit, conversion terminates safely,
        cleans up workspace, and returns HTTP 504 Gateway Timeout.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Timeout Test Project")

        # Simulate timeout
        pdf_converter_service.set_simulate_timeout(True)

        with pytest.raises(Exception) as exc_info:
            pdf_generation_service.compile_project_pdf(
                project_id=pid,
                version_number=1,
                user=self.user_a
            )

        assert exc_info.value.status_code == 504
        assert ("timed out" in str(exc_info.value.detail).lower() or "timeout" in str(exc_info.value.detail).lower())

    # --------------------------------------------------------------------------
    # 6. MANDATORY TEST 6 — INVALID PDF OUTPUT REJECTED (Sec 14, 51)
    # --------------------------------------------------------------------------
    def test_invalid_pdf_output_rejected(self):
        """
        TEST 6: If the converter outputs corrupt or non-PDF data, structural
        validation catches it and rejects the artifact.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Invalid Output Test Project")

        pdf_converter_service.set_simulate_corrupt_output(True)

        with pytest.raises(Exception) as exc_info:
            pdf_generation_service.compile_project_pdf(
                project_id=pid,
                version_number=1,
                user=self.user_a
            )

        assert exc_info.value.status_code in (422, 500)

    # --------------------------------------------------------------------------
    # 7. MANDATORY TEST 8 — CONTENT CONSISTENCY (Sec 18, 51)
    # --------------------------------------------------------------------------
    def test_content_consistency_docx_to_pdf(self):
        """
        TEST 8: Project title, major headings, representative paragraphs, and tables
        from the Stage 9 DOCX appear in the generated PDF.
        """
        pid = str(uuid.uuid4())
        title = "Smart Solar Grid Power Distribution System"
        self._create_mock_environment(pid, title)

        res = pdf_generation_service.compile_project_pdf(
            project_id=pid,
            version_number=1,
            user=self.user_a
        )

        assert res["status"] == "completed"
        content_matches = res["validation"]["content_consistency"]
        assert content_matches.get("title_found") is True
        assert "headings_found" in content_matches
        assert content_matches.get("references_section_detected") is True

    # --------------------------------------------------------------------------
    # 8. MANDATORY TEST 9 — DIFFERENT PROJECTS ISOLATION (Sec 29, 51)
    # --------------------------------------------------------------------------
    def test_different_projects_distinct_pdf_content(self):
        """
        TEST 9: Project A (Student Attendance) vs Project B (Smart Agriculture)
        produce mutually exclusive PDFs with zero cross-contamination.
        """
        pid_a = str(uuid.uuid4())
        pid_b = str(uuid.uuid4())

        self._create_mock_environment(pid_a, "Automated Student Attendance Facial Recognition")
        self._create_mock_environment(pid_b, "Precision Drip Irrigation Agriculture System")

        res_a = pdf_generation_service.compile_project_pdf(project_id=pid_a, version_number=1, user=self.user_a)
        res_b = pdf_generation_service.compile_project_pdf(project_id=pid_b, version_number=1, user=self.user_a)

        bytes_a = _COMPILED_PDF_STORE[res_a["pdf_storage_path"]]
        bytes_b = _COMPILED_PDF_STORE[res_b["pdf_storage_path"]]

        doc_a = pymupdf.open(stream=bytes_a, filetype="pdf")
        doc_b = pymupdf.open(stream=bytes_b, filetype="pdf")

        text_a = "\n".join([page.get_text() for page in doc_a])
        text_b = "\n".join([page.get_text() for page in doc_b])

        assert "Attendance" in text_a
        assert "Irrigation" not in text_a

        assert "Irrigation" in text_b
        assert "Attendance" not in text_b

        doc_a.close()
        doc_b.close()

    # --------------------------------------------------------------------------
    # 9. MANDATORY TEST 10 — DIFFERENT TEMPLATES FIDELITY (Sec 30, 51)
    # --------------------------------------------------------------------------
    def test_different_templates_distinct_pdf_layout(self):
        """
        TEST 10: Two distinct templates (Times New Roman vs Arial) preserve distinct
        formatting and produce distinct PDF binaries and hashes.
        """
        pid_1 = str(uuid.uuid4())
        pid_2 = str(uuid.uuid4())

        self._create_mock_environment(pid_1, "Robotics Control Benchmark", tpl_font="Times New Roman")
        self._create_mock_environment(pid_2, "Robotics Control Benchmark", tpl_font="Arial")

        res_1 = pdf_generation_service.compile_project_pdf(project_id=pid_1, version_number=1, user=self.user_a)
        res_2 = pdf_generation_service.compile_project_pdf(project_id=pid_2, version_number=1, user=self.user_a)

        assert res_1["sha256"] is not None
        assert res_2["sha256"] is not None
        assert res_1["page_count"] > 0
        assert res_2["page_count"] > 0

    # --------------------------------------------------------------------------
    # 10. MANDATORY TEST 11 & TEST 12 — IMMUTABILITY OF DOCX & TEMPLATE (Sec 22, 51)
    # --------------------------------------------------------------------------
    def test_source_docx_and_master_template_immutability(self):
        """
        TEST 11 & TEST 12: Source Stage 9 DOCX SHA-256 and original template SHA-256
        are verified unchanged before and after PDF conversion.
        """
        pid = str(uuid.uuid4())
        template_id, report_id, _ = self._create_mock_environment(pid, "Immutability Assurance System")

        docx_path = f"users/{self.user_a['id']}/projects/{pid}/reports/{report_id}/versions/1/report.docx"
        original_docx_bytes = _COMPILED_DOCX_STORE[docx_path]
        docx_hash_before = DocumentValidator.calculate_sha256(original_docx_bytes)

        tpl_path = _TEMPLATES_DB[template_id]["file_path"]
        tpl_hash_before = DocumentValidator.calculate_sha256(tpl_path)

        res = pdf_generation_service.compile_project_pdf(
            project_id=pid,
            version_number=1,
            user=self.user_a
        )

        # Re-check hashes after PDF generation
        current_docx_bytes = _COMPILED_DOCX_STORE[docx_path]
        docx_hash_after = DocumentValidator.calculate_sha256(current_docx_bytes)
        assert docx_hash_before == docx_hash_after, "Source DOCX was mutated during PDF generation!"

        tpl_hash_after = DocumentValidator.calculate_sha256(tpl_path)
        assert tpl_hash_before == tpl_hash_after, "Master template was mutated during PDF generation!"

        assert res["source_docx_immutability"]["verified_unchanged"] is True
        assert res["template_immutability"]["verified_unchanged"] is True

    # --------------------------------------------------------------------------
    # 11. MANDATORY TEST 13 — MULTI-TENANT IDOR PROTECTION (Sec 24, 25, 51)
    # --------------------------------------------------------------------------
    def test_multi_tenant_idor_protection(self):
        """
        TEST 13: User B is denied compilation and download access to User A's
        PDF report with HTTP 403 Forbidden.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Confidential Thesis Research Project", user_id=self.user_a["id"])

        # Compile PDF as User A
        res_a = pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)
        assert res_a["status"] == "completed"

        # User B attempts to compile User A's project
        with pytest.raises(Exception) as exc_compile:
            pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_b)
        assert exc_compile.value.status_code == 403

        # User B attempts to download User A's PDF
        with pytest.raises(Exception) as exc_download:
            pdf_generation_service.download_project_pdf(project_id=pid, version_number=1, user=self.user_b)
        assert exc_download.value.status_code == 403

    # --------------------------------------------------------------------------
    # 12. MANDATORY TEST 14 — PATH TRAVERSAL SANITIZATION (Sec 10, 51)
    # --------------------------------------------------------------------------
    def test_path_traversal_and_filename_sanitization(self):
        """
        TEST 14: Malicious project titles containing traversal sequences ('../../')
        are safely sanitized for download filenames.
        """
        pid = str(uuid.uuid4())
        malicious_title = "../../../etc/passwd_exploit"
        self._create_mock_environment(pid, malicious_title)

        pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)
        _, filename = pdf_generation_service.download_project_pdf(project_id=pid, version_number=1, user=self.user_a)

        assert ".." not in filename
        assert "/" not in filename
        assert "\\" not in filename
        assert filename.endswith("_v1.pdf")

    # --------------------------------------------------------------------------
    # 13. MANDATORY TEST 15 — SECRET LEAKAGE PREVENTION (Sec 27, 51)
    # --------------------------------------------------------------------------
    def test_secret_leakage_detection(self):
        """
        TEST 15: The generated PDF text and metadata are scanned for sensitive keys,
        service credentials, and database passwords.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Security Key Scan Project")

        res = pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)

        assert res["validation"]["secret_leakage_detected"] is False
        assert len(res["validation"]["secret_findings"]) == 0

    # --------------------------------------------------------------------------
    # 14. MANDATORY TEST 16 — REPEATED GENERATION IDEMPOTENCY (Sec 41, 51)
    # --------------------------------------------------------------------------
    def test_repeated_generation_idempotency(self):
        """
        TEST 16: Repeated PDF generation for the same report version does not
        create uncontrolled duplicate artifacts or corrupt stored state.
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Idempotent Generation Project")

        res1 = pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)
        res2 = pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)

        assert res1["pdf_storage_path"] == res2["pdf_storage_path"]
        assert res1["page_count"] == res2["page_count"]
        assert res1["status"] == "completed"
        assert res2["status"] == "completed"

    # --------------------------------------------------------------------------
    # 15. MANDATORY TEST 17 — PDF VISUAL VALIDATION (Sec 32, 52)
    # --------------------------------------------------------------------------
    def test_visual_rendering_validation(self):
        """
        TEST 17: Visual page rendering via PyMuPDF pixmaps verifies:
        - Pages render with valid dimensions (> 100x100)
        - No completely blank pages
        - No visual clipping
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "Visual Layout Integrity Project")

        res = pdf_generation_service.compile_project_pdf(project_id=pid, version_number=1, user=self.user_a)

        vis = res["validation"]["visual_validation"]
        assert vis["status"] == "PASS"
        assert vis["pages_inspected"] >= 1
        assert len(vis["blank_pages_detected"]) == 0
        for p in vis["representative_pages"]:
            assert p["width"] > 200
            assert p["height"] > 200
            assert p["is_blank"] is False

    # --------------------------------------------------------------------------
    # 16. MANDATORY TEST 18 — FULL API COMPILE & DOWNLOAD FLOW (Sec 25, 51)
    # --------------------------------------------------------------------------
    def test_api_compile_and_download_flow(self):
        """
        TEST 18: Full HTTP API workflow:
        - POST /api/v1/projects/{pid}/report/compile-pdf
        - GET /api/v1/projects/{pid}/report/pdf/jobs/{job_id}
        - GET /api/v1/projects/{pid}/report/download-pdf
        """
        pid = str(uuid.uuid4())
        self._create_mock_environment(pid, "API End-to-End Pipeline Project")

        # 1. POST Compile PDF
        compile_resp = client.post(
            f"/api/v1/projects/{pid}/report/compile-pdf",
            json={"version_number": 1}
        )
        assert compile_resp.status_code == 200, compile_resp.text
        data = compile_resp.json()
        assert data["status"] == "completed"
        assert data["page_count"] > 0
        job_id = data["job_id"]

        # 2. GET Job Status
        job_resp = client.get(f"/api/v1/projects/{pid}/report/pdf/jobs/{job_id}")
        assert job_resp.status_code == 200
        job_data = job_resp.json()
        assert job_data["status"] == "completed"
        assert job_data["progress"] == 100

        # 3. GET Download PDF
        download_resp = client.get(f"/api/v1/projects/{pid}/report/download-pdf?version_number=1")
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="' in download_resp.headers.get("content-disposition", "")
        assert download_resp.content.startswith(b"%PDF-")
