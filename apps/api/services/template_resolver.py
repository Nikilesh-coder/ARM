"""
ReportForge AI / ARM - Template Resolver Service
Provides authoritative, deterministic resolution of the user-selected or active college DOCX template.
Guarantees source-of-truth preservation for custom uploaded templates.
"""

import os
import json
import hashlib
from typing import Optional, Tuple
from apps.api.core.logging import get_logger

logger = get_logger("service.template_resolver")

DEFAULT_MASTER_TEMPLATE_PATH = os.path.abspath(".storage/templates/master_college_template.docx")


def _validate_resolved_template(resolved_path: str, template_id: str) -> str:
    """Enforces that the resolved template exists, is non-empty, and is strictly a .docx file."""
    from fastapi import HTTPException
    if not resolved_path:
        raise HTTPException(status_code=404, detail=f"No template resolved for id '{template_id}'.")
    if resolved_path.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Resolved template path '{resolved_path}' for id '{template_id}' is a PDF file. "
                f"The original PDF must never be passed into the report-generation engine. "
                f"A valid converted .docx template is required."
            )
        )
    if not resolved_path.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Resolved template '{resolved_path}' for id '{template_id}' is not a .docx document."
        )
    if not os.path.exists(resolved_path) or os.path.getsize(resolved_path) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Resolved template DOCX does not exist or is empty: {resolved_path}"
        )
    return os.path.abspath(resolved_path)


