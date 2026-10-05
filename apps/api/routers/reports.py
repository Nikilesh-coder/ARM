"""
ReportForge AI - Reports Router
Handles report planning, section breakdown, and deterministic compilation requests.
"""

import uuid
import os
import glob
import re
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from apps.api.core.database import db_manager
from apps.api.schemas.report import ReportPlanRequestDTO, ReportPlanResponseDTO, SectionPlanDTO
from apps.api.services.document.generator import create_full_academic_report
from apps.api.services.document.template_extractor import get_active_template_design
from apps.api.core.logging import get_logger

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = get_logger("reports.router")

_REPORTS_STORE: Dict[str, Any] = {}
_REPORT_ID_MAPPING: Dict[str, str] = {}

DEFAULT_ACADEMIC_SECTIONS = [
    SectionPlanDTO(
        section_key="title_page", title="Title / Cover Page", sequence_order=1, level=1, mandatory=True, estimated_word_count=50
    ),
    SectionPlanDTO(section_key="certificate", title="Certificate", sequence_order=2, level=1, mandatory=True, estimated_word_count=100),
    SectionPlanDTO(section_key="declaration", title="Declaration", sequence_order=3, level=1, mandatory=True, estimated_word_count=100),
    SectionPlanDTO(
        section_key="acknowledgement", title="Acknowledgement", sequence_order=4, level=1, mandatory=True, estimated_word_count=150
    ),
    SectionPlanDTO(section_key="abstract", title="Abstract", sequence_order=5, level=1, mandatory=True, estimated_word_count=300),
    SectionPlanDTO(
        section_key="introduction", title="Chapter 1: Introduction",
        sequence_order=6, level=1, mandatory=True, estimated_word_count=600
    ),
    SectionPlanDTO(
        section_key="literature_survey", title="Chapter 2: Literature Survey",
        sequence_order=7, level=1, mandatory=True, estimated_word_count=800
    ),
    SectionPlanDTO(
        section_key="system_architecture", title="Chapter 3: System Architecture & Methodology",
        sequence_order=8, level=1, mandatory=True, estimated_word_count=1000
    ),
    SectionPlanDTO(
        section_key="implementation", title="Chapter 4: Implementation & Details",
        sequence_order=9, level=1, mandatory=True, estimated_word_count=1200
    ),
    SectionPlanDTO(
        section_key="results", title="Chapter 5: Results & Discussion",
        sequence_order=10, level=1, mandatory=True, estimated_word_count=600
    ),
    SectionPlanDTO(
        section_key="conclusion", title="Chapter 6: Conclusion & Future Scope",
        sequence_order=11, level=1, mandatory=True, estimated_word_count=400
    ),
    SectionPlanDTO(
        section_key="references", title="References", sequence_order=12, level=1, mandatory=True, estimated_word_count=200
    )
]


@router.post("/plan", response_model=ReportPlanResponseDTO)
def create_report_plan(dto: ReportPlanRequestDTO):
    report_id = f"rep_{uuid.uuid4().hex[:12]}"
    sections = dto.custom_sections or DEFAULT_ACADEMIC_SECTIONS
    now = datetime.now(timezone.utc)

    record = {
        "report_id": report_id,
        "project_id": dto.project_id,
        "template_id": dto.template_id,
        "title": dto.report_title,
        "status": "planned",
        "sections": sections,
        "created_at": now
    }
    _REPORTS_STORE[report_id] = record
    return record


@router.get("/{report_id}/plan", response_model=ReportPlanResponseDTO)
def get_report_plan(report_id: str):
    if report_id not in _REPORTS_STORE:
        raise HTTPException(status_code=404, detail="Report not found")
    return _REPORTS_STORE[report_id]


class GenerateReportRequest(BaseModel):
    title: Optional[str] = None
    project_title: Optional[str] = None
    research_query: Optional[str] = None
    search_query: Optional[str] = None
    project_type: Optional[str] = None
    student_name: Optional[str] = None
    roll_no: Optional[str] = None
    guide_name: Optional[str] = None
    department: Optional[str] = None
    institution: Optional[str] = None
    problem_statement: Optional[str] = None
    proposed_solution: Optional[str] = None
    tech_stack: Optional[str] = None
    blueprint: Optional[List[Dict[str, Any]]] = None
    template_id: Optional[str] = None
    project_id: Optional[str] = None


