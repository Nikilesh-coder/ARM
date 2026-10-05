"""
ARM Stage 10 - Template Replacement Engine Router
Provides endpoints for executing in-place template replacement,
polling 7-state progress, downloading DOCX/PDF, and previewing output.
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from apps.api.core.auth import get_current_user_optional
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger
from apps.api.services.replacement_engine_service import replacement_engine_service, _REPLACEMENT_JOBS
from apps.api.services.master_template_service import master_template_service, MASTER_TEMPLATE_ID


router = APIRouter(prefix="/replacement", tags=["Template Replacement Engine"])
logger = get_logger("replacement.router")


class ReplacementExecutionRequest(BaseModel):
    """Payload for triggering the ARM Template Replacement Engine."""
    project_id: Optional[str] = None
    template_id: Optional[str] = None
    custom_content: Optional[Dict[str, Any]] = None
    custom_assets: Optional[Dict[str, Any]] = None
    project_data: Optional[Dict[str, Any]] = None
    user_instructions: Optional[str] = None
    search_query: Optional[str] = None
    query: Optional[str] = None
    provider: Optional[str] = Field(None, description="Document provider: 'internal' (default) or 'carbone'")


class PdfAnalysisRequest(BaseModel):
    """Payload for analyzing a candidate college PDF template."""
    pdf_path: str = Field(..., description="Absolute path or relative path to PDF file")


class TemplateAnalyzeRequest(BaseModel):
    """Payload for analyzing canonical template fields."""
    template_id: Optional[str] = Field(default=MASTER_TEMPLATE_ID, description="Template identifier")


@router.post("/analyze")
def analyze_replacement_template(payload: TemplateAnalyzeRequest):
    """
    Analyzes template fields, canonical placeholders, and image requirements
    for the Master College Template or specified template.
    """
    tid = payload.template_id or MASTER_TEMPLATE_ID
    if tid != MASTER_TEMPLATE_ID:
        client = db_manager.client
        found = False
        if client:
            try:
                res = client.table("templates").select("id").eq("id", tid).execute()
                if res.data and len(res.data) > 0:
                    found = True
            except Exception:
                pass
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{tid}' not found."
            )

    fields = master_template_service.get_template_fields(tid)


    canonical_field_names = [f["field_name"] for f in fields]
    image_field_names = [f["field_name"] for f in fields if f.get("field_type") == "image"]
    required_field_names = [f["field_name"] for f in fields if f.get("is_required")]

    return {
        "template_id": tid,
        "template_name": "Master College Template (IEEE Standard)",
        "total_fields": len(fields),
        "canonical_fields": canonical_field_names,
        "image_fields": image_field_names,
        "required_fields": required_field_names,
        "fields": fields,
    }


@router.get("/providers")

def list_document_providers():
    """
    Returns available document generation providers (Internal, Carbone, etc.).
    Never exposes API keys or sensitive credentials.
    """
    return replacement_engine_service.list_document_providers()


@router.post("/analyze-pdf")
def analyze_pdf_template(payload: PdfAnalysisRequest):
    """
    Analyzes whether a college PDF template contains editable text/layout information
    suitable for reliable in-place replacement without breaking visual integrity.
    """
    if not os.path.exists(payload.pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF template file not found at: '{payload.pdf_path}'"
        )
    return replacement_engine_service.analyze_pdf_template(payload.pdf_path)


@router.post("/execute")
def execute_replacement(
    payload: ReplacementExecutionRequest,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Executes the ARM Master College Template Replacement Engine:
    1. Loads Master College Template (source of truth).
    2. Loads student structured content (or invokes AI Report Agent).
    3. Matches each generated field to its TemplateField.
    4. Replaces existing template text in-place.
    5. Replaces existing template images with ARM-selected/generated assets.
    6. Strictly preserves fonts, colors, headings, spacing, margins, logos, headers, footers.
    7. Generates completed report.
    8. Validates output and provides preview & download.
    """
    try:
        result = replacement_engine_service.execute_replacement(
            project_id=payload.project_id,
            template_id=payload.template_id,
            custom_content=payload.custom_content,
            custom_assets=payload.custom_assets,
            project_data=payload.project_data,
            user_instructions=payload.user_instructions,
            search_query=payload.search_query or payload.query,
            provider=payload.provider,
        )
        return result
    except Exception as e:
        logger.error(f"Error executing replacement pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template Replacement failed: {str(e)}"
        )


@router.get("/status/{job_id}")
@router.get("/jobs/{job_id}")
@router.get("/jobs/{job_id}/status")
def get_replacement_status(job_id: str):
    """
    Polls real-time progression through the 7 states:
    QUEUED -> ANALYZING -> GENERATING -> REPLACING -> VALIDATING -> COMPLETED / FAILED
    """
    job = replacement_engine_service.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replacement job '{job_id}' not found."
        )
    return job