def resolve_selected_template_path(template_id: Optional[str] = None) -> Tuple[str, str]:
    """
    Deterministically resolves the user-selected college template .docx file path and template_id.
    Resolution priority:
    1. If master preset: return DEFAULT_MASTER_TEMPLATE_PATH
    2. If explicit template_id provided:
       a. Check custom_template_service / in-memory store
       b. Check Supabase DB templates table and download from storage if needed
       c. Check if template_id is a direct filesystem path
       d. Search .storage/templates recursively for matching directory/id
       e. If NOT found: raise 404 error (NO silent fallback to master or default template)
    3. If template_id not provided (None or empty):
       Raise 400/404 error (strict requirement: explicit template selection required).
    HARD CONSTRAINT:
       The returned path MUST be a validated .docx file. The original PDF is NEVER returned.
    Returns:
        (template_docx_path, resolved_template_id)
    """
    from fastapi import HTTPException
    from apps.api.core.config import settings
    from apps.api.services.storage import get_storage_provider
    from apps.api.core.database import db_manager

    # 1. Reject missing / empty template_id (NO silent fallback)
    if not template_id or not template_id.strip():
        logger.error("[TEMPLATE-RESOLVER] No template_id was provided for report generation.")
        raise HTTPException(
            status_code=400,
            detail="No college template selected. Please select or upload a college DOCX template before generating a report."
        )

    tid = template_id.strip()

    # 2. Master College Template Presets
    if tid in ("00000000-0000-0000-0000-000000000001", "master-college-template", "master", "master_template"):
        if os.path.exists(DEFAULT_MASTER_TEMPLATE_PATH):
            return _validate_resolved_template(DEFAULT_MASTER_TEMPLATE_PATH, tid), "00000000-0000-0000-0000-000000000001"
        fallback_web = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.docx")
        if os.path.exists(fallback_web):
            return _validate_resolved_template(fallback_web, tid), "00000000-0000-0000-0000-000000000001"
        return _validate_resolved_template(DEFAULT_MASTER_TEMPLATE_PATH, tid), "00000000-0000-0000-0000-000000000001"

    # 3. Explicit template_id provided
    cust = None

    # a. Check custom template service / in-memory store
    try:
        from apps.api.services.custom_template_service import custom_template_service
        cust = custom_template_service.get_template(tid)
    except Exception as e:
        logger.debug(f"[TEMPLATE-RESOLVER] custom_template_service lookup note: {e}")

    # b. If not in memory, query Supabase templates table
    if not cust and db_manager.client:
        try:
            res = db_manager.client.table("templates").select("*").eq("id", tid).execute()
            if res.data and len(res.data) > 0:
                cust = res.data[0]
        except Exception as e:
            logger.debug(f"[TEMPLATE-RESOLVER] DB templates table query note: {e}")

    # c. If template record found, inspect candidate paths or download from storage provider
    if cust:
        c_path = (
            cust.get("converted_docx_path")
            or cust.get("working_docx_path")
            or cust.get("file_path")
            or cust.get("path")
            or cust.get("original_file_path")
        )
        if c_path and os.path.exists(c_path):
            if c_path.lower().endswith(".pdf"):
                working_cand = f"{os.path.splitext(c_path)[0]}_working.docx"
                if os.path.exists(working_cand):
                    c_path = working_cand
                else:
                    from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                    w_path, _, _ = pdf_to_docx_service.convert_pdf_file_to_docx(c_path, working_cand)
                    c_path = w_path

            resolved_abs = _validate_resolved_template(c_path, tid)
            logger.info(f"[TEMPLATE-RESOLVER] Resolved via existing local path: {resolved_abs} for id={tid}")
            return resolved_abs, tid

        # Check relative to storage base
        if c_path:
            for prefix in [".storage", ".storage/templates"]:
                rel_try = os.path.abspath(os.path.join(prefix, c_path))
                if os.path.exists(rel_try):
                    if rel_try.lower().endswith(".pdf"):
                        working_cand = f"{os.path.splitext(rel_try)[0]}_working.docx"
                        if os.path.exists(working_cand):
                            rel_try = working_cand
                        else:
                            from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                            w_path, _, _ = pdf_to_docx_service.convert_pdf_file_to_docx(rel_try, working_cand)
                            rel_try = w_path

                    resolved_abs = _validate_resolved_template(rel_try, tid)
                    logger.info(f"[TEMPLATE-RESOLVER] Resolved via relative path: {resolved_abs} for id={tid}")
                    return resolved_abs, tid

        # If not present on local disk (e.g. Render container restart), download from Supabase Storage
        storage_path = cust.get("storage_path")
        if not storage_path and c_path and "users/" in c_path:
            storage_path = c_path[c_path.index("users/"):]

        if storage_path:
            try:
                sp = get_storage_provider()
                file_data = sp.download_file(settings.storage.bucket_templates, storage_path)
                if file_data:
                    local_dest = os.path.abspath(os.path.join(".storage", settings.storage.bucket_templates, storage_path))
                    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
                    with open(local_dest, "wb") as f_out:
                        f_out.write(file_data)
                    resolved_abs = _validate_resolved_template(local_dest, tid)
                    logger.info(f"[TEMPLATE-RESOLVER] Downloaded from cloud storage to {resolved_abs} for id={tid}")
                    return resolved_abs, tid
            except Exception as dl_err:
                logger.warning(f"[TEMPLATE-RESOLVER] Could not download storage_path '{storage_path}': {dl_err}")

    # d. Check template_id as direct filesystem path
    if os.path.exists(tid):
        if tid.lower().endswith(".docx"):
            return _validate_resolved_template(tid, tid), tid
        elif tid.lower().endswith(".pdf"):
            working_cand = f"{os.path.splitext(tid)[0]}_working.docx"
            if not os.path.exists(working_cand):
                from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                pdf_to_docx_service.convert_pdf_file_to_docx(tid, working_cand)
            if os.path.exists(working_cand):
                return _validate_resolved_template(working_cand, tid), tid

    # e. Search .storage/templates recursively for directory matching template_id
    storage_base = os.path.abspath(".storage")
    if os.path.exists(storage_base):
        for root, dirs, files in os.walk(storage_base):
            if tid in root or tid in dirs:
                t_dir = root if tid in root else os.path.join(root, tid)
                docx_files = [f for f in os.listdir(t_dir) if f.lower().endswith(".docx")]
                if docx_files:
                    cand = os.path.abspath(os.path.join(t_dir, docx_files[0]))
                    resolved_abs = _validate_resolved_template(cand, tid)
                    logger.info(f"[TEMPLATE-RESOLVER] Resolved via storage dir walk: {resolved_abs} for id={tid}")
                    return resolved_abs, tid
                pdf_files = [f for f in os.listdir(t_dir) if f.lower().endswith(".pdf")]
                if pdf_files:
                    pdf_cand = os.path.abspath(os.path.join(t_dir, pdf_files[0]))
                    working_cand = f"{os.path.splitext(pdf_cand)[0]}_working.docx"
                    from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                    w_path, _, _ = pdf_to_docx_service.convert_pdf_file_to_docx(pdf_cand, working_cand)
                    resolved_abs = _validate_resolved_template(w_path, tid)
                    return resolved_abs, tid

    # f. Strict: if explicit template_id was requested but cannot be found, raise 404
    logger.error(f"[TEMPLATE-RESOLVER] Template '{tid}' was requested but could not be found in memory, DB, or storage.")
    raise HTTPException(
        status_code=404,
        detail=f"Selected template '{tid}' not found in storage. Please upload or re-select the template."
    )


def is_zero_change_intent(text_or_inputs: str) -> bool:
    """
    Checks whether user input strictly requests zero changes / exact template copy.
    """
    if not text_or_inputs:
        return False
    lower_text = str(text_or_inputs).lower()
    zero_change_phrases = [
        "do not change",
        "do not replace",
        "do not modify",
        "return the template exactly",
        "exactly as uploaded",
        "as uploaded",
        "zero change",
        "zero changes",
        "no change",
        "no changes",
        "keep as is",
        "exact copy",
        "unchanged",
        "raw copy",
        "without changes",
        "without modifications",
        "zero content change",
        "zero replacement",
        "do not alter",
        "leave as is",
        "keep original",
    ]
    return any(phrase in lower_text for phrase in zero_change_phrases)
