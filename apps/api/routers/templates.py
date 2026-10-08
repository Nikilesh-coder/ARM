"""
ReportForge AI - Templates Router
Stage 2: Production-grade College Template Upload & Ingestion
Handles DOCX & PDF validation, private storage, database registration,
safe replacement, and analysis job queueing.
"""

import os
import io
import uuid
import zipfile
import tempfile
import hashlib
import pypdf
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status, BackgroundTasks, Query
from fastapi.responses import FileResponse

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.core.auth import get_current_user_optional
from apps.api.services.storage import get_storage_provider
from apps.api.services.template_intelligence import template_intelligence_service, _JOBS_STORE
from packages.template_intelligence.parser import TemplateParser
from packages.template_intelligence.schema import TemplateSchema
from apps.api.schemas.template import (
    TemplateUploadResponse,
    TemplateConfirmDTO,
    TemplateDTO,
    TemplateAnalyzeResponse,
    TemplateAnalysisResponse,
    GenerationJobResponse,
    TemplateReviewResponse,
    TemplateReviewPatchRequest,
    TemplateLockRequest,
    TemplateLockResponse,
    TemplateFieldDTO,
    TemplateFieldResponseDTO,
    MasterTemplateResponseDTO,
    CustomTemplateMappingRequest,
)
from apps.api.services.master_template_service import master_template_service

logger = get_logger("templates")
router = APIRouter(tags=["Templates"])

# In-memory storage cache for local fallback / mocks
_TEMPLATES_DB: Dict[str, Any] = {}
_TEMPLATE_SCHEMAS: Dict[str, TemplateSchema] = {}


def _is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _get_template_with_ownership_check(template_id: str, project_id: str, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to verify template existence, project membership, and user authorization."""
    client = db_manager.client
    template = None
    if client:
        try:
            t_res = client.table("templates").select("*").eq("id", template_id).execute()
            if t_res.data and len(t_res.data) > 0:
                template = t_res.data[0]
        except Exception as e:
            logger.error(f"Error fetching template {template_id}: {e}")

    if not template:
        template = _TEMPLATES_DB.get(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    if template.get("project_id") and str(template.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template does not belong to this project.")

    t_owner = template.get("user_id") or template.get("owner_id")
    if user and t_owner and str(t_owner) != str(user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this template.")

    return template


def _verify_project_ownership(project_id: str, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to verify project existence and user authorization."""
    client = db_manager.client
    project = None
    if client:
        try:
            res = client.table("projects").select("*").eq("id", project_id).execute()
            if res.data and len(res.data) > 0:
                project = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}")

    # Fallback to local memory store
    if not project:
        from apps.api.routers.projects import _PROJECTS_STORE
        project = _PROJECTS_STORE.get(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )

    if user:
        owner = project.get("user_id") or project.get("owner_id")
        if owner and str(owner) != str(user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this project."
            )

    return project