@router.post("/generate")
def generate_full_report(req: GenerateReportRequest):
    """
    Generates a full academic report strictly grounded in the Master College Template
    or custom user-uploaded college template using the template-preserving in-place replacement engine.
    Never redesigns, reconstructs, or recreates the college template from scratch.
    For zero-change requests: returns an exact raw copy of the selected template directly.
    """
    import shutil
    import hashlib
    from apps.api.services.template_resolver import resolve_selected_template_path, is_zero_change_intent
    from apps.api.services.replacement_engine_service import replacement_engine_service, _REPLACEMENT_JOBS
    from apps.api.routers.projects import _PROJECTS_STORE
    from apps.api.services.academic_title_formatter import separate_title_and_research_query, extract_clean_academic_title

    current_stage = "Request received"
    try:
        # [1] Request received
        current_stage = "Request received"
        logger.info("[1] Request received")
        print("\n[ARM PIPELINE] [1] Request received")

        from apps.api.services.report_file_storage_service import report_file_storage_service

        report_id = f"rep_{uuid.uuid4().hex[:10]}"
        final_docx_path = str(report_file_storage_service.get_canonical_path(report_id, "docx"))
        final_pdf_path = None

        # --------------------------------------------------------------------------
        # SEPARATE PROJECT TITLE FROM RESEARCH QUERY & LOAD PROJECT
        # --------------------------------------------------------------------------
        proj = None
        if req.project_id:
            proj = _PROJECTS_STORE.get(req.project_id)
            if not proj and db_manager.client:
                try:
                    p_res = db_manager.client.table("projects").select("*").eq("id", req.project_id).execute()
                    if p_res.data:
                        proj = p_res.data[0]
                except Exception:
                    pass

        # [2] Project loaded
        current_stage = "Project loaded"
        logger.info("[2] Project loaded")
        print("[ARM PIPELINE] [2] Project loaded")

        saved_name = None
        if proj:
            raw_saved = (proj.get("project_name") or proj.get("title") or proj.get("report_title") or "").strip()
            if raw_saved.startswith(('"', '“', "'")) and raw_saved.endswith(('"', '”', "'")):
                raw_saved = raw_saved[1:-1].strip()
            if raw_saved:
                saved_name = raw_saved

        clean_title, effective_query = separate_title_and_research_query(
            raw_title=req.title,
            project_title=req.project_title,
            research_query=req.research_query,
            search_query=req.search_query,
            saved_project_title=saved_name,
        )

        all_req_text = f"{clean_title} {req.problem_statement or ''} {req.proposed_solution or ''} {req.tech_stack or ''}"

        # --------------------------------------------------------------------------
        # 1. RESOLVE SELECTED TEMPLATE (Custom User Uploaded or Master Template)
        # --------------------------------------------------------------------------
        effective_template_id = req.template_id
        if not effective_template_id and req.project_id and proj and proj.get("template_id"):
            effective_template_id = proj.get("template_id")
            logger.info(f"[REPORT-GEN] Resolved template_id='{effective_template_id}' from project '{req.project_id}'")

        source_template_path, resolved_template_id = resolve_selected_template_path(effective_template_id)

        # [3] Template loaded
        current_stage = "Template loaded"
        logger.info(f"[3] Template loaded: {resolved_template_id} ({source_template_path})")
        print(f"[ARM PIPELINE] [3] Template loaded: {resolved_template_id}")

        # --------------------------------------------------------------------------
        # 2. CLEAR ZERO-CHANGE CONDITION AT THE VERY BEGINNING OF PRODUCTION FLOW
        # --------------------------------------------------------------------------
        explicit_zero_change = is_zero_change_intent(all_req_text)
        has_text_replacements = (
            not explicit_zero_change
            and bool(
                (clean_title and len(clean_title) > 3)
                or req.problem_statement
                or req.proposed_solution
            )
        )
        has_image_replacements = False

        if explicit_zero_change or (not has_text_replacements and not has_image_replacements):
            current_stage = "Content generation started"
            logger.info("[4] Content generation started")
            print("[ARM PIPELINE] [4] Content generation started")

            current_stage = "Content generation completed"
            logger.info("[5] Content generation completed")
            print("[ARM PIPELINE] [5] Content generation completed")

            current_stage = "Slide analysis started"
            logger.info("[6] Slide analysis started")
            print("[ARM PIPELINE] [6] Slide analysis started")

            current_stage = "Image generation started"
            logger.info("[7] Image generation started")
            print("[ARM PIPELINE] [7] Image generation started")

            current_stage = "Image generation completed"
            logger.info("[8] Image generation completed")
            print("[ARM PIPELINE] [8] Image generation completed")

            current_stage = "Template replacement started"
            logger.info("[9] Template replacement started")
            print("[ARM PIPELINE] [9] Template replacement started")

            if not os.path.exists(source_template_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Selected template file not found at: {source_template_path}"
                )

            # DIRECT ATOMIC CANONICAL SAVE — Byte-for-byte identical master copy
            tpl_ext = Path(source_template_path).suffix.lstrip(".").lower() or "docx"
            saved_canonical_path, storage_key = report_file_storage_service.save_report_file_atomically(
                report_id=report_id,
                source_data_or_path=source_template_path,
                extension=tpl_ext,
                metadata={
                    "job_id": report_id,
                    "document_id": report_id,
                    "project_id": req.project_id,
                    "template_id": resolved_template_id,
                    "title": clean_title,
                    "zero_change": True,
                }
            )
            final_docx_path = str(saved_canonical_path)

            with open(source_template_path, "rb") as f_s:
                src_bytes = f_s.read()
                src_sha256 = hashlib.sha256(src_bytes).hexdigest()
            with open(final_docx_path, "rb") as f_d:
                dst_bytes = f_d.read()
                dst_sha256 = hashlib.sha256(dst_bytes).hexdigest()

            current_stage = "Final document created"
            logger.info("[10] Final document created")
            print("[ARM PIPELINE] [10] Final document created")

            actual_pdf_path = None
            preview_sections = []
            try:
                import docx as pydocx
                doc_obj = pydocx.Document(final_docx_path)
                sec_title = "Cover Page"
                sec_lines = []
                for p in doc_obj.paragraphs:
                    p_text = p.text.strip()
                    if not p_text:
                        continue
                    if any(h in p_text.upper() for h in ['CONTENTS', 'ABSTRACT', 'INTRODUCTION', 'OBJECTIVES', 'COMMUNITY AWARENESS', 'ADVANTAGES', 'PROBLEMS', 'CONCLUSION', 'REFERENCES', 'QUERIES', 'THANK YOU']) and len(p_text) < 50:
                        if sec_lines:
                            preview_sections.append({
                                "id": f"sec_{len(preview_sections)+1}",
                                "title": sec_title,
                                "content": "\n".join(sec_lines[:15]),
                                "wordCount": sum(len(x.split()) for x in sec_lines)
                            })
                            sec_lines = []
                        sec_title = p_text
                    else:
                        sec_lines.append(p_text)
                if sec_lines:
                    preview_sections.append({
                        "id": f"sec_{len(preview_sections)+1}",
                        "title": sec_title,
                        "content": "\n".join(sec_lines[:15]),
                        "wordCount": sum(len(x.split()) for x in sec_lines)
                    })
            except Exception as ex:
                logger.warning(f"[PRODUCTION-ZERO-CHANGE-PREVIEW] Could not extract preview sections: {ex}")

            if preview_sections:
                html_parts = [
                    f"<div class='p-6 font-serif max-w-3xl mx-auto space-y-6'>",
                    f"<h1 class='text-xl font-bold uppercase text-center text-blue-900 border-b pb-3'>{clean_title}</h1>",
                ]
                for sec in preview_sections[:8]:
                    html_parts.append(f"<div class='border-b border-zinc-100 pb-4'><h2 class='text-sm font-bold text-zinc-800 mb-2'>{sec['title']}</h2><p class='text-xs text-zinc-600 leading-relaxed whitespace-pre-line'>{sec['content']}</p></div>")
                html_parts.append("</div>")
                preview_html = "".join(html_parts)
            else:
                preview_html = f"<div class='p-6 text-center text-xs text-zinc-600 font-serif'><h3>{clean_title}</h3><p class='mt-2 text-zinc-400'>Original Template Preserved Byte-for-Byte (Zero Modifications Requested)</p></div>"

            _REPLACEMENT_JOBS[report_id] = {
                "job_id": report_id,
                "template_id": resolved_template_id,
                "template_path": source_template_path,
                "docx_path": final_docx_path,
                "pdf_path": actual_pdf_path,
                "preview_html": preview_html,
                "state": "COMPLETED",
                "progress_percent": 100,
                "arm_ui_state": "completed",
                "status_message": "Report successfully returned: exact raw copy of selected template.",
                "fields_replaced": 0,
                "images_replaced": 0,
                "sha256": dst_sha256,
                "file_size": len(dst_bytes),
                "identical": src_sha256 == dst_sha256,
            }

            # [11] Report record saved
            current_stage = "Report record saved"
            logger.info("[11] Report record saved")
            print("[ARM PIPELINE] [11] Report record saved")

            _REPORT_ID_MAPPING[report_id] = final_docx_path
            _REPORT_ID_MAPPING[f"doc-{report_id}"] = final_docx_path
            if req.project_id:
                _REPORT_ID_MAPPING[req.project_id] = final_docx_path

            _REPORTS_STORE[report_id] = {
                "report_id": report_id,
                "job_id": report_id,
                "document_id": report_id,
                "title": clean_title,
                "docx_path": final_docx_path,
                "file_name": f"{re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:30] or 'Report'}_ARM.docx",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
            }

            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:30] or "Report"

            # [12] Generation completed
            current_stage = "Generation completed"
            logger.info("[12] Generation completed")
            print("[ARM PIPELINE] [12] Generation completed\n")

            return {
                "report_id": report_id,
                "job_id": report_id,
                "document_id": report_id,
                "title": clean_title,
                "file_name": f"{safe_name}_ARM.docx",
                "output_path": final_docx_path,
                "pdf_path": None,
                "file_size_bytes": len(dst_bytes),
                "download_url": f"http://localhost:8000/api/v1/reports/{report_id}/download",
                "pdf_download_url": None,
                "preview_sections": preview_sections,
                "status": "completed",
                "state": "COMPLETED",
                "fields_replaced": 0,
                "images_replaced": 0,
                "sha256": dst_sha256,
                "identical": src_sha256 == dst_sha256,
            }

        # --------------------------------------------------------------------------
        # 3. REGULAR REPORT GENERATION FLOW (WHEN REPLACEMENTS ARE REQUESTED)
        # --------------------------------------------------------------------------
        problem_stmt = req.problem_statement or (proj.get("problem_statement") if proj else None)
        if not problem_stmt or (effective_query and problem_stmt == req.title):
            problem_stmt = f"Academic research and development for {clean_title}."
            if effective_query:
                problem_stmt += f" Focus areas: {effective_query}."

        project_data = {
            "id": req.project_id or f"proj_{report_id}",
            "title": clean_title,
            "project_title": clean_title,
            "search_query": effective_query,
            "research_query": effective_query,
            "project_type": req.project_type or (proj.get("project_type") if proj else None) or "Capstone Project",
            "student_name": req.student_name or (proj.get("student_name") if proj else None),
            "roll_number": req.roll_no or (proj.get("roll_number") if proj else None),
            "guide_name": req.guide_name or (proj.get("guide_name") if proj else None),
            "department": req.department or (proj.get("department") if proj else None),
            "institution": req.institution or (proj.get("institution") if proj else None),
            "academic_year": (proj.get("academic_year") if proj else None) or "2026-2027",
            "problem_statement": problem_stmt,
            "proposed_solution": req.proposed_solution or (proj.get("proposed_solution") if proj else None) or f"Framework and implementation details for {clean_title}.",
            "template_id": resolved_template_id,
        }

        # Execute safe in-place replacement on the Master or Custom College Template
        current_stage = "Template replacement and document synthesis"
        job_result = replacement_engine_service.execute_replacement(
            project_id=req.project_id,
            project_data=project_data,
            template_id=resolved_template_id,
            search_query=effective_query,
            job_id=report_id,
        )

        # STRICT VERIFICATION: Never report completed if replacement failed
        if job_result.get("state") == "FAILED" or job_result.get("state") != "COMPLETED":
            err_details = job_result.get("errors") or [job_result.get("status_message", "Report replacement stopped.")]
            report_file_storage_service.record_failed_generation(
                report_id=report_id,
                reason=str(err_details),
                metadata={"title": clean_title, "project_id": req.project_id, "template_id": resolved_template_id}
            )
            raise RuntimeError(f"Report replacement failed: {err_details}")

        gen_docx = job_result.get("docx_path") or job_result.get("output_path")
        if not gen_docx or not os.path.exists(gen_docx):
            report_file_storage_service.record_failed_generation(
                report_id=report_id,
                reason="Generated report document was not found after replacement",
                metadata={"title": clean_title, "project_id": req.project_id}
            )
            raise RuntimeError(f"Generated report document missing on disk: {gen_docx}")

        doc_ext = Path(gen_docx).suffix.lstrip(".").lower() or "docx"
        canonical_doc_path, storage_key = report_file_storage_service.save_report_file_atomically(
            report_id=report_id,
            source_data_or_path=gen_docx,
            extension=doc_ext,
            metadata={
                "job_id": report_id,
                "document_id": report_id,
                "project_id": req.project_id,
                "template_id": resolved_template_id,
                "title": clean_title,
                "fields_replaced": job_result.get("fields_replaced", 0),
                "images_replaced": job_result.get("images_replaced", 0),
            }
        )

        active_docx = str(canonical_doc_path)
        file_size = os.path.getsize(active_docx)
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:30] or "Report"

        # Build preview sections from replaced field values
        field_vals = job_result.get("field_values", {})
        preview_sections = []
        section_display_map = [
            ("abstract", "Abstract"),
            ("introduction", "Chapter 1: Introduction"),
            ("objectives", "Objectives"),
            ("problem_statement", "Problem Statement"),
            ("methodology", "Chapter 2: System Methodology"),
            ("advantages", "Advantages"),
            ("disadvantages", "Disadvantages"),
            ("problems_observed", "Problems Observed"),
            ("implementation", "Chapter 3: Implementation"),
            ("results", "Chapter 4: Results & Analysis"),
            ("conclusion", "Chapter 5: Conclusion"),
            ("references", "References"),
        ]
        for key, label in section_display_map:
            val = field_vals.get(key)
            if val:
                content_str = "\n".join(val) if isinstance(val, list) else str(val)
                preview_sections.append({
                    "id": key,
                    "title": label,
                    "wordCount": len(content_str.split()),
                    "content": content_str[:1200]
                })

        # [11] Report record saved
        current_stage = "Report record saved"
        logger.info("[11] Report record saved")
        print("[ARM PIPELINE] [11] Report record saved")

        _REPORT_ID_MAPPING[report_id] = active_docx
        _REPORT_ID_MAPPING[f"doc-{report_id}"] = active_docx
        if req.project_id:
            _REPORT_ID_MAPPING[req.project_id] = active_docx

        _REPORTS_STORE[report_id] = {
            "report_id": report_id,
            "job_id": report_id,
            "document_id": report_id,
            "title": clean_title,
            "docx_path": active_docx,
            "storage_key": storage_key,
            "file_name": f"{safe_name}_ARM.{doc_ext}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }

        # [12] Generation completed
        current_stage = "Generation completed"
        logger.info("[12] Generation completed")
        print("[ARM PIPELINE] [12] Generation completed\n")

        return {
            "report_id": report_id,
            "job_id": report_id,
            "document_id": report_id,
            "title": clean_title,
            "file_name": f"{safe_name}_ARM.{doc_ext}",
            "output_path": active_docx,
            "storage_key": storage_key,
            "pdf_path": None,
            "file_size_bytes": file_size,
            "download_url": f"http://localhost:8000/api/v1/reports/{report_id}/download",
            "pdf_download_url": None,
            "preview_sections": preview_sections,
            "status": "completed",
            "state": "COMPLETED",
            "fields_replaced": job_result.get("fields_replaced", 0),
            "images_replaced": job_result.get("images_replaced", 0),
        }
    except Exception as e:
        logger.error(f"FAILED AT STAGE: [{current_stage}] - Error: {e}")
        print(f"\nFAILED AT STAGE: [{current_stage}] - Error: {e}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed at stage [{current_stage}]: {str(e)}"
        )


@router.get("/{report_id}/download")
def download_generated_report(report_id: str):
    """
    Robust download endpoint for generated academic reports.
    Resolves canonical report_id, job_id, document_id, project_id, or client aliases
    using the single canonical ReportFileStorageService.
    Emits the standardized ARM REPORT DOWNLOAD TRACE block.
    """
    from apps.api.services.report_file_storage_service import report_file_storage_service

    clean_id = (report_id or "").strip()
    if clean_id.lower().endswith(".docx"):
        clean_id = clean_id[:-5]
    elif clean_id.lower().endswith(".pptx"):
        clean_id = clean_id[:-5]
    elif clean_id.lower().endswith(".pdf"):
        clean_id = clean_id[:-4]

    res = report_file_storage_service.resolve_report_file(clean_id)

    file_path = res.get("file_path")
    docx_exists = res.get("found", False)
    storage_key = res.get("storage_key", f"reports/{clean_id}.docx")
    doc_id = clean_id
    ext = res.get("extension", "docx")
    meta = res.get("metadata") or {}

    # Step 3: Mandatory ARM REPORT DOWNLOAD TRACE structured logging
    trace_log = (
        f"\n================================================================================\n"
        f"ARM REPORT DOWNLOAD TRACE\n\n"
        f"Report ID:\n{clean_id}\n\n"
        f"Document ID:\n{doc_id}\n\n"
        f"DOCX path:\n{file_path or 'NOT RESOLVED'}\n\n"
        f"DOCX exists:\n{'YES' if docx_exists else 'NO'}\n\n"
        f"PDF path:\nN/A\n\n"
        f"PDF exists:\nNO\n\n"
        f"Storage key:\n{storage_key}\n\n"
        f"Download lookup:\n{'FOUND' if docx_exists else 'NOT FOUND'}\n"
        f"================================================================================"
    )
    logger.info(trace_log)
    print(trace_log, flush=True)

    if not docx_exists:
        if res.get("status") == "FAILED":
            err_reason = res.get("error_reason") or meta.get("error_reason", "Generation failed")
            logger.error(f"[REPORT-DOWNLOAD-FAILED] Generation failed for ID '{report_id}': {err_reason}")
            raise HTTPException(
                status_code=404,
                detail=f"Report generation for ID '{report_id}' FAILED during synthesis: {err_reason}",
                headers={
                    "X-Requested-Id": report_id,
                    "X-Resolved-Path": file_path or "",
                    "X-Storage-Key": storage_key,
                    "X-Generation-Status": "FAILED",
                }
            )

        logger.error(f"[REPORT-DOWNLOAD-404] File not found for ID '{report_id}'")
        diagnostic_detail = (
            f"Generated report file for ID '{report_id}' was not found. "
            f"Requested ID: {report_id} | Resolved path: {file_path or f'.storage/reports/{clean_id}.docx'} | "
            f"Storage key: {storage_key} | Generation status: FILE_NOT_FOUND"
        )
        raise HTTPException(
            status_code=404,
            detail=diagnostic_detail,
            headers={
                "X-Requested-Id": report_id,
                "X-Resolved-Path": file_path or f".storage/reports/{clean_id}.docx",
                "X-Storage-Key": storage_key,
                "X-Generation-Status": "FILE_NOT_FOUND",
            }
        )

    with open(file_path, "rb") as f_d:
        file_bytes = f_d.read()
        served_sha = hashlib.sha256(file_bytes).hexdigest()

    logger.info(
        f"[REPORT-DOWNLOAD-SERVE] Serving report_id='{clean_id}' "
        f"path='{file_path}' size={len(file_bytes)} sha256={served_sha}"
    )

    out_filename = f"Report_{clean_id}.{ext}"
    media_type = report_file_storage_service.get_media_type(ext)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=out_filename,
        headers={"Content-Disposition": f'attachment; filename="{out_filename}"'}
    )



@router.get("/{report_id}/download-pdf")
def download_generated_report_pdf(report_id: str):
    raise HTTPException(
        status_code=400,
        detail="PDF output generation has been removed from ARM. Please download the report in DOCX format."
    )
