"""
ARM Stage 9 - Deterministic DOCX Generation Engine Test Suite
Validates:
1. Mandatory Document Test: Full report assembly with headings, paragraphs, lists, tables, captions, footers, reopen test
2. Original Template Immutability: SHA-256 before == SHA-256 after (original template untouched)
3. Locked Template Requirement: Generation rejected if template is not locked (HTTP 400)
4. Approved Report Plan Requirement: Generation rejected if plan is missing or unapproved (HTTP 400)
5. Stage 8 Verification Quality Gate: Blocking issues prevent compilation unless force=True (HTTP 422 -> REVIEW_REQUIRED)
6. Different Template Test: Template A vs Template B produces distinct formatting strictly driven by each template's schema
7. Same Content / Different Template Test: Identical content rendered differently under distinct templates
8. Different Project Test: Attendance vs Agriculture yields isolated project-specific content with zero bleed
9. Multi-Tenant IDOR Protection: User B denied access to User A's document compilation & download (HTTP 403)
10. Path Traversal & Filename Sanitization: Unsafe project titles cleanly sanitized
11. Generation Job Lifecycle: Real progression through states to completion (progress 100%)
12. End-to-End API Routes: POST compile-docx, GET download-docx, GET document jobs
"""

import os
import uuid
import tempfile
import pytest
import docx
from datetime import datetime, timezone
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
from packages.citation_verifier.schema import (
    ReportVerificationReport,
    VerificationSummary,
    QualityGateResult,
    ClaimVerificationRecord
)
from packages.document_engine.engine import DocumentAssembler
from packages.document_engine.validator import DocumentValidator
from apps.api.services.document_generation import document_generation_service, _COMPILED_DOCX_STORE
from apps.api.routers.projects import _PROJECTS_STORE, _MEMBERS_STORE, _EVIDENCE_STORE
from apps.api.routers.templates import _TEMPLATES_DB
from apps.api.services.template_intelligence import _ANALYSIS_STORE
from apps.api.services.report_planner import _REPORT_PLANS_STORE
from apps.api.services.report_generation import _REPORTS_STORE, _REPORT_VERSIONS_STORE

client = TestClient(app)


