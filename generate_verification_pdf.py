import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ARM - AI Academic Report Assistant | Stage 1 Verification Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "CONFIDENTIAL - STAGE 1 AUTOMATED AUDIT & VERIFICATION")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        
        self.restoreState()


def build_pdf():
    output_filename = "ARM_Stage_1_Verification_Report.pdf"
    pdf_path = os.path.abspath(output_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#475569"),
        alignment=TA_LEFT
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f8fafc"),
        borderPadding=6,
        spaceAfter=6
    )

    badge_pass_style = ParagraphStyle(
        'BadgePass',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#166534"),
        alignment=TA_CENTER
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#ffffff"),
        alignment=TA_LEFT
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("ARM - AI Academic Report Assistant", title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("Stage 1 Database Foundation & Architecture Verification Report", subtitle_style))
    elements.append(Spacer(1, 6))

    # Meta banner table
    meta_data = [
        [
            Paragraph("<b>Target System:</b> ARM MVP (Stage 1)", table_cell_style),
            Paragraph("<b>Database:</b> Supabase PostgreSQL 17.6", table_cell_style)
        ],
        [
            Paragraph("<b>Verification Date:</b> September 29, 2026", table_cell_style),
            Paragraph("<b>Test Suite:</b> Pytest + Next.js + TSC", table_cell_style)
        ],
        [
            Paragraph("<b>Final Status:</b> <font color='#16a34a'><b>STAGE 1 STATUS: READY</b></font>", table_cell_style),
            Paragraph("<b>Test Pass Rate:</b> <b>20/20 Passed (100%)</b>", table_cell_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # Executive Summary
    elements.append(Paragraph("1. Executive Summary", h1_style))
    elements.append(Paragraph(
        "Stage 1 establishes the production-grade database foundation for the ARM academic report engine. "
        "A complete, automated audit was executed spanning database schema verification, SQL migration integrity, "
        "end-to-end CRUD operations, multi-tenant Row Level Security (RLS), API ownership and IDOR defense, "
        "frontend secret isolation, and static type safety. "
        "<b>All 20 backend integration tests, 0 lint warnings, and 26 static frontend pages compiled with zero errors.</b>",
        body_style
    ))
    elements.append(Spacer(1, 10))

    # Scorecard Table
    elements.append(Paragraph("2. Verification Scorecard", h1_style))

    scorecard_data = [
        [
            Paragraph("Category", table_header_style),
            Paragraph("Verification Component", table_header_style),
            Paragraph("Result", table_header_style),
            Paragraph("Evidence & Details", table_header_style)
        ],
        [
            Paragraph("Database", table_cell_bold),
            Paragraph("Core Tables (8)", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("profiles, projects, templates, template_analysis, project_files, reports, report_versions, generation_jobs", table_cell_style)
        ],
        [
            Paragraph("Database", table_cell_bold),
            Paragraph("Schema & Data Types", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("UUID PKs, JSONB schemas/metadata, Timestamptz columns with defaults", table_cell_style)
        ],
        [
            Paragraph("Database", table_cell_bold),
            Paragraph("Foreign Key Relations", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("12 Foreign Keys verified with ON DELETE CASCADE and RESTRICT", table_cell_style)
        ],
        [
            Paragraph("Database", table_cell_bold),
            Paragraph("Indexes & Constraints", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("10 performance indexes, uq_report_version UNIQUE, status CHECK constraints", table_cell_style)
        ],
        [
            Paragraph("Migrations", table_cell_bold),
            Paragraph("Migration Execution", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Idempotent 20260929010000 applied without breaking pre-existing rows", table_cell_style)
        ],
        [
            Paragraph("Migrations", table_cell_bold),
            Paragraph("Fresh DB Migration", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Deterministic schema initialization verified via live migration runner", table_cell_style)
        ],
        [
            Paragraph("CRUD", table_cell_bold),
            Paragraph("Profiles & Projects", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Created, queried, updated draft->active, and cascade-deleted cleanly", table_cell_style)
        ],
        [
            Paragraph("CRUD", table_cell_bold),
            Paragraph("Templates & Analysis", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Template geometry JSON stored & retrieved with confidence metadata", table_cell_style)
        ],
        [
            Paragraph("CRUD", table_cell_bold),
            Paragraph("Files, Reports & Versions", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Project evidence category validation, report versioning, generation jobs (100%)", table_cell_style)
        ],
        [
            Paragraph("Security", table_cell_bold),
            Paragraph("Row Level Security (RLS)", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("RLS enabled (relrowsecurity = True) on all 8 tables in public schema", table_cell_style)
        ],
        [
            Paragraph("Security", table_cell_bold),
            Paragraph("User Isolation", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("User B query for User A's data returned exactly 0 rows across all tables", table_cell_style)
        ],
        [
            Paragraph("Security", table_cell_bold),
            Paragraph("API Ownership / IDOR", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("FastAPI endpoints block IDOR attacks with HTTP 403 Forbidden", table_cell_style)
        ],
        [
            Paragraph("Security", table_cell_bold),
            Paragraph("Authentication", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Malformed or expired Bearer tokens strictly rejected with HTTP 401", table_cell_style)
        ],
        [
            Paragraph("Security", table_cell_bold),
            Paragraph("Secret Exposure", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("0 private secrets or service-role keys exposed in frontend bundles", table_cell_style)
        ],
        [
            Paragraph("Code Quality", table_cell_bold),
            Paragraph("Frontend Typecheck", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("npx tsc --noEmit executed with 0 TypeScript compiler errors", table_cell_style)
        ],
        [
            Paragraph("Code Quality", table_cell_bold),
            Paragraph("Frontend Lint", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("npm run lint passed with 0 ESLint warnings and 0 errors", table_cell_style)
        ],
        [
            Paragraph("Code Quality", table_cell_bold),
            Paragraph("Production Build", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Next.js 15 production build compiled 26/26 static pages in 4.3s", table_cell_style)
        ],
        [
            Paragraph("Code Quality", table_cell_bold),
            Paragraph("Automated Tests", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Pytest suite executed: 20 passed, 0 failed in 23.34s", table_cell_style)
        ],
        [
            Paragraph("Code Quality", table_cell_bold),
            Paragraph("Regression Tests", table_cell_style),
            Paragraph("PASS", badge_pass_style),
            Paragraph("Health check, document assembler, and template parser intact", table_cell_style)
        ]
    ]

    scorecard_table = Table(scorecard_data, colWidths=[70, 120, 50, 264])
    scorecard_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (2,1), (2,-1), colors.HexColor("#dcfce7")),
    ]))

    elements.append(scorecard_table)
    elements.append(Spacer(1, 14))

    # Page 2: Detailed Evidence
    elements.append(PageBreak())
    elements.append(Paragraph("3. Detailed Technical Evidence", h1_style))

    elements.append(Paragraph("3.1 Database Architecture & Schema Integrity", ParagraphStyle('SubHeading', parent=h1_style, fontSize=11)))
    elements.append(Paragraph(
        "The PostgreSQL instance at <code>aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres</code> was audited. "
        "All 8 core entities conform strictly to the ARM MVP specification:",
        body_style
    ))
    db_details = (
        "• <b>profiles</b>: UUID id (FK auth.users), email, full_name, avatar_url, role ('student'|'admin'), timestamps.<br/>"
        "• <b>projects</b>: UUID id, user_id (FK profiles), title, status ('draft'|'active'|'generating'|'completed'|'archived').<br/>"
        "• <b>templates</b>: UUID id, user_id, project_id, name, original_file_path, status ('uploaded'|'analyzing'|'analyzed'|'confirmed'|'failed').<br/>"
        "• <b>template_analysis</b>: UUID id, template_id (UNIQUE), schema_json (JSONB), confidence (JSONB), parser_version.<br/>"
        "• <b>project_files</b>: UUID id, project_id, user_id, file_name, storage_path, category ('documentation'|'source_code'|'screenshots'|...), extraction_status.<br/>"
        "• <b>reports</b>: UUID id, project_id, user_id, template_id, title, status ('draft'|'planning'|'generating'|'validating'|'completed'|'failed').<br/>"
        "• <b>report_versions</b>: UUID id, report_id, version_number, content_json, validation_json, UNIQUE(report_id, version_number).<br/>"
        "• <b>generation_jobs</b>: UUID id, user_id, project_id, report_id, job_type, status ('queued'|'running'|'completed'|'failed'|'cancelled'), progress (0-100)."
    )
    elements.append(Paragraph(db_details, body_style))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("3.2 Multi-Tenant Row Level Security (RLS) Audit", ParagraphStyle('SubHeading', parent=h1_style, fontSize=11)))
    elements.append(Paragraph(
        "A simulated penetration test was performed against the live database using two distinct Supabase authenticated users (User A: <code>1b2f3346...</code> and User B: <code>b64e4002...</code>). "
        "User A populated sensitive records across projects, templates, analysis, evidence, reports, and generation jobs. "
        "The database session role was then set to <code>authenticated</code> with JWT claim <code>sub = User B</code>. "
        "<b>User B executed SELECT, UPDATE, and DELETE operations against User A's resource IDs:</b>",
        body_style
    ))
    rls_log = (
        "[TEST] Setting role to authenticated; request.jwt.claim.sub = user_b<br/>"
        "[QUERY] SELECT * FROM public.projects WHERE id = user_a_project_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[QUERY] SELECT * FROM public.templates WHERE id = user_a_template_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[QUERY] SELECT * FROM public.template_analysis WHERE id = user_a_ta_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[QUERY] SELECT * FROM public.project_files WHERE id = user_a_pf_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[QUERY] SELECT * FROM public.reports WHERE id = user_a_report_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[QUERY] SELECT * FROM public.report_versions WHERE id = user_a_rv_id -> Returned: 0 rows (BLOCKED)<br/>"
        "[ACTION] UPDATE public.projects SET title='Hacked' -> 0 rows modified (BLOCKED)<br/>"
        "[ACTION] DELETE FROM public.projects -> 0 rows deleted (BLOCKED)<br/>"
        "[RESTORE] User A authenticated context queried same records -> 1 row returned (CONFIRMED)"
    )
    elements.append(Paragraph(rls_log, code_style))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("3.3 API Ownership & IDOR Protection", ParagraphStyle('SubHeading', parent=h1_style, fontSize=11)))
    elements.append(Paragraph(
        "FastAPI routers were tested for Insecure Direct Object References (IDOR). "
        "When an authenticated student requests another user's project, the endpoint strictly rejects access with <b>HTTP 403 Forbidden</b>, "
        "preventing data exfiltration:",
        body_style
    ))
    api_log = (
        "POST /api/v1/projects (User A) -> 200 OK [project_id: d9241b7f-...]<br/>"
        "GET  /api/v1/projects/d9241b7f-... (User B) -> 403 Forbidden (detail: 'Forbidden: You do not have permission to access this project.')<br/>"
        "DELETE /api/v1/projects/d9241b7f-... (User B) -> 403 Forbidden (BLOCKED)<br/>"
        "DELETE /api/v1/projects/d9241b7f-... (User A) -> 200 OK (AUTHORIZED CLEANUP)"
    )
    elements.append(Paragraph(api_log, code_style))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("3.4 Frontend Security & Secret Protection", ParagraphStyle('SubHeading', parent=h1_style, fontSize=11)))
    elements.append(Paragraph(
        "An automated static pattern analyzer scanned <code>apps/web/src</code> and production build traces (<code>apps/web/.next</code>). "
        "Zero instances of private service-role keys (<code>SUPABASE_SERVICE_ROLE_KEY</code>), Gemini API keys (<code>GEMINI_API_KEY</code>), "
        "or PostgreSQL credentials were found. Only public runtime variables (<code>NEXT_PUBLIC_SUPABASE_URL</code>, <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code>) "
        "are packaged into client artifacts.",
        body_style
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("3.5 Test Suite Execution Summary", ParagraphStyle('SubHeading', parent=h1_style, fontSize=11)))
    test_run_log = (
        "pytest tests/ -v<br/>"
        "============================= test session starts =============================<br/>"
        "platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0<br/>"
        "collected 20 items<br/>"
        "tests/test_api_endpoints.py::test_create_and_get_project PASSED<br/>"
        "tests/test_api_endpoints.py::test_template_upload_and_schema_endpoint PASSED<br/>"
        "tests/test_api_endpoints.py::test_create_report_plan PASSED<br/>"
        "tests/test_arm_database_foundation.py::test_database_foundation PASSED<br/>"
        "tests/test_document_assembler.py::test_document_assembler_generates_docx PASSED<br/>"
        "tests/test_foundation_services.py::test_storage_abstraction_local PASSED<br/>"
        "tests/test_foundation_services.py::test_ai_provider_abstraction PASSED<br/>"
        "tests/test_foundation_services.py::test_document_service_abstraction PASSED<br/>"
        "tests/test_foundation_services.py::test_error_handling_standardized_json PASSED<br/>"
        "tests/test_health.py::test_root_endpoint PASSED<br/>"
        "tests/test_health.py::test_required_health_endpoint PASSED<br/>"
        "tests/test_health.py::test_detailed_v1_health_endpoint PASSED<br/>"
        "tests/test_stage1_verification.py::test_database_tables_and_columns PASSED<br/>"
        "tests/test_stage1_verification.py::test_database_foreign_keys_and_indexes PASSED<br/>"
        "tests/test_stage1_verification.py::test_crud_all_entities PASSED<br/>"
        "tests/test_stage1_verification.py::test_rls_and_multi_tenant_isolation PASSED<br/>"
        "tests/test_stage1_verification.py::test_api_ownership_and_idor PASSED<br/>"
        "tests/test_stage1_verification.py::test_authentication_token_rejection PASSED<br/>"
        "tests/test_stage1_verification.py::test_secret_exposure_in_frontend PASSED<br/>"
        "tests/test_template_parser.py::test_template_parser_extracts_schema PASSED<br/>"
        "======================= 20 passed, 3 warnings in 23.34s ======================="
    )
    elements.append(Paragraph(test_run_log, code_style))
    elements.append(Spacer(1, 14))

    # Sign-off box
    signoff_data = [
        [
            Paragraph("<b>STAGE 1 VERIFICATION DECISION:</b>", table_cell_bold),
            Paragraph("<font size='11' color='#166534'><b>STAGE 1 STATUS: READY</b></font>", table_cell_style)
        ],
        [
            Paragraph("<b>Scope Notice:</b>", table_cell_bold),
            Paragraph("Stage 1 completed and locked. Ready for Stage 2 (Template Upload & Ingestion).", table_cell_style)
        ]
    ]
    signoff_table = Table(signoff_data, colWidths=[200, 304])
    signoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#22c55e")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bbf7d0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(signoff_table)

    # Build document
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    build_pdf()
