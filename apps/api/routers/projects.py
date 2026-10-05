"""
ReportForge AI - Projects, Members & Evidence Router
Stage 5: Project Information + Evidence Locker
"""

import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from apps.api.schemas.project import (
    ProjectCreateDTO,
    ProjectUpdateDTO,
    ProjectResponseDTO,
    ProjectMemberCreateDTO,
    ProjectMemberUpdateDTO,
    ProjectMemberResponseDTO,
    EvidenceResponseDTO,
    EvidenceUpdateDTO,
    ProjectReadinessDTO,
)
from apps.api.schemas.report import (
    ReportPlan,
    PlanReportRequestDTO,
    ApprovePlanRequestDTO,
    ReportCreateDTO,
    ReportResponseDTO,
    GeneratedContentCreateDTO,
    GeneratedContentResponseDTO,
    ReportAssetCreateDTO,
    ReportAssetResponseDTO,
)
from packages.report_generator import GeneratedReport
from packages.citation_verifier import ReportVerificationReport
from apps.api.services.citation_verification import get_citation_verification_service, CitationVerificationService
from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.core.auth import get_current_user_optional
from apps.api.services.storage import get_storage_provider
from apps.api.services.ai import get_ai_provider, AIProvider

logger = get_logger("projects")
router = APIRouter(prefix="/projects", tags=["Projects"])

# In-memory fallbacks
_PROJECTS_STORE: Dict[str, Any] = {}
_MEMBERS_STORE: Dict[str, Dict[str, Any]] = {}
_EVIDENCE_STORE: Dict[str, Dict[str, Any]] = {}
_EVIDENCE_BYTES_STORE: Dict[str, bytes] = {}

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}

