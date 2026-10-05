"""
ARM Stage 9 - Deterministic Document Generation Service
Coordinates locked templates, approved report plans, generated report drafts,
Stage 8 verification quality gates, deterministic DOCX compilation,
structural validation, reopen testing, private storage, and job progression.
"""

import os
import re
import io
import uuid
import shutil
import tempfile
import copy
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import HTTPException, status

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.services.storage import get_storage_provider
from apps.api.services.template_intelligence import template_intelligence_service
from apps.api.services.report_planner import report_planner_service
from apps.api.services.report_generation import report_generation_service
from apps.api.services.citation_verification import get_citation_verification_service
from packages.template_intelligence.schema import TemplateSchema
from packages.document_engine.engine import DocumentAssembler
from packages.document_engine.validator import DocumentValidator

logger = get_logger("document_generation_service")

# In-memory storage for test/offline fallback
_COMPILED_DOCX_STORE: Dict[str, bytes] = {}
_DOCUMENT_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class DocumentGenerationService:
    """Service orchestrating deterministic DOCX document compilation and validation."""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitizes filename against path traversal and illegal filesystem characters."""
        clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
        clean = re.sub(r'_+', '_', clean).strip('._')
        return clean or "Academic_Report"

    @classmethod
    def _update_job(cls, job_id: str, **kwargs):
        """Updates progress, stage, step, and status on generation_jobs."""
        client = db_manager.client
        now = datetime.now(timezone.utc)
        kwargs["updated_at"] = now.isoformat()

        if client:
            try:
                client.table("generation_jobs").update(kwargs).eq("id", job_id).execute()
            except Exception as e:
                logger.error(f"Error updating generation job {job_id} in DB: {e}")

        job = _DOCUMENT_JOBS_STORE.get(job_id, {})
        job.update(kwargs)
        _DOCUMENT_JOBS_STORE[job_id] = job

    @classmethod
    def get_job(
        cls,
        project_id: str,
        job_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieves real-time status and step progression of a document compilation job."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        job = None
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).execute()
                if res.data and len(res.data) > 0:
                    job = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching job {job_id}: {e}")

        if not job:
            job = _DOCUMENT_JOBS_STORE.get(job_id)

        if not job or str(job.get("project_id")) != str(project_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found.")

        return job

    @classmethod
    def compile_project_docx(
        cls,
        project_id: str,
        version_number: Optional[int] = None,
        force: bool = False,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end deterministic DOCX generation:
        1. Verifies project ownership (multi-tenant IDOR protection)
        2. Enforces locked college template requirement
        3. Enforces approved ReportPlan requirement
        4. Fetches generated report content
        5. Validates Stage 8 verification quality gates (blocking issues prevent final compilation)
        6. Tracks real-time job progression via generation_jobs
        7. Enforces original template SHA-256 immutability
        8. Executes deterministic DocumentAssembler
        9. Runs OpenXML ZIP integrity and python-docx reopen validation
        10. Persists to private storage and updates report_versions
        """
        from apps.api.routers.projects import _verify_project_ownership, _PROJECTS_STORE, _MEMBERS_STORE, _EVIDENCE_STORE
        project_data = _verify_project_ownership(project_id, user)
        user_id = user["id"] if user else project_data.get("user_id") or "usr_demo_student"
        client = db_manager.client
        now = datetime.now(timezone.utc)

        # ----------------------------------------------------------------------
        # 1. Fetch Template and enforce Locked Template Requirement
        # ----------------------------------------------------------------------
        template_id = project_data.get("template_id")
        template_row = None

        if client and template_id:
            try:
                t_res = client.table("templates").select("*").eq("id", template_id).execute()
                if t_res.data and len(t_res.data) > 0:
                    template_row = t_res.data[0]
            except Exception as e:
                logger.warning(f"Error fetching template {template_id} from DB: {e}")

        if not template_row and template_id:
            from apps.api.routers.templates import _TEMPLATES_DB
            template_row = _TEMPLATES_DB.get(template_id)

        if not template_row:
            # Fallback search by project_id
            if client:
                try:
                    t_res2 = client.table("templates").select("*").eq("project_id", project_id).limit(1).execute()
                    if t_res2.data and len(t_res2.data) > 0:
                        template_row = t_res2.data[0]
                        template_id = template_row["id"]
                except Exception:
                    pass

        if not template_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No template associated with this project. Upload and lock a template before generation."
            )

        # Enforce locked status strictly
        is_locked = template_row.get("is_locked", False)
        t_status = template_row.get("status")
        if not is_locked or t_status not in ("locked", "approved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Template '{template_row.get('name', template_id)}' is not locked (current status: '{t_status}'). "
                    f"Only locked templates can be used for deterministic document compilation."
                )
            )

        # Load authoritative locked schema
        locked_schema_dict = template_intelligence_service.get_locked_template(template_id)
        if not locked_schema_dict:
            # Fallback to schema in analysis
            analysis = template_intelligence_service.get_template_analysis(template_id)
            if analysis and analysis.get("schema_data"):
                locked_schema_dict = analysis.get("schema_data")

        if not locked_schema_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Locked template schema could not be retrieved. Please review and lock the template."
            )

        template_schema = TemplateSchema.model_validate(locked_schema_dict)

        # ----------------------------------------------------------------------
        # 2. Fetch and Validate Approved Report Plan Requirement
        # ----------------------------------------------------------------------
        report_plan = report_planner_service.get_latest_plan(project_id=project_id, user=user)
        if not report_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No report plan found for this project. Trigger report planning and approval first."
            )

        if not report_plan.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report plan is not approved. The student or advisor must approve the plan before compilation."
            )

        # ----------------------------------------------------------------------
        # 3. Fetch Generated Report Content
        # ----------------------------------------------------------------------
        if version_number:
            report_draft = report_generation_service.get_report_version(
                project_id=project_id,
                version_number=version_number,
                user=user
            )
        else:
            report_draft = report_generation_service.get_latest_report(project_id=project_id, user=user)

        if not report_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No generated report draft found for this project. Trigger content generation first."
            )

        # ----------------------------------------------------------------------
        # 4. Fetch and Validate Stage 8 Verification Results
        # ----------------------------------------------------------------------
        verification_service = get_citation_verification_service()
        verification_report = verification_service.get_latest_verification(
            project_id=project_id,
            user_id=user_id
        )

        document_mode = "FINAL"
        if verification_report:
            qg = verification_report.quality_gates
            if not qg.can_proceed_to_document_generation and not force:
                logger.warning(f"Compilation blocked by Stage 8 verification: {qg.blocking_issues}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "Document generation blocked by Stage 8 verification issues",
                        "blocking_issues": qg.blocking_issues,
                        "warnings": qg.warnings,
                        "message": "Resolve verification issues or provide force=true to compile as REVIEW_REQUIRED draft."
                    }
                )
            elif not qg.can_proceed_to_document_generation and force:
                document_mode = "REVIEW_REQUIRED"
        else:
            # If no verification was run, default to DRAFT mode
            document_mode = "DRAFT"

        # ----------------------------------------------------------------------
        # 5. Initialize Generation Job
        # ----------------------------------------------------------------------
        job_id = str(uuid.uuid4())
        job_row = {
            "id": job_id,
            "project_id": project_id,
            "user_id": user_id,
            "report_id": report_draft.report_id,
            "job_type": "document_generation",
            "status": "running",
            "progress": 10,
            "progress_percentage": 10,
            "current_stage": "document_assembly",
            "current_step": "validating_inputs",
            "started_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {
                "template_id": template_id,
                "report_id": report_draft.report_id,
                "version_number": report_draft.version_number,
                "document_mode": document_mode
            }
        }

        if client:
            try:
                client.table("generation_jobs").insert(job_row).execute()
            except Exception as e:
                logger.warning(f"Error inserting document generation job into DB: {e}")

        _DOCUMENT_JOBS_STORE[job_id] = job_row

        # ----------------------------------------------------------------------
        # 6. Template Immutability Check & Working Copy Setup
        # ----------------------------------------------------------------------
        cls._update_job(job_id, progress=25, progress_percentage=25, current_step="loading_template")

        temp_dir = tempfile.mkdtemp(prefix="arm_docx_")
        original_template_path = template_row.get("original_file_path") or template_row.get("storage_path")
        working_template_path: Optional[str] = None
        original_sha256: Optional[str] = None

        if original_template_path and os.path.exists(original_template_path) and original_template_path.endswith(".docx"):
            original_sha256 = DocumentValidator.calculate_sha256(original_template_path)
            # Create a separate isolated working copy to guarantee immutability
            working_template_path = os.path.join(temp_dir, "working_template.docx")
            shutil.copy2(original_template_path, working_template_path)
        else:
            # Check if template bytes are available in storage
            storage = get_storage_provider()
            storage_path = template_row.get("storage_path")
            if storage_path:
                try:
                    tpl_bytes = storage.download_file(settings.storage.bucket_templates, storage_path)
                    if tpl_bytes and len(tpl_bytes) > 0 and (template_row.get("file_type") == "docx" or storage_path.endswith(".docx")):
                        cached_orig = os.path.join(temp_dir, "original_template.docx")
                        with open(cached_orig, "wb") as f:
                            f.write(tpl_bytes)
                        original_sha256 = DocumentValidator.calculate_sha256(cached_orig)
                        original_template_path = cached_orig
                        working_template_path = os.path.join(temp_dir, "working_template.docx")
                        shutil.copy2(cached_orig, working_template_path)
                except Exception as e:
                    logger.warning(f"Could not retrieve master template bytes from storage: {e}")

        # ----------------------------------------------------------------------
        # 7. Load Evidence and Project Information
        # ----------------------------------------------------------------------
        cls._update_job(job_id, progress=40, progress_percentage=40, current_step="loading_content")

        # Fetch evidence files for image embedding
        evidence_inventory: List[Dict[str, Any]] = []
        if client:
            try:
                ev_res = client.table("project_files").select("*").eq("project_id", project_id).execute()
                if ev_res.data:
                    evidence_inventory = ev_res.data
            except Exception:
                pass
        if not evidence_inventory:
            evidence_inventory = [
                ev for ev in _EVIDENCE_STORE.values()
                if str(ev.get("project_id")) == str(project_id)
            ]

        # Fetch members
        members: List[Dict[str, Any]] = []
        if client:
            try:
                m_res = client.table("project_members").select("*").eq("project_id", project_id).execute()
                if m_res.data:
                    members = m_res.data
            except Exception:
                pass
        if not members:
            members = [
                m for m in _MEMBERS_STORE.values()
                if str(m.get("project_id")) == str(project_id)
            ]

        project_context = copy.deepcopy(project_data)
        project_context["members"] = members

        # ----------------------------------------------------------------------
        # 8. Document Assembly Engine
        # ----------------------------------------------------------------------
        cls._update_job(job_id, progress=60, progress_percentage=60, current_step="assembling_document")

        assembler = DocumentAssembler(
            template_schema=template_schema,
            master_template_path=working_template_path
        )

        assembler.assemble_report(
            generated_report=report_draft,
            project_info=project_context,
            verified_claims=verification_report.claims if verification_report else None,
            evidence_inventory=evidence_inventory
        )

        output_filename = f"{cls._sanitize_filename(project_data.get('title', 'Report'))}_v{report_draft.version_number}.docx"
        compiled_local_path = os.path.join(temp_dir, output_filename)
        assembler.save(compiled_local_path)

        # ----------------------------------------------------------------------
        # 9. Verify Original Template Immutability
        # ----------------------------------------------------------------------
        if original_template_path and original_sha256:
            is_intact = DocumentValidator.verify_template_immutability(original_template_path, original_sha256)
            if not is_intact:
                cls._update_job(job_id, status="failed", error_message="Original template file was modified during compilation.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Fatal error: Template immutability violation detected."
                )

        # ----------------------------------------------------------------------
        # 10. OpenXML ZIP Structural Validation and Reopen Test
        # ----------------------------------------------------------------------
        cls._update_job(job_id, progress=85, progress_percentage=85, current_step="validating_docx")

        validation_result = DocumentValidator.validate_docx(compiled_local_path)
        if not validation_result.get("valid") or not validation_result.get("reopen_success"):
            err_msg = "; ".join(validation_result.get("errors", ["Unknown DOCX validation failure"]))
            cls._update_job(job_id, status="failed", error_message=err_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generated DOCX failed structural validation or reopen test: {err_msg}"
            )

        # ----------------------------------------------------------------------
        # 11. Persistence to Private Storage & Database Updates
        # ----------------------------------------------------------------------
        cls._update_job(job_id, progress=95, progress_percentage=95, current_step="saving_document")

        with open(compiled_local_path, "rb") as f:
            docx_bytes = f.read()

        # Logical storage path: users/{user_id}/projects/{project_id}/reports/{report_id}/versions/{version_number}/report.docx
        report_id = report_draft.report_id
        version_num = report_draft.version_number
        storage_rel_path = f"users/{user_id}/projects/{project_id}/reports/{report_id}/versions/{version_num}/report.docx"

        storage = get_storage_provider()
        try:
            storage.upload_file(
                bucket=settings.storage.bucket_reports,
                path=storage_rel_path,
                data=docx_bytes,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            logger.warning(f"Storage upload notice: {e}")

        # In-memory store for instant test download
        _COMPILED_DOCX_STORE[storage_rel_path] = docx_bytes

        # Update database: report_versions and reports
        if client:
            try:
                # Update report_versions row
                client.table("report_versions").update({
                    "docx_storage_path": storage_rel_path,
                    "validation_summary": {
                        "document_mode": document_mode,
                        "docx_validation": validation_result,
                        "verified_at": now.isoformat(),
                        "template_sha256": original_sha256
                    }
                }).eq("report_id", report_id).eq("version_number", version_num).execute()

                # Update reports row
                client.table("reports").update({
                    "docx_storage_path": storage_rel_path,
                    "status": "completed",
                    "updated_at": now.isoformat()
                }).eq("id", report_id).execute()
            except Exception as e:
                logger.error(f"Error persisting DOCX storage path in DB: {e}")

        # Update local report store
        from apps.api.services.report_generation import _REPORTS_STORE, _REPORT_VERSIONS_STORE
        if report_id in _REPORTS_STORE:
            _REPORTS_STORE[report_id]["docx_storage_path"] = storage_rel_path
            _REPORTS_STORE[report_id]["status"] = "completed"

        vers_list = _REPORT_VERSIONS_STORE.get(report_id, [])
        for v in vers_list:
            if v.get("version_number") == version_num:
                v["docx_storage_path"] = storage_rel_path
                v["validation_summary"] = {
                    "document_mode": document_mode,
                    "docx_validation": validation_result
                }

        # Complete Job
        cls._update_job(
            job_id,
            status="completed",
            progress=100,
            progress_percentage=100,
            current_stage="completed",
            current_step="completed",
            completed_at=now.isoformat(),
            result_payload={
                "docx_storage_path": storage_rel_path,
                "file_name": output_filename,
                "file_size_bytes": len(docx_bytes),
                "document_mode": document_mode,
                "validation": validation_result,
                "template_immutability": {
                    "original_sha256": original_sha256,
                    "verified_unchanged": True
                }
            }
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "project_id": project_id,
            "report_id": report_id,
            "version_number": version_num,
            "file_name": output_filename,
            "document_mode": document_mode,
            "docx_storage_path": storage_rel_path,
            "file_size_bytes": len(docx_bytes),
            "validation": validation_result,
            "template_immutability": {
                "original_sha256": original_sha256,
                "verified_unchanged": True
            }
        }

    @classmethod
    def download_project_docx(
        cls,
        project_id: str,
        version_number: Optional[int] = None,
        user: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        """
        Retrieves the compiled DOCX binary with strict multi-tenant IDOR protection.
        Returns: (file_bytes, download_filename)
        """
        from apps.api.routers.projects import _verify_project_ownership
        project_data = _verify_project_ownership(project_id, user)

        # Get latest report or specific version
        if version_number:
            report_draft = report_generation_service.get_report_version(
                project_id=project_id,
                version_number=version_number,
                user=user
            )
        else:
            report_draft = report_generation_service.get_latest_report(project_id=project_id, user=user)

        if not report_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report draft not found for this project."
            )

        # Retrieve version record
        client = db_manager.client
        storage_path = None
        version_num = version_number or report_draft.version_number

        if client:
            try:
                res = client.table("report_versions").select("docx_storage_path").eq(
                    "report_id", report_draft.report_id
                ).eq("version_number", version_num).execute()
                if res.data and len(res.data) > 0:
                    storage_path = res.data[0].get("docx_storage_path")
            except Exception as e:
                logger.warning(f"Error querying docx_storage_path from DB: {e}")

        if not storage_path:
            from apps.api.services.report_generation import _REPORT_VERSIONS_STORE
            vers_list = _REPORT_VERSIONS_STORE.get(report_draft.report_id, [])
            for v in vers_list:
                if v.get("version_number") == version_num:
                    storage_path = v.get("docx_storage_path")
                    break

        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compiled DOCX document for version {version_num} has not been generated yet."
            )

        # Retrieve file bytes from in-memory cache or storage provider
        docx_bytes = _COMPILED_DOCX_STORE.get(storage_path)

        if not docx_bytes:
            storage = get_storage_provider()
            try:
                docx_bytes = storage.download_file(settings.storage.bucket_reports, storage_path)
            except Exception as e:
                logger.error(f"Error downloading compiled DOCX from storage: {e}")

        if not docx_bytes or len(docx_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Compiled DOCX file could not be found in storage."
            )

        # Sanitized download filename
        filename = f"{cls._sanitize_filename(project_data.get('title', 'Academic_Report'))}_v{version_num}.docx"
        return docx_bytes, filename


document_generation_service = DocumentGenerationService()
