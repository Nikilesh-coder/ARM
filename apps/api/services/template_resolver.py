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


def resolve_selected_template_path(template_id: Optional[str] = None) -> Tuple[str, str]:
    """
    Deterministically resolves the user-selected college template .docx file path and template_id.
    Resolution priority:
    1. If template_id provided:
       a. If master preset: return DEFAULT_MASTER_TEMPLATE_PATH
       b. Check custom_template_service / in-memory store
       c. Check if template_id is a direct filesystem path
       d. Search .storage/templates recursively for matching directory/id
       e. If NOT found: raise 404 error (NO silent fallback to old or wrong template)
    2. If template_id not provided (None or empty):
       Default strictly to DEFAULT_MASTER_TEMPLATE_PATH (Institutional Master).
       Never silently fall back to old user uploads or stale active_template_design stems.
    Returns:
        (template_file_path, resolved_template_id)
    """
    from fastapi import HTTPException

    # 1. Master College Template Presets
    if template_id in ("00000000-0000-0000-0000-000000000001", "master-college-template", "master", "master_template"):
        if os.path.exists(DEFAULT_MASTER_TEMPLATE_PATH):
            return DEFAULT_MASTER_TEMPLATE_PATH, "00000000-0000-0000-0000-000000000001"
        fallback_web = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.docx")
        if os.path.exists(fallback_web):
            return fallback_web, "00000000-0000-0000-0000-000000000001"
        return DEFAULT_MASTER_TEMPLATE_PATH, "00000000-0000-0000-0000-000000000001"

    # 2. Explicit template_id provided
    if template_id and template_id.strip():
        tid = template_id.strip()

        # a. Check custom template service
        try:
            from apps.api.services.custom_template_service import custom_template_service
            cust = custom_template_service.get_template(tid)
            if cust:
                c_path = cust.get("original_file_path") or cust.get("storage_path") or cust.get("path")
                if c_path and os.path.exists(c_path):
                    resolved_abs = os.path.abspath(c_path)
                    logger.info(f"[TEMPLATE-RESOLVER] Resolved via custom_template_service: {resolved_abs} for id={tid}")
                    return resolved_abs, tid
                # Check relative to .storage
                if c_path:
                    for prefix in [".storage", ".storage/templates"]:
                        rel_try = os.path.abspath(os.path.join(prefix, c_path))
                        if os.path.exists(rel_try):
                            logger.info(f"[TEMPLATE-RESOLVER] Resolved via custom_template_service rel path: {rel_try} for id={tid}")
                            return rel_try, tid
        except Exception as e:
            logger.debug(f"[TEMPLATE-RESOLVER] custom_template_service lookup note: {e}")

        # b. Check template_id as direct filesystem path
        if os.path.exists(tid) and tid.lower().endswith(".docx"):
            return os.path.abspath(tid), tid

        # c. Search .storage/templates recursively for directory matching template_id
        storage_base = os.path.abspath(".storage")
        if os.path.exists(storage_base):
            for root, dirs, files in os.walk(storage_base):
                if tid in root or tid in dirs:
                    t_dir = root if tid in root else os.path.join(root, tid)
                    for f in os.listdir(t_dir):
                        if f.lower().endswith(".docx"):
                            cand = os.path.abspath(os.path.join(t_dir, f))
                            logger.info(f"[TEMPLATE-RESOLVER] Resolved via storage dir walk: {cand} for id={tid}")
                            return cand, tid

        # d. Strict: if explicit template_id was requested but cannot be found, raise 404
        logger.error(f"[TEMPLATE-RESOLVER] Template '{tid}' was explicitly requested but could not be found.")
        raise HTTPException(
            status_code=404,
            detail=f"Selected template '{tid}' not found in storage. Please upload or re-select the template."
        )

    # 3. No template_id provided: default strictly to master template
    if os.path.exists(DEFAULT_MASTER_TEMPLATE_PATH):
        logger.info(f"[TEMPLATE-RESOLVER] No template_id provided; using default master template: {DEFAULT_MASTER_TEMPLATE_PATH}")
        return DEFAULT_MASTER_TEMPLATE_PATH, "00000000-0000-0000-0000-000000000001"

    fallback_web = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.docx")
    if os.path.exists(fallback_web):
        return fallback_web, "00000000-0000-0000-0000-000000000001"

    return DEFAULT_MASTER_TEMPLATE_PATH, "00000000-0000-0000-0000-000000000001"


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