MAX_EVIDENCE_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def _verify_project_ownership(project_id: str, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to verify project existence and authenticated user ownership."""
    client = db_manager.client
    project_data = None
    if client:
        try:
            res = client.table("projects").select("*").eq("id", project_id).execute()
            if res.data and len(res.data) > 0:
                project_data = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}")

    if not project_data:
        project_data = _PROJECTS_STORE.get(project_id)

    if not project_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if user:
        owner = project_data.get("user_id") or project_data.get("owner_id")
        if owner and str(owner) != str(user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this project."
            )

    return project_data


def _enrich_project_summary(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches project record with template name, generation status, and latest report summary.
    """
    res = dict(p)
    proj_id = p.get("id")

    # 1. Resolve template name
    template_id = p.get("template_id")
    template_name = "Master College Template (Standard IEEE)"
    if template_id and template_id != "master-college-template":
        client = db_manager.client
        if client:
            try:
                t_res = client.table("templates").select("name, title").eq("id", template_id).execute()
                if t_res.data:
                    template_name = t_res.data[0].get("name") or t_res.data[0].get("title") or template_name
            except Exception:
                pass
        if template_name == "Master College Template (Standard IEEE)":
            try:
                from apps.api.services.custom_template_service import custom_template_service
                cust = custom_template_service.get_template(template_id)
                if cust:
                    template_name = cust.get("name") or template_name
            except Exception:
                pass
    res["template_name"] = template_name

    # 2. Check for latest replacement job
    from apps.api.services.replacement_engine_service import _REPLACEMENT_JOBS
    matching_jobs = [j for j in _REPLACEMENT_JOBS.values() if j.get("project_id") == proj_id]
    latest_job = matching_jobs[-1] if matching_jobs else None

    # 3. Check for reports record in DB
    report_record = None
    client = db_manager.client
    if client and proj_id:
        try:
            r_res = client.table("reports").select("*").eq("project_id", proj_id).order("updated_at", desc=True).limit(1).execute()
            if r_res.data:
                report_record = r_res.data[0]
        except Exception:
            pass

    # 4. Synthesize generation_status and latest_report
    if latest_job:
        res["latest_job_id"] = latest_job.get("job_id")
        res["generation_status"] = latest_job.get("state", "COMPLETED").lower()
        stats = latest_job.get("stats", {})
        res["latest_report"] = {
            "id": latest_job.get("job_id"),
            "title": p.get("title") or "Academic Report",
            "version": 1,
            "status": latest_job.get("state", "COMPLETED"),
            "approval_status": latest_job.get("approval_status", "pending"),
            "approved_at": latest_job.get("approved_at"),
            "word_count": stats.get("estimated_word_count"),
            "page_count": stats.get("page_count", 1),
            "docx_url": f"/api/v1/replacement/download/{latest_job['job_id']}?format=docx",
            "pdf_url": f"/api/v1/replacement/download/{latest_job['job_id']}?format=pdf" if latest_job.get("pdf_path") else None,
            "updated_at": latest_job.get("updated_at") or p.get("updated_at"),
        }
    elif report_record:
        rep_status = report_record.get("status", "draft")
        res["generation_status"] = rep_status
        res["latest_report"] = {
            "id": report_record.get("id"),
            "title": report_record.get("title") or p.get("title") or "Academic Report",
            "version": report_record.get("current_version", 1),
            "status": rep_status,
            "approval_status": report_record.get("status") if report_record.get("status") in ("approved", "pending") else "pending",
            "word_count": report_record.get("total_word_count"),
            "page_count": report_record.get("page_count", 1),
            "docx_url": f"/api/v1/projects/{proj_id}/report/download-docx",
            "pdf_url": None,
            "updated_at": report_record.get("updated_at") or p.get("updated_at"),
        }
    else:
        res["generation_status"] = p.get("status") or "not_started"
        res["latest_report"] = None
        res["latest_job_id"] = None

    return res



# ==============================================================================
# 1. PROJECT CRUD & INFORMATION ENDPOINTS
# ==============================================================================

@router.post("", response_model=ProjectResponseDTO)
def create_project(
    dto: ProjectCreateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    client = db_manager.client
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    title = dto.title or dto.project_name or "Untitled Project"

    owner_id = user["id"] if user else None
    if not owner_id and client:
        try:
            prof_res = client.table("profiles").select("id").limit(1).execute()
            if prof_res.data:
                owner_id = prof_res.data[0]["id"]
        except Exception:
            pass

    row = {
        "id": project_id,
        "user_id": owner_id or (user["id"] if user else "usr_demo_student"),
        "owner_id": owner_id or (user["id"] if user else "usr_demo_student"),
        "title": title,
        "project_name": title,
        "report_title": dto.report_title or title,
        "report_type": dto.report_type or "report",
        "project_type": dto.project_type or "capstone",
        "description": dto.description,
        "academic_year": dto.academic_year or "2026-2027",
        "department": dto.department,
        "institution": dto.institution,
        "semester": dto.semester,
        "guide_name": dto.guide_name,
        "abstract_summary": dto.abstract_summary,
        "problem_statement": dto.problem_statement,
        "objectives": dto.objectives,
        "scope": dto.scope,
        "methodology": dto.methodology,
        "expected_outcome": dto.expected_outcome,
        "actual_outcome": dto.actual_outcome,
        "start_date": dto.start_date,
        "end_date": dto.end_date,
        "additional_notes": dto.additional_notes,
        "instructions": dto.instructions or dto.additional_notes,
        "template_id": dto.template_id,
        "is_team_project": dto.is_team_project or False,
        "target_page_count": dto.target_page_count or 30,
        "tech_stack": dto.tech_stack or [],
        "status": "draft",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    if client:
        try:
            res = client.table("projects").insert(row).execute()
            if res.data and len(res.data) > 0:
                _PROJECTS_STORE[project_id] = res.data[0]
                # Initialize report if template_id was selected
                if dto.template_id:
                    try:
                        tpl_uuid = dto.template_id if len(str(dto.template_id)) == 36 else None
                        client.table("reports").insert({
                            "id": str(uuid.uuid4()),
                            "project_id": project_id,
                            "template_id": tpl_uuid,
                            "title": title,
                            "report_type": dto.project_type or dto.report_type or "capstone",
                            "current_version": 1,
                            "status": "planning",
                            "user_id": owner_id or (user["id"] if user else "usr_demo_student"),
                            "created_at": now.isoformat(),
                            "updated_at": now.isoformat(),
                        }).execute()
                    except Exception as re_err:
                        logger.warn(f"Initial report auto-creation note: {re_err}")
                return res.data[0]
        except Exception as e:
            logger.error(f"Error persisting project: {e}")

    _PROJECTS_STORE[project_id] = row
    return row


@router.get("", response_model=List[ProjectResponseDTO])
def list_projects(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    Returns academic projects for the authenticated user only.
    Prevents unauthorized exposure of other users' projects.
    """
    client = db_manager.client
    if client:
        try:
            if user:
                query = client.table("projects").select("*").or_(f"user_id.eq.{user['id']},owner_id.eq.{user['id']}")
                res = query.order("updated_at", desc=True).execute()
                if res.data is not None:
                    return [_enrich_project_summary(p) for p in res.data]
            else:
                return []
        except Exception as e:
            logger.error(f"Error listing projects: {e}")

    if user:
        user_id_str = str(user["id"])
        matching = [
            p for p in _PROJECTS_STORE.values()
            if str(p.get("owner_id")) == user_id_str or str(p.get("user_id")) == user_id_str
        ]
        return [_enrich_project_summary(p) for p in matching]

    return []


@router.get("/{project_id}", response_model=ProjectResponseDTO)
def get_project(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    project = _verify_project_ownership(project_id, user)
    return _enrich_project_summary(project)


@router.patch("/{project_id}", response_model=ProjectResponseDTO)
def update_project(
    project_id: str,
    dto: ProjectUpdateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    project = _verify_project_ownership(project_id, user)
    now = datetime.now(timezone.utc)

    # Extract non-None updates
    update_data: Dict[str, Any] = {"updated_at": now.isoformat()}
    for field, val in dto.model_dump(exclude_unset=True).items():
        if val is not None:
            update_data[field] = val

    if "title" in update_data and not update_data.get("project_name"):
        update_data["project_name"] = update_data["title"]
    elif "project_name" in update_data and not update_data.get("title"):
        update_data["title"] = update_data["project_name"]

    client = db_manager.client
    if client:
        try:
            res = client.table("projects").update(update_data).eq("id", project_id).execute()
            if res.data and len(res.data) > 0:
                updated = res.data[0]
                _PROJECTS_STORE[project_id] = updated
                return updated
        except Exception as e:
            logger.error(f"Error updating project in DB: {e}")

    # Fallback in-memory
    project.update(update_data)
    _PROJECTS_STORE[project_id] = project
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)

    client = db_manager.client
    if client:
        try:
            # Delete related child records if any exist
            try:
                client.table("reports").delete().eq("project_id", project_id).execute()
                client.table("report_assets").delete().eq("project_id", project_id).execute()
                client.table("evidence_files").delete().eq("project_id", project_id).execute()
            except Exception:
                pass
            client.table("projects").delete().eq("id", project_id).execute()
        except Exception as e:
            logger.error(f"Error deleting project: {e}")

    _PROJECTS_STORE.pop(project_id, None)
    return {"status": "success", "message": f"Project {project_id} deleted."}


@router.post("/{project_id}/regenerate")
def regenerate_project_report(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Triggers in-place template replacement regeneration for this project."""
    project = _verify_project_ownership(project_id, user)
    from apps.api.services.replacement_engine_service import replacement_engine_service
    return replacement_engine_service.execute_replacement(
        project_id=project_id,
        template_id=project.get("template_id"),
        project_data=project,
    )


# ==============================================================================
# 2. PROJECT READINESS INDICATOR
# ==============================================================================

@router.get("/{project_id}/readiness", response_model=ProjectReadinessDTO)
def get_project_readiness(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    project = _verify_project_ownership(project_id, user)
    client = db_manager.client

    # 1. Template Lock Status
    template_locked = False
    if client:
        try:
            t_res = client.table("templates").select("id, is_locked, status").eq("project_id", project_id).execute()
            if t_res.data:
                for t in t_res.data:
                    if t.get("is_locked") is True or t.get("status") == "locked":
                        template_locked = True
                        break
        except Exception as e:
            logger.error(f"Error querying template lock status: {e}")

    if not template_locked:
        from apps.api.routers.templates import _TEMPLATES_DB
        for t in _TEMPLATES_DB.values():
            if str(t.get("project_id")) == str(project_id) and (t.get("is_locked") is True or t.get("status") == "locked"):
                template_locked = True
                break

    # 2. Project Information Completeness
    required_fields = ["title", "problem_statement", "objectives", "guide_name"]
    optional_fields = ["department", "institution", "academic_year", "methodology", "expected_outcome"]
    missing_fields = []
    filled_count = 0

    for f in required_fields:
        val = project.get(f)
        if not val or not str(val).strip():
            missing_fields.append(f)
        else:
            filled_count += 1

    for f in optional_fields:
        val = project.get(f)
        if val and str(val).strip():
            filled_count += 1

    info_completed = len(missing_fields) == 0

    # 3. Evidence Count
    evidence_count = 0
    if client:
        try:
            f_res = client.table("project_files").select("id", count="exact").eq("project_id", project_id).execute()
            if f_res.count is not None:
                evidence_count = f_res.count
            elif f_res.data:
                evidence_count = len(f_res.data)
        except Exception as e:
            logger.error(f"Error counting project files: {e}")

    if evidence_count == 0:
        evidence_count = sum(1 for e in _EVIDENCE_STORE.values() if str(e.get("project_id")) == str(project_id))

    # 4. Members Count
    members_count = 0
    if client:
        try:
            m_res = client.table("project_members").select("id", count="exact").eq("project_id", project_id).execute()
            if m_res.count is not None:
                members_count = m_res.count
            elif m_res.data:
                members_count = len(m_res.data)
        except Exception as e:
            logger.error(f"Error counting project members: {e}")

    if members_count == 0:
        members_count = sum(1 for m in _MEMBERS_STORE.values() if str(m.get("project_id")) == str(project_id))

    # Calculate completion percentage
    # - Template locked: 40%
    # - Info completeness: up to 40% (based on 9 fields)
    # - Evidence count (>0): 10%
    # - Members count (>0): 10%
    score = 0
    if template_locked:
        score += 40
    score += int((filled_count / (len(required_fields) + len(optional_fields))) * 40)
    if evidence_count > 0:
        score += 10
    if members_count > 0:
        score += 10

    score = min(100, score)
    is_ready = bool(template_locked and info_completed)

    return ProjectReadinessDTO(
        project_id=project_id,
        template_locked=template_locked,
        info_completed=info_completed,
        evidence_count=evidence_count,
        members_count=members_count,
        is_ready_for_generation=is_ready,
        missing_fields=missing_fields,
        completion_percentage=score
    )


# ==============================================================================
# 3. PROJECT MEMBERS ENDPOINTS
# ==============================================================================

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponseDTO])
def list_project_members(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    if client:
        try:
            res = client.table("project_members").select("*").eq("project_id", project_id).order("created_at", desc=False).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            logger.error(f"Error listing project members: {e}")

    return [m for m in _MEMBERS_STORE.values() if str(m.get("project_id")) == str(project_id)]


@router.post("/{project_id}/members", response_model=ProjectMemberResponseDTO)
def add_project_member(
    project_id: str,
    dto: ProjectMemberCreateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    if not dto.name or not dto.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member name is required and cannot be empty.")

    member_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = {
        "id": member_id,
        "project_id": project_id,
        "user_id": user["id"] if user else None,
        "name": dto.name.strip(),
        "roll_number": dto.roll_number.strip() if dto.roll_number else None,
        "email": dto.email.strip() if dto.email else None,
        "role": dto.role.strip() if dto.role else "Member",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    client = db_manager.client
    if client:
        try:
            res = client.table("project_members").insert(row).execute()
            if res.data and len(res.data) > 0:
                _MEMBERS_STORE[member_id] = res.data[0]
                return res.data[0]
        except Exception as e:
            logger.error(f"Error inserting member: {e}")

    _MEMBERS_STORE[member_id] = row
    return row


@router.patch("/{project_id}/members/{member_id}", response_model=ProjectMemberResponseDTO)
def update_project_member(
    project_id: str,
    member_id: str,
    dto: ProjectMemberUpdateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    now = datetime.now(timezone.utc)

    # Check member exists and belongs to project
    client = db_manager.client
    member = None
    if client:
        try:
            res = client.table("project_members").select("*").eq("id", member_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                member = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching member: {e}")

    if not member:
        member = _MEMBERS_STORE.get(member_id)

    if not member or str(member.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

    update_data: Dict[str, Any] = {"updated_at": now.isoformat()}
    if dto.name is not None:
        if not dto.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member name cannot be empty.")
        update_data["name"] = dto.name.strip()
    if dto.roll_number is not None:
        update_data["roll_number"] = dto.roll_number.strip() if dto.roll_number else None
    if dto.email is not None:
        update_data["email"] = dto.email.strip() if dto.email else None
    if dto.role is not None:
        update_data["role"] = dto.role.strip() if dto.role else "Member"

    if client:
        try:
            res = client.table("project_members").update(update_data).eq("id", member_id).execute()
            if res.data and len(res.data) > 0:
                updated = res.data[0]
                _MEMBERS_STORE[member_id] = updated
                return updated
        except Exception as e:
            logger.error(f"Error updating member: {e}")

    member.update(update_data)
    _MEMBERS_STORE[member_id] = member
    return member


@router.delete("/{project_id}/members/{member_id}")
def delete_project_member(
    project_id: str,
    member_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    member = None
    if client:
        try:
            res = client.table("project_members").select("*").eq("id", member_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                member = res.data[0]
        except Exception as e:
            logger.error(f"Error finding member: {e}")

    if not member:
        member = _MEMBERS_STORE.get(member_id)

    if not member or str(member.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

    if client:
        try:
            client.table("project_members").delete().eq("id", member_id).execute()
        except Exception as e:
            logger.error(f"Error deleting member: {e}")

    _MEMBERS_STORE.pop(member_id, None)
    return {"status": "success", "message": "Member removed successfully."}


# ==============================================================================
# 4. EVIDENCE LOCKER ENDPOINTS
# ==============================================================================

@router.get("/{project_id}/evidence", response_model=List[EvidenceResponseDTO])
def list_project_evidence(
    project_id: str,
    category: Optional[str] = Query(None, description="Optional category filter"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    if client:
        try:
            query = client.table("project_files").select("*").eq("project_id", project_id)
            if category:
                query = query.eq("category", category)
            res = query.order("created_at", desc=True).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            logger.error(f"Error listing evidence: {e}")

    results = [e for e in _EVIDENCE_STORE.values() if str(e.get("project_id")) == str(project_id)]
    if category:
        results = [e for e in results if e.get("category") == category]
    return sorted(results, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/{project_id}/evidence", response_model=EvidenceResponseDTO)
async def upload_project_evidence(
    project_id: str,
    file: UploadFile = File(...),
    category: Optional[str] = Form("other"),
    description: Optional[str] = Form(None),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    project = _verify_project_ownership(project_id, user)
    owner_id = user["id"] if user else (project.get("user_id") or project.get("owner_id") or "usr_demo_student")

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename must be provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EVIDENCE_EXTENSIONS.keys()))}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if len(content) > MAX_EVIDENCE_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {MAX_EVIDENCE_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    sha256_hash = hashlib.sha256(content).hexdigest()
    mime_type = ALLOWED_EVIDENCE_EXTENSIONS.get(ext, file.content_type or "application/octet-stream")
    evidence_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Isolated Storage Path
    safe_filename = os.path.basename(file.filename)
    storage_path = f"users/{owner_id}/projects/{project_id}/evidence/{evidence_id}/{safe_filename}"

    # Store file bytes
    storage_provider = get_storage_provider()
    try:
        storage_provider.upload_file(
            bucket=settings.storage.bucket_evidence,
            path=storage_path,
            data=content,
            content_type=mime_type
        )
    except Exception as e:
        logger.warning(f"Storage upload note: {e}")

    _EVIDENCE_BYTES_STORE[evidence_id] = content

    category_clean = (category.strip().lower() if category else "other")
    row = {
        "id": evidence_id,
        "project_id": project_id,
        "user_id": owner_id,
        "file_name": safe_filename,
        "file_type": ext.lstrip(".") or "evidence",
        "mime_type": mime_type,
        "file_size_bytes": len(content),
        "file_size": len(content),
        "storage_path": storage_path,
        "sha256_hash": sha256_hash,
        "category": category_clean,
        "description": description.strip() if description else None,
        "upload_status": "ready",
        "processing_status": "ready",
        "processing_error": None,
        "metadata": {
            "original_name": file.filename,
            "content_type": mime_type,
            "sha256": sha256_hash,
            "size_bytes": len(content),
            "category": category_clean,
            "description": description.strip() if description else None,
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    client = db_manager.client
    if client:
        try:
            res = client.table("project_files").insert(row).execute()
            if res.data and len(res.data) > 0:
                _EVIDENCE_STORE[evidence_id] = res.data[0]
                return res.data[0]
        except Exception as e:
            logger.error(f"Error persisting evidence in DB: {e}")

    _EVIDENCE_STORE[evidence_id] = row
    return row


@router.get("/{project_id}/evidence/{evidence_id}", response_model=EvidenceResponseDTO)
def get_project_evidence(
    project_id: str,
    evidence_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    evidence = None
    if client:
        try:
            res = client.table("project_files").select("*").eq("id", evidence_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                evidence = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching evidence: {e}")

    if not evidence:
        evidence = _EVIDENCE_STORE.get(evidence_id)

    if not evidence or str(evidence.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    return evidence


@router.get("/{project_id}/evidence/{evidence_id}/download")
def download_project_evidence(
    project_id: str,
    evidence_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    evidence = None
    if client:
        try:
            res = client.table("project_files").select("*").eq("id", evidence_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                evidence = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching evidence for download: {e}")

    if not evidence:
        evidence = _EVIDENCE_STORE.get(evidence_id)

    if not evidence or str(evidence.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    # Retrieve file bytes
    content: Optional[bytes] = _EVIDENCE_BYTES_STORE.get(evidence_id)
    if not content:
        storage_provider = get_storage_provider()
        try:
            content = storage_provider.download_file(
                bucket=settings.storage.bucket_evidence,
                path=evidence.get("storage_path")
            )
        except Exception as e:
            logger.error(f"Error downloading from storage: {e}")

    if not content:
        # Fallback if bytes were not stored
        content = b""

    mime = evidence.get("mime_type") or "application/octet-stream"
    fname = evidence.get("file_name") or "evidence.bin"

    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@router.patch("/{project_id}/evidence/{evidence_id}", response_model=EvidenceResponseDTO)
def update_project_evidence(
    project_id: str,
    evidence_id: str,
    dto: EvidenceUpdateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    evidence = None
    if client:
        try:
            res = client.table("project_files").select("*").eq("id", evidence_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                evidence = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching evidence for update: {e}")

    if not evidence:
        evidence = _EVIDENCE_STORE.get(evidence_id)

    if not evidence or str(evidence.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    now = datetime.now(timezone.utc)
    update_data: Dict[str, Any] = {"updated_at": now.isoformat()}
    if dto.category is not None:
        update_data["category"] = dto.category.strip().lower()
    if dto.description is not None:
        update_data["description"] = dto.description.strip()

    if client:
        try:
            res = client.table("project_files").update(update_data).eq("id", evidence_id).execute()
            if res.data and len(res.data) > 0:
                updated = res.data[0]
                _EVIDENCE_STORE[evidence_id] = updated
                return updated
        except Exception as e:
            logger.error(f"Error updating evidence: {e}")

    evidence.update(update_data)
    _EVIDENCE_STORE[evidence_id] = evidence
    return evidence


@router.delete("/{project_id}/evidence/{evidence_id}")
def delete_project_evidence(
    project_id: str,
    evidence_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    client = db_manager.client

    evidence = None
    if client:
        try:
            res = client.table("project_files").select("*").eq("id", evidence_id).eq("project_id", project_id).execute()
            if res.data and len(res.data) > 0:
                evidence = res.data[0]
        except Exception as e:
            logger.error(f"Error finding evidence to delete: {e}")

    if not evidence:
        evidence = _EVIDENCE_STORE.get(evidence_id)

    if not evidence or str(evidence.get("project_id")) != str(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    # Remove from storage
    storage_provider = get_storage_provider()
    try:
        storage_path = evidence.get("storage_path")
        if storage_path:
            storage_provider.delete_file(bucket=settings.storage.bucket_evidence, path=storage_path)
    except Exception as e:
        logger.warning(f"Storage delete warning: {e}")

    if client:
        try:
            client.table("project_files").delete().eq("id", evidence_id).execute()
        except Exception as e:
            logger.error(f"Error deleting evidence from DB: {e}")

    _EVIDENCE_STORE.pop(evidence_id, None)
    _EVIDENCE_BYTES_STORE.pop(evidence_id, None)
    return {"status": "success", "message": "Evidence deleted successfully."}


# ==============================================================================
# 5. AI REPORT PLANNER ENDPOINTS (Stage 6)
# ==============================================================================

@router.post("/{project_id}/report-plan", response_model=ReportPlan)
def plan_project_report(
    project_id: str,
    dto: Optional[PlanReportRequestDTO] = None,
    sync: bool = Query(True, description="Synchronous execution"),
    force: bool = Query(False, description="Force regeneration, bypassing cache"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    ai_provider: AIProvider = Depends(get_ai_provider)
):
    _verify_project_ownership(project_id, user)
    force_flag = force or (dto.force if dto else False)
    target_pages = dto.target_page_count if dto else None

    from apps.api.services.report_planner import report_planner_service
    plan = report_planner_service.create_report_plan(
        project_id=project_id,
        user=user,
        force=force_flag,
        ai_provider=ai_provider,
        target_page_count=target_pages
    )
    return plan


@router.get("/{project_id}/report-plan", response_model=ReportPlan)
def get_project_report_plan(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_planner import report_planner_service
    plan = report_planner_service.get_latest_plan(project_id=project_id, user=user)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report plan found for this project. Trigger report planning first."
        )
    return plan


@router.post("/{project_id}/report-plan/approve", response_model=ReportPlan)
def approve_project_report_plan(
    project_id: str,
    dto: Optional[ApprovePlanRequestDTO] = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_planner import report_planner_service
    plan = report_planner_service.get_latest_plan(project_id=project_id, user=user)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report plan found to approve."
        )
    plan_id = dto.plan_id if (dto and dto.plan_id) else plan.plan_id
    updated_plan = report_planner_service.approve_plan(project_id=project_id, plan_id=plan_id, user=user)
    return updated_plan


@router.get("/{project_id}/report-plan/jobs/{job_id}")
def get_planning_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_planner import report_planner_service
    return report_planner_service.get_job(project_id=project_id, job_id=job_id, user=user)


# ==============================================================================
# 6. AI REPORT GENERATION ENDPOINTS (Stage 7)
# ==============================================================================

class GenerateReportDraftDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    force: bool = False


@router.post("/{project_id}/generate-report", response_model=GeneratedReport)
def generate_project_report(
    project_id: str,
    dto: Optional[GenerateReportDraftDTO] = None,
    force: bool = Query(False, description="Force regeneration of report draft"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    ai_provider: AIProvider = Depends(get_ai_provider)
):
    """
    Executes section-by-section AI report generation grounded in locked template,
    approved report plan, project facts, and evidence inventory.
    """
    _verify_project_ownership(project_id, user)
    force_flag = force or (dto.force if dto else False)

    from apps.api.services.report_generation import report_generation_service
    report = report_generation_service.generate_report(
        project_id=project_id,
        user=user,
        force=force_flag,
        ai_provider=ai_provider
    )
    return report


@router.get("/{project_id}/report", response_model=GeneratedReport)
def get_latest_project_report(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves the latest generated report draft for a project."""
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_generation import report_generation_service
    report = report_generation_service.get_latest_report(project_id=project_id, user=user)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generated report found for this project. Trigger generation first."
        )
    return report


@router.get("/{project_id}/report/versions")
def list_project_report_versions(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Lists all version history summaries for this report."""
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_generation import report_generation_service
    return report_generation_service.get_report_versions(project_id=project_id, user=user)


@router.get("/{project_id}/report/versions/{version_number}", response_model=GeneratedReport)
def get_project_report_version(
    project_id: str,
    version_number: int,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves a specific historical version of the report."""
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_generation import report_generation_service
    report = report_generation_service.get_report_version(
        project_id=project_id,
        version_number=version_number,
        user=user
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report version {version_number} not found."
        )
    return report


@router.get("/{project_id}/report/jobs/{job_id}")
def get_report_generation_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves the status and step progress for a content generation job."""
    _verify_project_ownership(project_id, user)
    from apps.api.services.report_generation import report_generation_service
    return report_generation_service.get_job(project_id=project_id, job_id=job_id, user=user)


# ==============================================================================
# STAGE 8: CITATION + EVIDENCE VERIFICATION ENDPOINTS
# ==============================================================================

@router.post("/{project_id}/report/verify", response_model=ReportVerificationReport)
def verify_project_report(
    project_id: str,
    version_number: Optional[int] = Query(None, description="Specific report version to verify (defaults to current)"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service)
):
    """Triggers citation and evidence verification on the generated report draft."""
    _verify_project_ownership(project_id, user)
    user_id = user.get("id") if user else None
    return verification_service.verify_project_report(
        project_id=project_id,
        user_id=user_id,
        version_number=version_number
    )


@router.get("/{project_id}/report/verification", response_model=Optional[ReportVerificationReport])
def get_latest_project_report_verification(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service)
):
    """Retrieves the latest verification report for the project's current report draft."""
    _verify_project_ownership(project_id, user)
    user_id = user.get("id") if user else None
    return verification_service.get_latest_verification(
        project_id=project_id,
        user_id=user_id
    )


@router.get("/{project_id}/report/versions/{version_number}/verification", response_model=Optional[ReportVerificationReport])
def get_version_project_report_verification(
    project_id: str,
    version_number: int,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service)
):
    """Retrieves the verification report strictly isolated to a specific report version number."""
    _verify_project_ownership(project_id, user)
    user_id = user.get("id") if user else None
    res = verification_service.get_version_verification(
        project_id=project_id,
        version_number=version_number,
        user_id=user_id
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification records for report version {version_number} not found."
        )
    return res


@router.get("/{project_id}/report/verification/jobs/{job_id}")
def get_report_verification_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service)
):
    """Retrieves the status and step progress for a citation verification job."""
    _verify_project_ownership(project_id, user)
    user_id = user.get("id") if user else None
    return verification_service.get_verification_job(
        project_id=project_id,
        job_id=job_id,
        user_id=user_id
    )


# ==============================================================================
# STAGE 9: DETERMINISTIC DOCX GENERATION ENGINE ENDPOINTS
# ==============================================================================

class CompileDocxRequestDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version_number: Optional[int] = None
    force: bool = False


@router.post("/{project_id}/report/compile-docx")
def compile_project_docx_report(
    project_id: str,
    dto: Optional[CompileDocxRequestDTO] = None,
    version_number: Optional[int] = Query(None, description="Specific report version to compile"),
    force: bool = Query(False, description="Force compilation even if review is required"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Executes deterministic DOCX compilation grounded in the locked template,
    approved report plan, generated content, and Stage 8 verification quality gates.
    """
    from apps.api.services.document_generation import document_generation_service
    ver_num = version_number if version_number is not None else (dto.version_number if dto else None)
    force_flag = force or (dto.force if dto else False)

    return document_generation_service.compile_project_docx(
        project_id=project_id,
        version_number=ver_num,
        force=force_flag,
        user=user
    )


@router.get("/{project_id}/report/download-docx")
def download_project_docx_report(
    project_id: str,
    version_number: Optional[int] = Query(None, description="Specific report version to download"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Securely downloads the compiled DOCX document with multi-tenant IDOR protection.
    """
    from apps.api.services.document_generation import document_generation_service
    file_bytes, filename = document_generation_service.download_project_docx(
        project_id=project_id,
        version_number=version_number,
        user=user
    )

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{project_id}/report/document/jobs/{job_id}")
def get_document_generation_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves the status and step progress for a document compilation job."""
    from apps.api.services.document_generation import document_generation_service
    return document_generation_service.get_job(
        project_id=project_id,
        job_id=job_id,
        user=user
    )


# ==============================================================================
# STAGE 10: PDF GENERATION & VALIDATION ENGINE ENDPOINTS
# ==============================================================================

class CompilePdfRequestDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version_number: Optional[int] = None


@router.post("/{project_id}/report/compile-pdf")
def compile_project_pdf_report(
    project_id: str,
    dto: Optional[CompilePdfRequestDTO] = None,
    version_number: Optional[int] = Query(None, description="Specific report version to convert to PDF"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    raise HTTPException(
        status_code=400,
        detail="PDF output generation has been removed from ARM. Please download the report in DOCX format."
    )


@router.get("/{project_id}/report/download-pdf")
def download_project_pdf_report(
    project_id: str,
    version_number: Optional[int] = Query(None, description="Specific report version to download"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    raise HTTPException(
        status_code=400,
        detail="PDF output generation has been removed from ARM. Please download the report in DOCX format."
    )


@router.get("/{project_id}/report/pdf/jobs/{job_id}")
def get_pdf_generation_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves the status and step progress for a PDF conversion job."""
    from apps.api.services.pdf_generation import pdf_generation_service
    return pdf_generation_service.get_job(
        project_id=project_id,
        job_id=job_id,
        user=user
    )


# ------------------------------------------------------------------------------
# Stage 11 - Report Validation & Quality Engine Endpoints
# ------------------------------------------------------------------------------

class ValidateReportRequest(BaseModel):
    version_number: Optional[int] = None
    force_revalidate: Optional[bool] = False


@router.post("/{project_id}/report/validate")
async def validate_project_report(
    project_id: str,
    payload: Optional[ValidateReportRequest] = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Executes the automated 12-layer quality engine validation for a project's report.
    Evaluates template compliance, report plan compliance, content grounding,
    citations/evidence, numerical/tech consistency, placeholders, DOCX/PDF integrity,
    secret leakage, and final quality gate status.
    """
    from apps.api.services.quality_engine import quality_service
    version_num = payload.version_number if payload else None
    force_reval = payload.force_revalidate if payload else False

    result = quality_service.validate_project_report(
        project_id=project_id,
        user=user,
        version_number=version_num,
        force_revalidate=force_reval
    )
    return result.model_dump()


@router.get("/{project_id}/report/validation")
async def get_project_report_validation(
    project_id: str,
    version_number: Optional[int] = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieves the authoritative validation result for a project's report version.
    """
    from apps.api.services.quality_engine import quality_service
    if version_number:
        result = quality_service.get_version_validation(project_id, version_number, user=user)
    else:
        result = quality_service.get_latest_validation(project_id, user=user)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation result not found for this report version."
        )
    return result.model_dump()


@router.get("/{project_id}/report/validation/jobs/{job_id}")
async def get_validation_job_status(
    project_id: str,
    job_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves real-time status and progression for a report validation job."""
    from apps.api.services.quality_engine import quality_service
    return quality_service.get_validation_job(
        project_id=project_id,
        job_id=job_id,
        user=user
    )


# ==============================================================================
# PROJECT REPORTS, GENERATED CONTENT & ASSETS (Persistent Data Layer)
# ==============================================================================

@router.post("/{project_id}/reports", response_model=ReportResponseDTO)
def create_project_report_record(
    project_id: str,
    dto: ReportCreateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Creates a report record for a project with an assigned template."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = {
        "id": report_id,
        "project_id": project_id,
        "template_id": dto.template_id,
        "title": dto.title,
        "report_type": dto.report_type or "capstone",
        "current_version": 1,
        "status": dto.status or "planning",
        "user_id": user["id"] if user else "usr_demo_student",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if client:
        try:
            res = client.table("reports").insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error persisting report record: {e}")

    return row


@router.get("/{project_id}/reports", response_model=List[ReportResponseDTO])
def list_project_reports(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Lists all report records associated with a project."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    if client:
        try:
            res = client.table("reports").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.error(f"Error fetching reports: {e}")
    return []


@router.post("/{project_id}/reports/{report_id}/generated-content", response_model=GeneratedContentResponseDTO)
def record_generated_content(
    project_id: str,
    report_id: str,
    dto: GeneratedContentCreateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Persists a generated section or field matter against the report."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    content_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = {
        "id": content_id,
        "report_id": report_id,
        "project_id": project_id,
        "user_id": user["id"] if user else None,
        "section_key": dto.section_key,
        "field_key": dto.field_key,
        "content_type": dto.content_type,
        "raw_content": dto.raw_content,
        "formatted_content": dto.formatted_content,
        "word_count": dto.word_count or len(dto.raw_content.split()),
        "character_count": dto.character_count or len(dto.raw_content),
        "token_count": dto.token_count or 0,
        "confidence_score": dto.confidence_score or 1.0,
        "status": dto.status or "draft",
        "version_number": dto.version_number or 1,
        "metadata": dto.metadata or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if client:
        try:
            res = client.table("generated_contents").insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error persisting generated content: {e}")

    return row


@router.get("/{project_id}/reports/{report_id}/generated-content", response_model=List[GeneratedContentResponseDTO])
def list_generated_content_for_report(
    project_id: str,
    report_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves all generated content sections for a report."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    if client:
        try:
            res = client.table("generated_contents").select("*").eq("report_id", report_id).order("created_at", desc=False).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.error(f"Error fetching generated contents: {e}")
    return []


@router.post("/{project_id}/reports/{report_id}/assets", response_model=ReportAssetResponseDTO)
def record_report_asset(
    project_id: str,
    report_id: str,
    dto: ReportAssetCreateDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Registers an image, diagram, chart, or visual asset against a report."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    asset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = {
        "id": asset_id,
        "report_id": report_id,
        "project_id": project_id,
        "user_id": user["id"] if user else None,
        "asset_type": dto.asset_type,
        "title": dto.title,
        "caption": dto.caption,
        "file_name": dto.file_name,
        "storage_path": dto.storage_path,
        "mime_type": dto.mime_type or "image/png",
        "file_size_bytes": dto.file_size_bytes or 0,
        "source_evidence_id": dto.source_evidence_id,
        "section_key": dto.section_key,
        "field_key": dto.field_key,
        "metadata": dto.metadata or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if client:
        try:
            res = client.table("report_assets").insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error persisting report asset: {e}")

    return row


@router.get("/{project_id}/reports/{report_id}/assets", response_model=List[ReportAssetResponseDTO])
def list_report_assets(
    project_id: str,
    report_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Lists all assets registered for a given report."""
    _verify_project_ownership(project_id, user)
    client = db_manager.client
    if client:
        try:
            res = client.table("report_assets").select("*").eq("report_id", report_id).order("created_at", desc=False).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.error(f"Error fetching report assets: {e}")
    return []