@router.get("/download/{job_id}")
@router.get("/jobs/{job_id}/download")
def download_report_file(
    job_id: str,
    format: str = Query("docx", description="File format to download: 'docx' or 'pdf'")
):
    fmt = format.lower()
    if fmt == "pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF output generation has been removed from ARM. Please download the report in DOCX format."
        )

    from apps.api.services.report_file_storage_service import report_file_storage_service

    clean_id = (job_id or "").strip()
    res = report_file_storage_service.resolve_report_file(clean_id)

    if not res.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requested {fmt.upper()} file does not exist on disk for job ID '{job_id}'."
        )

    file_path = res["file_path"]
    ext = res.get("extension", "docx")
    media_type = report_file_storage_service.get_media_type(ext)
    filename = f"ARM_Report_{clean_id}.{ext}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


class RegenerateSectionRequest(BaseModel):
    """Payload for targeted single-section regeneration."""
    job_id: str = Field(..., description="Active template replacement job ID")
    section_name: str = Field(..., description="Canonical section or field name, e.g. 'methodology'")
    custom_prompt: Optional[str] = Field(None, description="Optional custom student instructions")


class ReplaceImageRequest(BaseModel):
    """Payload for in-place replacement of a template image slot."""
    job_id: str = Field(..., description="Active template replacement job ID")
    image_slot: str = Field(..., description="Target image slot: 'image_1', 'image_2', etc.")
    asset_path: Optional[str] = Field(None, description="Disk path to replacement image")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image data")
    caption: Optional[str] = Field(None, description="Updated figure caption")


class RegenerateReportRequest(BaseModel):
    """Payload for full report regeneration."""
    user_instructions: Optional[str] = Field(None, description="Optional updated student instructions")


@router.post("/regenerate-section")
def regenerate_section(payload: RegenerateSectionRequest):
    """
    Regenerates a single targeted section in-place:
    Synthesizes updated technical prose matching template constraints,
    re-runs OpenXML template insertion, and updates preview HTML and PDF.
    """
    try:
        return replacement_engine_service.regenerate_section(
            job_id=payload.job_id,
            section_name=payload.section_name,
            custom_prompt=payload.custom_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error regenerating section: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Section regeneration failed: {str(e)}"
        )


@router.post("/replace-image")
def replace_image(payload: ReplaceImageRequest):
    """
    Replaces a specific template image slot (image_1, image_2, etc.) in-place
    and updates document preview and PDF artifacts.
    """
    try:
        return replacement_engine_service.replace_image(
            job_id=payload.job_id,
            image_slot=payload.image_slot,
            asset_path=payload.asset_path,
            image_base64=payload.image_base64,
            caption=payload.caption,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error replacing image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image replacement failed: {str(e)}"
        )


@router.post("/approve/{job_id}")
def approve_report(job_id: str):
    """
    Approves the generated report:
    Persists student approval status, locks submission state, and synchronizes DB.
    """
    try:
        return replacement_engine_service.approve_report(job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report approval failed: {str(e)}"
        )


@router.post("/regenerate/{job_id}")
def regenerate_full_report(job_id: str, payload: Optional[RegenerateReportRequest] = None):
    """
    Performs a fresh, complete regeneration of the report in-place for an existing job.
    """
    try:
        instructions = payload.user_instructions if payload else None
        return replacement_engine_service.regenerate_full_report(job_id, instructions)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error regenerating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report regeneration failed: {str(e)}"
        )


@router.get("/preview/{job_id}")
def preview_report(job_id: str):
    """Returns the preview HTML, document stats, approval status, and action URLs for immediate rendering."""
    job = replacement_engine_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    return {
        "job_id": job_id,
        "state": job.get("state"),
        "approval_status": job.get("approval_status", "pending"),
        "approved_at": job.get("approved_at"),
        "preview_html": job.get("preview_html"),
        "stats": job.get("stats", {}),
        "fields_replaced": job.get("fields_replaced"),
        "total_fields": job.get("total_fields"),
        "images_replaced": job.get("images_replaced"),
        "warnings": job.get("warnings", []),
        "errors": job.get("errors", []),
        "download_docx_url": f"/api/v1/replacement/download/{job_id}?format=docx",
        "download_pdf_url": f"/api/v1/replacement/download/{job_id}?format=pdf" if job.get("pdf_path") else None,
    }


@router.get("/master-template")
def get_master_template_info():
    """Returns the locked Master College Template and its 20 canonical fields."""
    return master_template_service.get_master_template()