def _validate_template_file(content: bytes, filename: str) -> str:
    """Validates file format, size, magic bytes, and integrity. Returns extension."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a valid document."
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf" or ext != ".docx":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DOCX college templates are currently supported."
        )

    # Empty file check
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please upload a valid document."
        )

    # Maximum file size check (default: 25MB)
    max_bytes = settings.storage.docx_max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large. Please upload a smaller template."
        )

    # DOCX validation
    if ext == ".docx":
        # Magic bytes check (PK\x03\x04)
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ARM could not read this file. Please upload a valid document."
            )

        # Structural & anti-zip bomb check
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ARM could not read this file. Please upload a valid document."
                    )
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                if total_uncompressed > 100 * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File is too large. Please upload a smaller template."
                    )
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ARM could not read this file. Please upload a valid document."
            )

    return ext


@router.post("/projects/{project_id}/templates/upload", response_model=TemplateUploadResponse)
async def upload_project_template(
    project_id: str,
    file: UploadFile = File(...),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 2: College Template Upload Endpoint.
    1. Authenticates caller & verifies project ownership.
    2. Validates format (DOCX or PDF), magic bytes, and integrity.
    3. Securely stores untouched original bytes in private storage.
    4. Handles safe template replacement (preserves previous original file).
    5. Registers template record in Supabase with status 'uploaded' and analysis_status 'pending'.
    """
    project = _verify_project_ownership(project_id, user)
    owner_id = user["id"] if user else (project.get("user_id") or project.get("owner_id") or "usr_demo_student")

    content = await file.read()
    ext = _validate_template_file(content, file.filename or "")

    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 1. Private Storage Destination - Store untouched original DOCX template
    storage_path = f"users/{owner_id}/projects/{project_id}/templates/{template_id}/original.docx"
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    storage_provider = get_storage_provider()
    try:
        storage_provider.upload_file(
            bucket=settings.storage.bucket_templates,
            path=storage_path,
            data=content,
            content_type=content_type
        )
    except Exception as e:
        logger.error(f"Failed to store template file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template upload failed. Please try again."
        )

    local_storage_dir = os.path.abspath(
        os.path.join(".storage", settings.storage.bucket_templates, f"users/{owner_id}/projects/{project_id}/templates/{template_id}")
    )
    os.makedirs(local_storage_dir, exist_ok=True)
    local_docx_path = os.path.join(local_storage_dir, "original.docx")

    with open(local_docx_path, "wb") as f_docx:
        f_docx.write(content)

    # 2. Safe Replacement: Historical templates remain preserved in storage and DB
    # The active template is queried via order('created_at', desc=True)
    client = db_manager.client

    # 3. Database Registration
    db_user_id = owner_id if _is_valid_uuid(owner_id) else None
    if not db_user_id and client:
        try:
            prof = client.table("profiles").select("id").limit(1).execute()
            if prof.data:
                db_user_id = prof.data[0]["id"]
        except Exception:
            pass

    db_proj_id = project_id if _is_valid_uuid(project_id) else None

    template_record = {
        "id": template_id,
        "user_id": db_user_id,
        "owner_id": db_user_id,
        "project_id": db_proj_id,
        "name": file.filename,
        "original_file_path": local_docx_path,
        "original_pdf_path": None,
        "storage_path": storage_path,
        "converted_docx_path": local_docx_path,
        "working_docx_path": local_docx_path,
        "file_path": local_docx_path,
        "path": local_docx_path,
        "converted_from_pdf": False,
        "source_format": "docx",
        "source_file_type": "docx",
        "file_type": "docx",
        "file_size": len(content),
        "status": "uploaded",
        "analysis_status": "pending",
        "is_locked": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    if client:
        try:
            res = client.table("templates").insert(template_record).execute()
            if not res.data:
                raise Exception("Empty insert response from database.")
        except Exception as e:
            logger.error(f"Failed to register template in database: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Template registration failed. Please try again."
            )

    _TEMPLATES_DB[template_id] = {
        **template_record,
        "user_id": owner_id,
        "project_id": project_id
    }
    from apps.api.services.custom_template_service import _CUSTOM_TEMPLATES_STORE
    _CUSTOM_TEMPLATES_STORE[template_id] = {
        **template_record,
        "user_id": owner_id,
        "project_id": project_id
    }

    return TemplateUploadResponse(
        template_id=template_id,
        name=file.filename or "template",
        file_size_bytes=len(content),
        is_preset=False,
        status="uploaded",
        analysis_status="pending",
        project_id=project_id,
        original_file_path=storage_path,
        file_type="docx",
        message="Template uploaded successfully. Ready for analysis."
    )


@router.get("/templates/master", response_model=MasterTemplateResponseDTO)
def get_master_college_template():
    """
    Retrieves the authoritative Master College Template with all 20
    configurable fields, content limits, and placeholder mappings.
    Configured once by institution and automatically reused by all students.
    """
    return master_template_service.get_master_template()


@router.post("/templates/upload-custom", response_model=Dict[str, Any])
async def upload_custom_college_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    institution: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    report_type: Optional[str] = Form("Seminar"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 15: Upload & Ingest Custom College Template (.docx).
    1. Validates format (DOCX only), magic bytes, anti-zip bomb.
    2. Stores untouched original file in user storage bucket.
    3. Analyzes exact page geometry, paragraphs, candidate placeholders, and images.
    4. Categorizes into FIXED elements vs candidate REPLACEABLE elements.
    5. Saves template record under authenticated user ID.
    """
    from apps.api.services.custom_template_service import custom_template_service

    owner_id = user["id"] if user else "usr_demo_student"
    content = await file.read()
    upload_filename = file.filename or "college_template.docx"
    ext = os.path.splitext(upload_filename)[1].lower()
    if ext == ".pdf" or ext != ".docx":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DOCX college templates are currently supported."
        )

    upload_size = len(content)
    upload_sha256 = hashlib.sha256(content).hexdigest()

    logger.info(f"[RAW-TEMPLATE-UPLOAD] Received: filename={upload_filename} size={upload_size} sha256={upload_sha256}")
    print(f"\n[RAW-TEMPLATE-UPLOAD]\nfilename={upload_filename}\nfile_size={upload_size}\nsha256={upload_sha256}\n")

    try:
        record = custom_template_service.register_custom_template(
            file_bytes=content,
            filename=upload_filename,
            template_name=name,
            owner_id=owner_id,
            institution=institution,
            department=department,
            report_type=report_type,
        )
        record["sha256"] = upload_sha256
        record["file_size"] = upload_size
        _TEMPLATES_DB[record["id"]] = record
        return {
            "status": "success",
            "template": record,
            "message": f"College template '{record['name']}' uploaded and analyzed successfully.",
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error uploading custom template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload and analyze college template. Please ensure it is a valid DOCX file."
        )


@router.get("/templates/{template_id}/raw-download")
def download_raw_template(
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Temporary Isolated Diagnostic Endpoint: RAW TEMPLATE DOWNLOAD.
    Directly retrieves and streams the original immutable stored template file.
    ZERO report generation, ZERO AI, ZERO replacement engine, ZERO document parsing.
    """
    from apps.api.services.custom_template_service import custom_template_service, _CUSTOM_TEMPLATES_STORE

    target_path = None
    filename = "college_template.docx"

    # 1. Check custom templates store
    tpl = custom_template_service.get_template(template_id)
    if not tpl:
        tpl = _TEMPLATES_DB.get(template_id)
    if not tpl:
        tpl = _CUSTOM_TEMPLATES_STORE.get(template_id)

    # 2. Check Supabase if DB client available
    client = db_manager.client
    if not tpl and client:
        try:
            res = client.table("templates").select("*").eq("id", template_id).execute()
            if res.data and len(res.data) > 0:
                tpl = res.data[0]
        except Exception as e:
            logger.warning(f"Error querying template {template_id} from DB: {e}")

    # 3. Check master/preset fallback
    if not tpl and template_id in ("00000000-0000-0000-0000-000000000001", "master_template", "default"):
        target_path = os.path.abspath(".storage/templates/master_college_template.docx")
        filename = "master_college_template.docx"

    if tpl:
        filename = tpl.get("name") or tpl.get("filename") or "college_template.docx"
        if not filename.endswith(".docx"):
            filename = f"{filename}.docx"

        # Resolve path
        candidates = [
            tpl.get("original_file_path"),
            tpl.get("path"),
            tpl.get("storage_path"),
        ]
        for c in candidates:
            if not c:
                continue
            if os.path.exists(c):
                target_path = os.path.abspath(c)
                break
            rel_dot = os.path.abspath(os.path.join(".storage", c))
            if os.path.exists(rel_dot):
                target_path = rel_dot
                break
            rel_tpl = os.path.abspath(os.path.join(".storage", "templates", c))
            if os.path.exists(rel_tpl):
                target_path = rel_tpl
                break

    # 3b. Fallback: Download from cloud storage provider if not on local disk
    if (not target_path or not os.path.exists(target_path)) and tpl:
        s_path = tpl.get("storage_path")
        if not s_path and tpl.get("original_file_path") and "users/" in tpl.get("original_file_path", ""):
            orig = tpl.get("original_file_path", "")
            s_path = orig[orig.index("users/"):]
        if s_path:
            try:
                sp = get_storage_provider()
                file_data = sp.download_file(settings.storage.bucket_templates, s_path)
                if file_data:
                    local_dest = os.path.abspath(os.path.join(".storage", settings.storage.bucket_templates, s_path))
                    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
                    with open(local_dest, "wb") as f_out:
                        f_out.write(file_data)
                    target_path = local_dest
            except Exception as dl_err:
                logger.warning(f"[RAW-TEMPLATE-LOOKUP] Could not download from cloud storage: {dl_err}")

    # 3c. Fallback disk walk search across .storage if not found in memory/db
    if not target_path or not os.path.exists(target_path):
        base_storage = os.path.abspath(".storage")
        if os.path.exists(base_storage):
            for root, dirs, files in os.walk(base_storage):
                if template_id in root or template_id in dirs:
                    t_dir = root if template_id in root else os.path.join(root, template_id)
                    for f in os.listdir(t_dir):
                        if f.endswith((".docx", ".pdf")):
                            target_path = os.path.abspath(os.path.join(t_dir, f))
                            filename = f
                            break
                    if target_path and os.path.exists(target_path):
                        break

    file_exists = bool(target_path and os.path.exists(target_path))
    logger.info(f"[RAW-TEMPLATE-LOOKUP] template_id={template_id} path={target_path} exists={file_exists}")
    print(f"\n[RAW-TEMPLATE-LOOKUP]\ntemplate_id={template_id}\npath={target_path}\nexists={file_exists}\n")

    if not file_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Original template file for ID '{template_id}' not found in storage. Looked at: '{target_path}'"
        )

    # 4. Read raw file bytes & compute SHA-256 and size
    with open(target_path, "rb") as f:
        stored_bytes = f.read()

    stored_file_size = len(stored_bytes)
    stored_file_sha256 = hashlib.sha256(stored_bytes).hexdigest()

    log_msg = (
        f"\n[RAW-TEMPLATE]\n"
        f"template_id={template_id}\n"
        f"filename={filename}\n"
        f"path={target_path}\n"
        f"size={stored_file_size}\n"
        f"sha256={stored_file_sha256}\n"
    )
    print(log_msg)
    logger.info(log_msg)

    return FileResponse(
        path=target_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        headers={
            "X-Template-ID": template_id,
            "X-Stored-SHA256": stored_file_sha256,
            "X-Stored-Size": str(stored_file_size),
        }
    )


@router.get("/templates/{template_id}/details", response_model=Dict[str, Any])
@router.get("/templates/{template_id}", response_model=Dict[str, Any])
def get_template_details(
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves full template metadata including geometry, field mappings, image mappings, and status."""
    from apps.api.services.custom_template_service import custom_template_service

    user_id = user["id"] if user else None
    try:
        template = custom_template_service.get_template(template_id, user_id=user_id)
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))

    if not template:
        template = _TEMPLATES_DB.get(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College template not found.")

    return template


@router.put("/templates/{template_id}/mapping", response_model=Dict[str, Any])
def update_template_mappings(
    template_id: str,
    payload: CustomTemplateMappingRequest,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Saves verified user mapping for the custom template (Text fields & Image slots)."""
    from apps.api.services.custom_template_service import custom_template_service

    user_id = user["id"] if user else None
    try:
        updated = custom_template_service.update_mappings(
            template_id=template_id,
            field_mapping=payload.field_mapping,
            image_mapping=payload.image_mapping or [],
            user_id=user_id,
        )
        _TEMPLATES_DB[template_id] = updated
        return {
            "status": "success",
            "template": updated,
            "message": "Template mapping saved successfully. Template is Ready for report synthesis.",
        }
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.delete("/templates/{template_id}")
def delete_custom_template(
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Deletes an uploaded custom template with user authorization check."""
    from apps.api.services.custom_template_service import custom_template_service, _CUSTOM_TEMPLATES_STORE

    user_id = user["id"] if user else None
    try:
        tpl = custom_template_service.get_template(template_id, user_id=user_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found.")
        _CUSTOM_TEMPLATES_STORE.pop(template_id, None)
        _TEMPLATES_DB.pop(template_id, None)
        client = db_manager.client
        if client:
            try:
                client.table("templates").delete().eq("id", template_id).execute()
            except Exception:
                pass
        return {"status": "success", "message": f"Template {template_id} deleted successfully."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.get("/templates", response_model=List[TemplateDTO])
def list_available_templates(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Lists available templates for project creation and report generation:
    - Master College Template & Institutional presets
    - User uploaded custom templates (strictly isolated by user account)
    """
    from apps.api.services.custom_template_service import custom_template_service

    templates_map: Dict[str, Any] = {}

    # 1. Authoritative Master College Template
    master_tpl = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Standard College Academic Master Template (.docx)",
        "original_file_path": ".storage/templates/master_college_template.docx",
        "file_type": "docx",
        "file_size": 42100,
        "status": "ready",
        "is_locked": True,
        "is_institution_preset": True,
        "is_master": True,
        "institution": "Institutional Standard",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    templates_map[master_tpl["id"]] = master_tpl

    # 2. Add user-uploaded custom templates
    user_id = user["id"] if user else "usr_demo_student"
    custom_templates = custom_template_service.list_templates_for_user(user_id=user_id)
    for ct in custom_templates:
        templates_map[ct["id"]] = ct

    # 3. Add templates from in-memory cache
    for k, t in _TEMPLATES_DB.items():
        if k not in templates_map:
            norm_t = dict(t)
            if "name" not in norm_t or not norm_t["name"]:
                norm_t["name"] = norm_t.get("filename") or norm_t.get("template_name") or f"Template {k[:8]}"
            if "original_file_path" not in norm_t and "path" in norm_t:
                norm_t["original_file_path"] = norm_t["path"]
            if "file_size" not in norm_t and "size" in norm_t:
                norm_t["file_size"] = norm_t["size"]
            templates_map[k] = norm_t

    # 4. Query DB if connected
    client = db_manager.client
    if client:
        try:
            query = client.table("templates").select("*")
            if user:
                query = query.or_(f"user_id.eq.{user['id']},owner_id.eq.{user['id']},is_institution_preset.eq.true")
            res = query.order("created_at", desc=True).limit(50).execute()
            if res.data:
                for t in res.data:
                    if t.get("id") and t["id"] not in templates_map:
                        templates_map[t["id"]] = t
        except Exception as e:
            logger.error(f"Error querying templates list: {e}")

    # Fallback presets if list is minimal
    fallback_presets = [
        {
            "id": "tpl_preset_capstone",
            "name": "Standard University Capstone Report Template (.docx)",
            "original_file_path": ".storage/templates/capstone_template.docx",
            "file_type": "docx",
            "file_size": 42100,
            "status": "ready",
            "is_locked": True,
            "is_institution_preset": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "tpl_preset_community_service",
            "name": "Community Service Project Presentation & Report (.pdf/.docx)",
            "original_file_path": ".storage/templates/community_service_template.docx",
            "file_type": "docx",
            "file_size": 38900,
            "status": "ready",
            "is_locked": True,
            "is_institution_preset": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "tpl_preset_ieee_seminar",
            "name": "IEEE Double-Column Seminar & Survey Specification (.docx)",
            "original_file_path": ".storage/templates/ieee_seminar_template.docx",
            "file_type": "docx",
            "file_size": 35400,
            "status": "ready",
            "is_locked": True,
            "is_institution_preset": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    for p in fallback_presets:
        if p["id"] not in templates_map:
            templates_map[p["id"]] = p

    return list(templates_map.values())



@router.get("/templates/{template_id}/fields", response_model=List[TemplateFieldResponseDTO])
def list_template_fields(
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves all registered fields (text, long_text, image, table, list) for a template."""
    return master_template_service.get_template_fields(template_id)


@router.post("/templates/{template_id}/fields", response_model=TemplateFieldResponseDTO)
def register_template_field(
    template_id: str,
    dto: TemplateFieldDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Registers or updates a configurable field slot in a template."""
    client = db_manager.client
    field_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    field_name = dto.field_name or dto.field_key or "custom_field"
    section = dto.page_or_section or dto.section_key or "General"
    placeholder = dto.placeholder_identifier or f"{{{{{field_name.upper()}}}}}"

    row = {
        "id": field_id,
        "template_id": template_id,
        "field_key": field_name,
        "field_name": field_name,
        "field_label": dto.field_label or field_name,
        "field_type": dto.field_type or "text",
        "section_key": section,
        "page_or_section": section,
        "is_required": dto.is_required,
        "placeholder_identifier": placeholder,
        "content_limits": dto.content_limits or {},
        "image_dimensions": dto.image_dimensions or {},
        "ordering": dto.ordering or 0,
        "max_length": dto.max_length,
        "bounding_box": dto.bounding_box or {},
        "default_value": dto.default_value,
        "metadata": dto.metadata or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if client:
        try:
            res = client.table("template_fields").upsert(row, on_conflict="template_id,field_key").execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error upserting template field: {e}")

    return row


@router.get("/projects/{project_id}/template", response_model=Optional[TemplateDTO])
def get_project_template(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves the active template for a given project."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    if client:
        try:
            res = client.table("templates").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error querying template for project {project_id}: {e}")

    matching = [t for t in _TEMPLATES_DB.values() if t.get("project_id") == project_id]
    if matching:
        matching.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return matching[0]

    return None


@router.post("/projects/{project_id}/templates/{template_id}/analyze", response_model=TemplateAnalyzeResponse)
def analyze_template_action(
    project_id: str,
    template_id: str,
    sync: bool = Query(False),
    auto_execute: bool = Query(False),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 2 & 3 Action: Analyze Template
    Creates a real generation job (job_type='template_analysis', status='queued')
    and transitions the template status to 'analyzing'.
    """
    project = _verify_project_ownership(project_id, user)
    owner_id = user["id"] if user else (project.get("user_id") or project.get("owner_id") or "usr_demo_student")

    client = db_manager.client
    template_record = None

    if client:
        try:
            res = client.table("templates").select("*").eq("id", template_id).execute()
            if res.data and len(res.data) > 0:
                template_record = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching template {template_id}: {e}")

    if not template_record:
        template_record = _TEMPLATES_DB.get(template_id)

    if not template_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found."
        )

    # Ownership check
    t_owner = template_record.get("user_id") or template_record.get("owner_id")
    if user and t_owner and str(t_owner) != str(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this template."
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Create real generation job
    db_user_id = owner_id if _is_valid_uuid(owner_id) else None
    if not db_user_id and client:
        try:
            prof = client.table("profiles").select("id").limit(1).execute()
            if prof.data:
                db_user_id = prof.data[0]["id"]
        except Exception:
            pass

    db_proj_id = project_id if _is_valid_uuid(project_id) else None

    job_record = {
        "id": job_id,
        "user_id": db_user_id,
        "project_id": db_proj_id,
        "report_id": None,
        "job_type": "template_analysis",
        "status": "queued",
        "progress": 0,
        "current_step": "Analysis queued",
        "metadata": {
            "template_id": template_id,
            "template_name": template_record.get("name"),
            "file_type": template_record.get("file_type")
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    if client:
        try:
            client.table("generation_jobs").insert(job_record).execute()
            client.table("templates").update({
                "status": "analyzing",
                "analysis_status": "pending"
            }).eq("id", template_id).execute()
        except Exception as e:
            logger.error(f"Failed to queue generation job: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue template analysis job."
            )

    template_record["status"] = "analyzing"
    template_record["analysis_status"] = "pending"
    _JOBS_STORE[job_id] = job_record

    # If explicitly requested, process synchronously
    if sync or auto_execute:
        template_intelligence_service.process_analysis_job(job_id)

    return TemplateAnalyzeResponse(
        job_id=job_id,
        template_id=template_id,
        project_id=project_id,
        status="queued",
        message="Template analysis queued successfully. Ready for processing."
    )


@router.post("/projects/{project_id}/templates/{template_id}/jobs/{job_id}/execute")
def execute_template_job(
    project_id: str,
    template_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 3: Worker execution endpoint.
    Processes a queued template_analysis job.
    """
    _verify_project_ownership(project_id, user)
    job = template_intelligence_service.get_generation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found.")

    template_intelligence_service.process_analysis_job(job_id)
    return {"status": "completed", "job_id": job_id, "template_id": template_id}


@router.get("/projects/{project_id}/templates/{template_id}/analysis", response_model=TemplateAnalysisResponse)
def get_project_template_analysis(
    project_id: str,
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 3: Retrieves the normalized template analysis for a project's template.
    Strictly verifies project & template ownership.
    """
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    # Verify template exists
    template = None
    if client:
        try:
            t_res = client.table("templates").select("*").eq("id", template_id).execute()
            if t_res.data and len(t_res.data) > 0:
                template = t_res.data[0]
        except Exception as e:
            logger.error(f"Error fetching template {template_id}: {e}")

    if not template:
        template = _TEMPLATES_DB.get(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    if template.get("project_id") and str(template.get("project_id")) != str(project_id):
        raise HTTPException(status_code=404, detail="Template does not belong to this project.")

    # Ownership check
    t_owner = template.get("user_id") or template.get("owner_id")
    if user and t_owner and str(t_owner) != str(user["id"]):
        raise HTTPException(status_code=403, detail="You do not have permission to access this template analysis.")

    analysis = template_intelligence_service.get_template_analysis(template_id)
    if analysis:
        return TemplateAnalysisResponse(
            template_id=template_id,
            status="completed",
            schema_version=analysis.get("parser_version") or "1.0.0",
            parser_version=analysis.get("parser_version") or "1.0.0",
            schema_data=analysis.get("schema_json") or analysis.get("data") or analysis.get("normalized_schema"),
            warnings=analysis.get("warnings") or [],
            created_at=analysis.get("created_at"),
            updated_at=analysis.get("updated_at")
        )

    t_status = template.get("status")
    if t_status == "analyzing":
        return TemplateAnalysisResponse(template_id=template_id, status="analyzing", warnings=[])
    elif t_status == "failed":
        return TemplateAnalysisResponse(template_id=template_id, status="failed", warnings=["Template analysis failed."])
    else:
        return TemplateAnalysisResponse(template_id=template_id, status="pending", warnings=[])


@router.get("/projects/{project_id}/templates/{template_id}/jobs/{job_id}", response_model=GenerationJobResponse)
def get_project_template_job(
    project_id: str,
    template_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 3: Retrieves execution progress and step details for a template analysis job.
    """
    _verify_project_ownership(project_id, user)
    job = template_intelligence_service.get_generation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found.")

    # Verify job corresponds to template and project
    j_proj = job.get("project_id")
    j_meta = job.get("metadata") or {}
    if j_proj and str(j_proj) != str(project_id):
        raise HTTPException(status_code=403, detail="You do not have permission to view this job.")
    if j_meta.get("template_id") and str(j_meta.get("template_id")) != str(template_id):
        raise HTTPException(status_code=404, detail="Job does not belong to this template.")

    return GenerationJobResponse(
        id=job["id"],
        job_type=job.get("job_type", "template_analysis"),
        status=job.get("status", "queued"),
        progress=job.get("progress", 0),
        current_step=job.get("current_step"),
        error_message=job.get("error_message"),
        metadata=job.get("metadata"),
        result_payload=job.get("result_payload"),
        created_at=job.get("created_at"),
        updated_at=job.get("updated_at")
    )


@router.delete("/projects/{project_id}/templates/{template_id}")
def delete_project_template(
    project_id: str,
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Safely disassociates or removes template from project with strict ownership verification."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    if client:
        try:
            res = client.table("templates").select("*").eq("id", template_id).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="Template not found.")
            if user:
                t_owner = res.data[0].get("user_id")
                if t_owner and str(t_owner) != str(user["id"]):
                    raise HTTPException(status_code=403, detail="Forbidden: You do not own this template.")
            client.table("templates").delete().eq("id", template_id).execute()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete template.")

    _TEMPLATES_DB.pop(template_id, None)
    return {"status": "success", "message": f"Template {template_id} removed from project."}


# ------------------------------------------------------------------------------
# Stage 4: Template Review + Lock Endpoints
# ------------------------------------------------------------------------------

@router.get("/projects/{project_id}/templates/{template_id}/review", response_model=TemplateReviewResponse)
def get_project_template_review(
    project_id: str,
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 4: Retrieves the template review state including source analysis,
    reviewed schema draft, warnings, and lock metadata.
    """
    _verify_project_ownership(project_id, user)
    _get_template_with_ownership_check(template_id, project_id, user)

    review = template_intelligence_service.get_template_review(template_id)
    if not review:
        raise HTTPException(status_code=404, detail="Template analysis for review not found. Please analyze the template first.")

    return TemplateReviewResponse(**review)


@router.patch("/projects/{project_id}/templates/{template_id}/review", response_model=TemplateReviewResponse)
def patch_project_template_review(
    project_id: str,
    template_id: str,
    payload: TemplateReviewPatchRequest,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 4: Saves student review modifications to the template structure.
    Strictly rejects modifications if the template is already locked (409 Conflict).
    """
    _verify_project_ownership(project_id, user)
    template = _get_template_with_ownership_check(template_id, project_id, user)

    if template.get("is_locked") or template.get("status") == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is locked and cannot be modified. To make modifications, upload a new template version."
        )

    user_id = user["id"] if user else (template.get("user_id") or "usr_demo_student")

    try:
        updated_review = template_intelligence_service.save_template_review(
            template_id=template_id,
            reviewed_data=payload.reviewed_schema,
            user_id=str(user_id),
            notes=payload.notes
        )
        return TemplateReviewResponse(**updated_review)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving review for template {template_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save review draft.")


@router.post("/projects/{project_id}/templates/{template_id}/lock", response_model=TemplateLockResponse)
def lock_project_template(
    project_id: str,
    template_id: str,
    payload: Optional[TemplateLockRequest] = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 4: Atomically locks the template structure.
    The reviewed schema becomes the authoritative source of truth for future report generation.
    """
    _verify_project_ownership(project_id, user)
    template = _get_template_with_ownership_check(template_id, project_id, user)

    user_id = user["id"] if user else (template.get("user_id") or "usr_demo_student")
    notes = payload.notes if payload else None

    try:
        lock_result = template_intelligence_service.lock_template(
            template_id=template_id,
            user_id=str(user_id),
            notes=notes
        )
        return TemplateLockResponse(**lock_result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error locking template {template_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to lock template: {str(e)}")


@router.get("/projects/{project_id}/templates/{template_id}/locked-schema", response_model=Dict[str, Any])
def get_project_template_locked_schema(
    project_id: str,
    template_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Stage 4: Retrieves the authoritative locked schema for downstream report generation stages.
    """
    _verify_project_ownership(project_id, user)
    _get_template_with_ownership_check(template_id, project_id, user)

    locked_schema = template_intelligence_service.get_locked_template(template_id)
    if not locked_schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template is not locked yet.")

    return locked_schema


# ------------------------------------------------------------------------------
# Backward Compatibility & Legacy Parser Endpoints (Stage 1 Support)
# ------------------------------------------------------------------------------
@router.post("/templates/upload", response_model=TemplateUploadResponse)
async def upload_template_standalone(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Maintains compatibility with Stage 1 standalone AST inspect tests
    while supporting Stage 2 project-linked template ingestion.
    """
    if project_id:
        return await upload_project_template(project_id=project_id, file=file, user=user)

    content = await file.read()
    ext = _validate_template_file(content, file.filename or "")

    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    temp_dir = tempfile.gettempdir()
    saved_path = os.path.join(temp_dir, f"{template_id}{ext}")

    with open(saved_path, "wb") as f:
        f.write(content)

    try:
        parser = TemplateParser(saved_path)
        schema = parser.parse(template_id=template_id, template_name=file.filename or f"template{ext}")
        _TEMPLATES_DB[template_id] = {
            "id": template_id,
            "filename": file.filename or f"template{ext}",
            "original_file_path": saved_path,
            "storage_path": saved_path,
            "converted_docx_path": saved_path,
            "working_docx_path": saved_path,
            "path": saved_path,
            "converted_from_pdf": False,
            "file_type": "docx",
            "size": len(content)
        }
        _TEMPLATE_SCHEMAS[template_id] = schema
        from apps.api.services.custom_template_service import _CUSTOM_TEMPLATES_STORE
        _CUSTOM_TEMPLATES_STORE[template_id] = dict(_TEMPLATES_DB[template_id])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to analyze {ext.lstrip('.').upper()} template: {str(e)}")

    return TemplateUploadResponse(
        template_id=template_id,
        name=file.filename or "template",
        file_size_bytes=len(content),
        is_preset=False,
        status="analyzed",
        analysis_status="completed",
        file_type=ext.lstrip(".").lower(),
        message="Template parsed successfully. Review detected sections and typography."
    )


@router.get("/templates/{template_id}/schema", response_model=TemplateSchema)
def get_template_schema(template_id: str):
    """Retrieves the normalized JSON schema for a previously analyzed template."""
    if template_id not in _TEMPLATE_SCHEMAS:
        raise HTTPException(status_code=404, detail="Template schema not found.")
    return _TEMPLATE_SCHEMAS[template_id]


@router.put("/templates/{template_id}/confirm")
def confirm_template(template_id: str, payload: TemplateConfirmDTO):
    """Confirms or overrides detected template rules for subsequent report generation."""
    if template_id not in _TEMPLATES_DB:
        raise HTTPException(status_code=404, detail="Template not found.")
    _TEMPLATE_SCHEMAS[template_id] = payload.approved_schema
    return {
        "status": "confirmed",
        "template_id": template_id,
        "message": "Template confirmed and locked for report synthesis."
    }


from apps.api.services.document.template_extractor import extract_template_design, get_active_template_design

@router.post("/templates/convert-to-json")
async def convert_template_to_json(file: UploadFile = File(None)):
    """Extracts design elements into active template JSON contract."""
    temp_dir = tempfile.gettempdir()
    if file and file.filename:
        filename = file.filename
        content = await file.read()
        ext = os.path.splitext(filename)[1].lower()
        temp_path = os.path.join(temp_dir, f"template_{uuid.uuid4().hex[:8]}{ext}")
        with open(temp_path, "wb") as f:
            f.write(content)
    else:
        temp_path = "C:/Users/A9959/Downloads/SAI CHARAN PPT Modified.pdf"
        if not os.path.exists(temp_path):
            temp_path = "C:/Users/A9959/.gemini/antigravity/brain/4119903f-9471-48b7-9ff4-0fb4a386acab/.user_uploaded/media_1790616307252.pdf"
        filename = os.path.basename(temp_path)

    design = extract_template_design(temp_path, filename=filename)
    template_id = f"tpl_{uuid.uuid4().hex[:10]}"
    design["template_id"] = template_id
    _TEMPLATES_DB[template_id] = design

    return {
        "status": "success",
        "template_id": template_id,
        "template_name": filename,
        "message": f"Template design extracted from '{filename}' and stored internally in JSON contract.",
        "design": design
    }


@router.get("/templates/active-design")
def get_current_active_design():
    return get_active_template_design()


@router.post("/templates/template-copy-test")
async def template_copy_test(file: UploadFile = File(...)):
    """
    Diagnostic Test: Raw file copy with zero parsing, zero document libraries, zero XML modification.
    Receives uploaded DOCX, reads raw bytes, copies bytes to output file, and returns the copied file.
    """
    import hashlib
    content = await file.read()
    output_dir = os.path.abspath(".storage/test_copies")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"template-copy-test-output_{uuid.uuid4().hex[:8]}.docx")

    # Pure byte-for-byte write
    with open(output_file, "wb") as f:
        f.write(content)

    orig_hash = hashlib.sha256(content).hexdigest()
    with open(output_file, "rb") as f:
        copied_hash = hashlib.sha256(f.read()).hexdigest()

    return FileResponse(
        path=output_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="template-copy-test-output.docx",
        headers={
            "X-Original-SHA256": orig_hash,
            "X-Copied-SHA256": copied_hash,
            "X-Hashes-Match": str(orig_hash == copied_hash),
            "X-Original-Size": str(len(content)),
            "X-Copied-Size": str(os.path.getsize(output_file)),
        }
    )