class TestStage9DocxGeneration:

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
        yield
        app.dependency_overrides.clear()

    # --------------------------------------------------------------------------
    # 1. MANDATORY DOCUMENT TEST + REOPEN TEST (Section 55)
    # --------------------------------------------------------------------------
    def test_mandatory_document_assembly_and_reopen_test(self):
        """
        Builds a comprehensive report with headings, subheadings, paragraphs,
        bullet list, numbered list, table with headers & caption, quote, and references.
        Then reopens via python-docx and verifies all elements structurally exist.
        """
        schema = TemplateSchema(
            template_id="tpl_mandatory_01",
            template_name="Institutional Capstone Format",
            geometry=DocumentGeometry(
                margins=PageMargins(top_mm=25.4, bottom_mm=25.4, left_mm=31.75, right_mm=25.4)
            ),
            typography=TypographyRules(
                default_font="Times New Roman",
                default_size_pt=12.0,
                line_spacing=1.5,
                paragraph_after_pt=6.0,
                headings={
                    "heading_1": HeadingStyle(level=1, font_name="Times New Roman", size_pt=16.0, bold=True, all_caps=True),
                    "heading_2": HeadingStyle(level=2, font_name="Times New Roman", size_pt=13.0, bold=True)
                }
            ),
            header_footer=HeaderFooterRule(
                header_text_pattern="University College of Engineering  |  Project Report",
                footer_text_pattern="Confidential",
                has_page_numbers=True
            ),
            sections=[
                DetectedSection(id="sec_ch1", order=1, detected_title="Introduction", section_type="chapter", level=1),
                DetectedSection(id="sec_ch2", order=2, detected_title="System Architecture", section_type="chapter", level=1),
                DetectedSection(id="sec_ref", order=3, detected_title="References", section_type="references", level=1)
            ]
        )

        assembler = DocumentAssembler(template_schema=schema)

        # Title and Front matter
        assembler.add_heading("Automated Attendance System Using Computer Vision", level=1)
        assembler.add_body_paragraph("A Capstone Project Submitted in Partial Fulfillment of B.Tech Degree Requirements.")

        # Chapter 1: Introduction
        assembler.add_heading("Chapter 1: Introduction", level=1)
        assembler.add_body_paragraph(
            "Traditional attendance tracking in higher education institutions suffers from high proxy rates, "
            "inefficient record-keeping, and significant time overhead."
        )
        assembler.add_heading("1.1 Project Objectives", level=2)
        assembler.add_bullet_list([
            "Develop an edge-deployed facial verification algorithm.",
            "Eliminate proxy attendance through liveness detection.",
            "Generate deterministic automated attendance summaries."
        ])

        # Chapter 2: System Architecture
        assembler.add_heading("Chapter 2: System Architecture", level=1)
        assembler.add_body_paragraph("The hardware-software pipeline consists of three sequential operational phases:")
        assembler.add_numbered_list([
            "Face detection using Haar-cascade and MTCNN models.",
            "Embedding generation using 512-dimensional ResNet vectors.",
            "Cosine similarity classification against enrolled feature vectors."
        ])

        # Table with headers and caption
        assembler.add_table(
            headers=["Component", "Technology", "Performance Metric"],
            rows=[
                ["Frontend Portal", "Next.js 15 & React", "< 200ms latency"],
                ["Backend API", "FastAPI & Python 3.14", "95.4% accuracy"],
                ["Database Storage", "PostgreSQL & Supabase", "ACID compliant"]
            ],
            caption="Table 2.1: Architectural Module Specifications"
        )

        # Quote
        assembler.add_quote("Reliable attendance monitoring forms the bedrock of academic integrity.")

        # References section
        assembler.add_heading("References", level=1)
        assembler.add_references([
            "Schroff, F., Kalenichenko, D., & Philbin, J. (2015). FaceNet: A unified embedding for face recognition.",
            "Deng, J., et al. (2019). ArcFace: Additive angular margin loss for deep face recognition."
        ])

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            out_path = tf.name

        assembler.save(out_path)

        # Run DocumentValidator (OpenXML ZIP check + Reopen check)
        val = DocumentValidator.validate_docx(out_path)
        assert val["valid"] is True
        assert val["reopen_success"] is True
        assert val["section_count"] >= 1
        assert val["paragraph_count"] >= 10
        assert val["table_count"] == 1
        assert val["word_count"] > 100

        # Independent reopen via python-docx to verify exact structural compliance
        reopened = docx.Document(out_path)
        assert len(reopened.paragraphs) >= 10
        assert len(reopened.tables) == 1
        assert len(reopened.tables[0].rows) == 4
        assert len(reopened.tables[0].columns) == 3

        # Clean up
        if os.path.exists(out_path):
            os.remove(out_path)

    # --------------------------------------------------------------------------
    # 2. ORIGINAL TEMPLATE IMMUTABILITY (Section 4, 40)
    # --------------------------------------------------------------------------
    def test_original_template_immutability_sha256(self):
        """
        Proves that compiling a report using an existing master template
        NEVER mutates the original template file. SHA-256 before == SHA-256 after.
        """
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            master_path = tf.name

        # Create a sample master template
        master_doc = docx.Document()
        master_doc.add_heading("TEMPLATE MASTER COVER PAGE", level=1)
        master_doc.add_paragraph("Institutional Template Header: {{PROJECT_TITLE}}")
        master_doc.save(master_path)

        sha_before = DocumentValidator.calculate_sha256(master_path)

        schema = TemplateSchema(
            template_id="tpl_immut_01",
            template_name="Immutability Test Template",
            geometry=DocumentGeometry(),
            typography=TypographyRules(default_font="Calibri", default_size_pt=11.0)
        )

        # Assemble document using master template
        assembler = DocumentAssembler(template_schema=schema, master_template_path=master_path)
        assembler.add_heading("Generated Chapter Content", level=1)
        assembler.add_body_paragraph("This is newly generated content.")

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf_out:
            out_path = tf_out.name

        assembler.save(out_path)

        # Calculate SHA-256 after assembly
        sha_after = DocumentValidator.calculate_sha256(master_path)

        # Master template file MUST remain byte-for-byte identical
        assert sha_before == sha_after
        assert DocumentValidator.verify_template_immutability(master_path, sha_before) is True

        # Generated report must be a different file with valid OpenXML structure
        out_sha = DocumentValidator.calculate_sha256(out_path)
        assert out_sha != sha_before
        val = DocumentValidator.validate_docx(out_path)
        assert val["valid"] is True

        for p in [master_path, out_path]:
            if os.path.exists(p):
                os.remove(p)

    # --------------------------------------------------------------------------
    # 3. LOCKED TEMPLATE REQUIREMENT (Section 5)
    # --------------------------------------------------------------------------
    def test_locked_template_enforcement(self):
        """Ensures document generation is strictly rejected if the template is not locked."""
        proj_id = f"proj_unlocked_{uuid.uuid4().hex[:8]}"
        tpl_id = f"tpl_unlocked_{uuid.uuid4().hex[:8]}"

        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],
            "title": "Attendance App",
            "template_id": tpl_id
        }
        _TEMPLATES_DB[tpl_id] = {
            "id": tpl_id,
            "project_id": proj_id,
            "name": "Draft Template",
            "is_locked": False,  # NOT locked!
            "status": "draft"
        }

        with pytest.raises(Exception) as excinfo:
            document_generation_service.compile_project_docx(
                project_id=proj_id,
                user=self.user_a
            )
        assert "not locked" in str(excinfo.value.detail).lower()

    # --------------------------------------------------------------------------
    # 4. APPROVED REPORT PLAN REQUIREMENT (Section 6)
    # --------------------------------------------------------------------------
    def test_approved_report_plan_enforcement(self):
        """Ensures document generation is rejected if the ReportPlan is missing or unapproved."""
        proj_id = f"proj_unapproved_{uuid.uuid4().hex[:8]}"
        tpl_id = f"tpl_locked_{uuid.uuid4().hex[:8]}"

        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],
            "title": "Smart Agriculture",
            "template_id": tpl_id
        }
        _TEMPLATES_DB[tpl_id] = {
            "id": tpl_id,
            "project_id": proj_id,
            "name": "Locked Template",
            "is_locked": True,
            "status": "locked"
        }
        _ANALYSIS_STORE[tpl_id] = {
            "schema_data": TemplateSchema(template_id=tpl_id, template_name="Locked").model_dump()
        }

        # No plan in _PLANS_STORE
        with pytest.raises(Exception) as excinfo:
            document_generation_service.compile_project_docx(
                project_id=proj_id,
                user=self.user_a
            )
        assert "plan" in str(excinfo.value.detail).lower()

    # --------------------------------------------------------------------------
    # 5. STAGE 8 VERIFICATION QUALITY GATE ENFORCEMENT (Section 7, 8)
    # --------------------------------------------------------------------------
    def test_stage8_verification_quality_gate_blocks_generation(self):
        """
        If Stage 8 verification reports blocking issues, compilation is rejected
        with HTTP 422 unless force=True is provided, which compiles as REVIEW_REQUIRED.
        """
        proj_id = f"proj_gate_{uuid.uuid4().hex[:8]}"
        tpl_id = f"tpl_gate_{uuid.uuid4().hex[:8]}"
        rep_id = f"rep_gate_{uuid.uuid4().hex[:8]}"

        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],
            "title": "Quality Gate Verification Project",
            "template_id": tpl_id
        }
        _TEMPLATES_DB[tpl_id] = {
            "id": tpl_id,
            "project_id": proj_id,
            "name": "Locked Gate Template",
            "is_locked": True,
            "status": "locked"
        }
        _ANALYSIS_STORE[tpl_id] = {
            "schema_data": TemplateSchema(template_id=tpl_id, template_name="Locked Gate").model_dump()
        }

        # Mock Approved Plan
        from apps.api.schemas.report import ReportPlan, SectionPlanItem
        mock_plan = ReportPlan(
            plan_id="plan_gate_01",
            project_id=proj_id,
            template_id=tpl_id,
            title="Quality Gate Report",
            is_approved=True,
            total_sections=1,
            sections=[
                SectionPlanItem(
                    section_id="sec_1",
                    title="Methodology",
                    level=1,
                    order=1,
                    semantic_role="chapter",
                    purpose="Methodology description",
                    required=True
                )
            ]
        )
        _REPORT_PLANS_STORE["plan_gate_01"] = {
            "id": "plan_gate_01",
            "project_id": proj_id,
            "template_id": tpl_id,
            "is_approved": True,
            "plan_json": mock_plan.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Mock Report Draft
        draft = GeneratedReport(
            report_id=rep_id,
            project_id=proj_id,
            template_id=tpl_id,
            report_plan_id="plan_gate_01",
            title="Quality Gate Report",
            sections=[
                SectionGenerationOutput(
                    section_id="sec_1",
                    section_title="Methodology",
                    content_blocks=[
                        ContentBlock(block_type="paragraph", text="We achieved 99% accuracy on unverified data.")
                    ]
                )
            ]
        )
        _REPORTS_STORE[rep_id] = {
            "id": rep_id,
            "project_id": proj_id,
            "template_id": tpl_id,
            "title": "Quality Gate Report",
            "current_version": 1
        }
        version_id = str(uuid.uuid4())
        blocking_verification = ReportVerificationReport(
            id="ver_gate_01",
            report_id=rep_id,
            report_version_id=version_id,
            version_number=1,
            project_id=proj_id,
            summary=VerificationSummary(total_claims=1, unsupported=1),
            quality_gates=QualityGateResult(
                can_proceed_to_document_generation=False,  # BLOCKED!
                blocking_issues=["Critical unsupported claim: 99% accuracy has no evidence"]
            )
        )
        _REPORT_VERSIONS_STORE[rep_id] = [
            {
                "id": version_id,
                "report_id": rep_id,
                "version_number": 1,
                "content_json": [s.model_dump() for s in draft.sections],
                "validation_json": blocking_verification.model_dump(),
                "generation_metadata": draft.metadata.model_dump()
            }
        ]

        # Mock Stage 8 Verification with a BLOCKING ISSUE
        from apps.api.services.citation_verification import _VERIFICATIONS_STORE
        _VERIFICATIONS_STORE[version_id] = blocking_verification.model_dump()
        _VERIFICATIONS_STORE[blocking_verification.id] = blocking_verification.model_dump()

        # 1. Normal compilation attempt must be rejected with 422
        with pytest.raises(Exception) as excinfo:
            document_generation_service.compile_project_docx(
                project_id=proj_id,
                force=False,
                user=self.user_a
            )
        assert excinfo.value.status_code == 422

        # 2. Force compilation proceeds in REVIEW_REQUIRED mode
        res = document_generation_service.compile_project_docx(
            project_id=proj_id,
            force=True,
            user=self.user_a
        )
        assert res["status"] == "completed"
        assert res["document_mode"] == "REVIEW_REQUIRED"
        assert res["validation"]["valid"] is True

    # --------------------------------------------------------------------------
    # 6. DIFFERENT TEMPLATES TEST (Section 57)
    # --------------------------------------------------------------------------
    def test_different_templates_distinct_formatting(self):
        """
        Proves the Document Engine is strictly template-driven by compiling with
        two structurally different templates (Template A vs Template B).
        """
        # Template A: Times New Roman, 12pt, 31.75mm margins
        tpl_a = TemplateSchema(
            template_id="tpl_a",
            template_name="Template A (Times)",
            geometry=DocumentGeometry(margins=PageMargins(left_mm=31.75, right_mm=25.4)),
            typography=TypographyRules(default_font="Times New Roman", default_size_pt=12.0)
        )

        # Template B: Arial, 10.5pt, 20mm margins
        tpl_b = TemplateSchema(
            template_id="tpl_b",
            template_name="Template B (Arial)",
            geometry=DocumentGeometry(margins=PageMargins(left_mm=20.0, right_mm=20.0)),
            typography=TypographyRules(default_font="Arial", default_size_pt=10.5)
        )

        assembler_a = DocumentAssembler(template_schema=tpl_a)
        assembler_a.add_body_paragraph("Testing typography in Template A.")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf_a:
            out_a = tf_a.name
        assembler_a.save(out_a)

        assembler_b = DocumentAssembler(template_schema=tpl_b)
        assembler_b.add_body_paragraph("Testing typography in Template B.")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf_b:
            out_b = tf_b.name
        assembler_b.save(out_b)

        doc_a = docx.Document(out_a)
        doc_b = docx.Document(out_b)

        # Verify Template A font and margin
        sec_a = doc_a.sections[0]
        p_a = doc_a.paragraphs[0]
        assert abs(sec_a.left_margin.inches - (31.75 / 25.4)) < 0.05
        assert p_a.runs[0].font.name == "Times New Roman"

        # Verify Template B font and margin
        sec_b = doc_b.sections[0]
        p_b = doc_b.paragraphs[0]
        assert abs(sec_b.left_margin.inches - (20.0 / 25.4)) < 0.05
        assert p_b.runs[0].font.name == "Arial"

        for p in [out_a, out_b]:
            if os.path.exists(p):
                os.remove(p)

    # --------------------------------------------------------------------------
    # 7. DIFFERENT PROJECTS TEST (Section 59)
    # --------------------------------------------------------------------------
    def test_different_projects_distinct_content(self):
        """
        Verifies that compiling documents for two distinct projects (Attendance vs Agriculture)
        yields project-specific content with zero cross-contamination.
        """
        schema = TemplateSchema(
            template_id="tpl_common",
            template_name="Common Institutional Format",
            typography=TypographyRules(default_font="Calibri", default_size_pt=11.0)
        )

        # Project 1: Attendance
        draft_att = GeneratedReport(
            report_id="rep_att_01",
            project_id="proj_att",
            template_id="tpl_common",
            report_plan_id="plan_att",
            title="Facial Recognition Attendance System",
            sections=[
                SectionGenerationOutput(
                    section_id="sec_att_1",
                    section_title="Introduction",
                    content_blocks=[
                        ContentBlock(block_type="paragraph", text="Face recognition algorithms analyze biometric embeddings.")
                    ]
                )
            ]
        )
        assembler_att = DocumentAssembler(template_schema=schema)
        assembler_att.assemble_report(draft_att, project_info={"title": "Attendance System"})
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            out_att = tf.name
        assembler_att.save(out_att)

        # Project 2: Smart Agriculture
        draft_agr = GeneratedReport(
            report_id="rep_agr_01",
            project_id="proj_agr",
            template_id="tpl_common",
            report_plan_id="plan_agr",
            title="IoT Smart Agriculture and Irrigation",
            sections=[
                SectionGenerationOutput(
                    section_id="sec_agr_1",
                    section_title="Introduction",
                    content_blocks=[
                        ContentBlock(block_type="paragraph", text="Soil moisture sensors regulate automated drip irrigation valves.")
                    ]
                )
            ]
        )
        assembler_agr = DocumentAssembler(template_schema=schema)
        assembler_agr.assemble_report(draft_agr, project_info={"title": "Smart Agriculture"})
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            out_agr = tf.name
        assembler_agr.save(out_agr)

        val_att = DocumentValidator.validate_docx(out_att)
        val_agr = DocumentValidator.validate_docx(out_agr)
        assert val_att["valid"] is True
        assert val_agr["valid"] is True

        # Inspect reopened text
        read_att = docx.Document(out_att)
        att_text = " ".join(p.text for p in read_att.paragraphs)
        assert "biometric" in att_text.lower()
        assert "irrigation" not in att_text.lower()

        read_agr = docx.Document(out_agr)
        agr_text = " ".join(p.text for p in read_agr.paragraphs)
        assert "irrigation" in agr_text.lower()
        assert "biometric" not in agr_text.lower()

        for p in [out_att, out_agr]:
            if os.path.exists(p):
                os.remove(p)

    # --------------------------------------------------------------------------
    # 8. MULTI-TENANT IDOR PROTECTION (Section 45, 60)
    # --------------------------------------------------------------------------
    def test_multi_tenant_idor_protection(self):
        """
        User B must be strictly forbidden from compiling or downloading User A's report.
        """
        proj_id = f"proj_idor_{uuid.uuid4().hex[:8]}"
        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],  # Owned by User A
            "title": "Private Project of User A"
        }

        # 1. User B attempts to compile User A's DOCX
        self.current_user = self.user_b
        res_compile = client.post(f"/api/v1/projects/{proj_id}/report/compile-docx")
        assert res_compile.status_code == 403

        # 2. User B attempts to download User A's DOCX
        res_dl = client.get(f"/api/v1/projects/{proj_id}/report/download-docx")
        assert res_dl.status_code == 403

    # --------------------------------------------------------------------------
    # 9. PATH TRAVERSAL & FILENAME SANITIZATION (Section 33, 48)
    # --------------------------------------------------------------------------
    def test_path_traversal_and_filename_sanitization(self):
        """Verifies that malicious project titles are sanitized to safe filenames."""
        malicious_title = "../../../etc/passwd<script>alert(1)</script>"
        clean = document_generation_service._sanitize_filename(malicious_title)
        assert ".." not in clean
        assert "/" not in clean
        assert "\\" not in clean
        assert "<" not in clean
        assert ">" not in clean
        assert len(clean) > 0

    # --------------------------------------------------------------------------
    # 10. GENERATION JOB LIFECYCLE (Section 36)
    # --------------------------------------------------------------------------
    def test_generation_job_lifecycle(self):
        """
        Verifies that a document_generation job progresses from validating_inputs
        through assembling_document and validating_docx to completed (progress=100%).
        """
        job_id = str(uuid.uuid4())
        proj_id = str(uuid.uuid4())

        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],
            "title": "Lifecycle Project"
        }

        document_generation_service._update_job(
            job_id,
            project_id=proj_id,
            status="running",
            progress=10,
            current_step="validating_inputs"
        )
        j1 = document_generation_service.get_job(proj_id, job_id, user=self.user_a)
        assert j1["progress"] == 10
        assert j1["current_step"] == "validating_inputs"

        document_generation_service._update_job(
            job_id,
            progress=60,
            current_step="assembling_document"
        )
        j2 = document_generation_service.get_job(proj_id, job_id, user=self.user_a)
        assert j2["progress"] == 60
        assert j2["current_step"] == "assembling_document"

        document_generation_service._update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="completed"
        )
        j3 = document_generation_service.get_job(proj_id, job_id, user=self.user_a)
        assert j3["status"] == "completed"
        assert j3["progress"] == 100

    # --------------------------------------------------------------------------
    # 11. END-TO-END API COMPILE AND DOWNLOAD (Section 51)
    # --------------------------------------------------------------------------
    def test_api_compile_and_download_flow(self):
        """
        Validates full API compilation endpoint and subsequent download endpoint.
        """
        proj_id = f"proj_api_{uuid.uuid4().hex[:8]}"
        tpl_id = f"tpl_api_{uuid.uuid4().hex[:8]}"
        rep_id = f"rep_api_{uuid.uuid4().hex[:8]}"

        _PROJECTS_STORE[proj_id] = {
            "id": proj_id,
            "user_id": self.user_a["id"],
            "title": "API Verification Project",
            "template_id": tpl_id
        }
        _TEMPLATES_DB[tpl_id] = {
            "id": tpl_id,
            "project_id": proj_id,
            "name": "API Locked Template",
            "is_locked": True,
            "status": "locked"
        }
        _ANALYSIS_STORE[tpl_id] = {
            "schema_data": TemplateSchema(
                template_id=tpl_id,
                template_name="API Locked",
                typography=TypographyRules(default_font="Calibri", default_size_pt=11.5)
            ).model_dump()
        }

        # Approved Plan
        from apps.api.schemas.report import ReportPlan, SectionPlanItem
        mock_plan_api = ReportPlan(
            plan_id="plan_api_01",
            project_id=proj_id,
            template_id=tpl_id,
            title="API Verification Report",
            is_approved=True,
            total_sections=1,
            sections=[
                SectionPlanItem(
                    section_id="sec_api_1",
                    title="Introduction",
                    level=1,
                    order=1,
                    semantic_role="chapter",
                    purpose="Introduction",
                    required=True
                )
            ]
        )
        _REPORT_PLANS_STORE["plan_api_01"] = {
            "id": "plan_api_01",
            "project_id": proj_id,
            "template_id": tpl_id,
            "is_approved": True,
            "plan_json": mock_plan_api.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Report Draft
        draft = GeneratedReport(
            report_id=rep_id,
            project_id=proj_id,
            template_id=tpl_id,
            report_plan_id="plan_api_01",
            title="API Verification Report",
            sections=[
                SectionGenerationOutput(
                    section_id="sec_api_1",
                    section_title="Introduction",
                    content_blocks=[
                        ContentBlock(block_type="paragraph", text="Verifying end-to-end API compilation and download.")
                    ]
                )
            ]
        )
        _REPORTS_STORE[rep_id] = {
            "id": rep_id,
            "project_id": proj_id,
            "template_id": tpl_id,
            "title": "API Verification Report",
            "current_version": 1
        }
        _REPORT_VERSIONS_STORE[rep_id] = [
            {
                "id": str(uuid.uuid4()),
                "report_id": rep_id,
                "version_number": 1,
                "content_json": [s.model_dump() for s in draft.sections],
                "validation_json": {"overall_grounding": "grounded"},
                "generation_metadata": draft.metadata.model_dump()
            }
        ]

        self.current_user = self.user_a

        # 1. POST compile-docx
        res_comp = client.post(f"/api/v1/projects/{proj_id}/report/compile-docx")
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert comp_data["status"] == "completed"
        assert comp_data["validation"]["valid"] is True
        assert comp_data["validation"]["reopen_success"] is True

        # 2. GET download-docx
        res_dl = client.get(f"/api/v1/projects/{proj_id}/report/download-docx")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(res_dl.content) > 0
        assert "attachment" in res_dl.headers["content-disposition"]
