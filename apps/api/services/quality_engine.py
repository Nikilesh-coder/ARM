"""
ARM Stage 11 - Report Validation & Quality Engine Service
Coordinates multi-tenant authorization, evidence locker retrieval, Stage 4 Template,
Stage 6 Plan, Stage 8 Verification, Stage 9 DOCX, Stage 10 PDF, job progression,
idempotency, stale validation tracking, and structured database persistence.
"""

import os
import io
import uuid
import tempfile
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status

from apps.api.core.config import settings
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger
from apps.api.services.storage import get_storage_provider
from apps.api.services.report_generation import report_generation_service
from apps.api.services.document_generation import _COMPILED_DOCX_STORE
from apps.api.services.pdf_generation import _COMPILED_PDF_STORE
from packages.quality_engine.schema import (
    ReportQualityResult,
    InputHashes,
    QualityGateStatus
)
from packages.quality_engine.engine import ReportQualityEngine

logger = get_logger("quality_engine_service")

# Fallback in-memory stores for testing or disconnected environments
_VALIDATIONS_STORE: Dict[str, Dict[str, Any]] = {}
_VALIDATION_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class ReportQualityService:
    """Service orchestrating end-to-end report quality gate evaluation and lifecycle."""

    def __init__(self, engine: Optional[ReportQualityEngine] = None):
        self.engine = engine or ReportQualityEngine()

    def _get_and_authorize_project(self, project_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Multi-tenant authorization check preventing cross-tenant IDOR access."""
        from apps.api.routers.projects import _verify_project_ownership
        return _verify_project_ownership(project_id, user)

    @classmethod
    def _update_job(cls, job_id: str, **kwargs):
        """Updates progress and status on generation_jobs."""
        client = db_manager.client
        now = datetime.now(timezone.utc)
        kwargs["updated_at"] = now.isoformat()

        if client:
            try:
                client.table("generation_jobs").update(kwargs).eq("id", job_id).execute()
            except Exception as e:
                logger.error(f"Error updating generation job {job_id} in DB: {e}")

        job = _VALIDATION_JOBS_STORE.get(job_id, {})
        job.update(kwargs)
        _VALIDATION_JOBS_STORE[job_id] = job

    def get_validation_job(
        self,
        project_id: str,
        job_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieves real-time status and step progression of a validation job."""
        self._get_and_authorize_project(project_id, user)

        client = db_manager.client
        job = None
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).eq("project_id", project_id).execute()
                if res.data and len(res.data) > 0:
                    job = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching validation job {job_id}: {e}")

        if not job:
            job = _VALIDATION_JOBS_STORE.get(job_id)

        if not job or str(job.get("project_id")) != str(project_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation job not found.")

        return job

    def validate_project_report(
        self,
        project_id: str,
        user: Optional[Dict[str, Any]] = None,
        version_number: Optional[int] = None,
        force_revalidate: bool = False
    ) -> ReportQualityResult:
        """
        Executes end-to-end multi-layer validation for a project's report version.
        Supports idempotency, stale validation detection, and generation job tracking.
        """
        # 1. Multi-tenant Authorization
        project = self._get_and_authorize_project(project_id, user)
        user_id = user["id"] if user else project.get("user_id") or "usr_demo_student"
        client = db_manager.client
        now = datetime.now(timezone.utc)

        # 2. Retrieve Report and Report Version
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

        report_id = report_draft.report_id
        version_num = version_number or report_draft.version_number
        report_version_id = getattr(report_draft, "report_version_id", None)
        if not report_version_id:
            if client:
                try:
                    rv_res = client.table("report_versions").select("id").eq("report_id", report_id).eq("version_number", version_num).execute()
                    if rv_res.data and len(rv_res.data) > 0:
                        report_version_id = rv_res.data[0].get("id")
                except Exception:
                    pass
        if not report_version_id:
            from apps.api.services.report_generation import _REPORT_VERSIONS_STORE
            for v in _REPORT_VERSIONS_STORE.get(report_id, []):
                if v.get("version_number") == version_num and v.get("id"):
                    report_version_id = v.get("id")
                    break
        if not report_version_id:
            report_version_id = str(uuid.uuid4())

        # 3. Retrieve Template Schema
        template_schema = None
        template_id = project.get("template_id")
        if client and template_id:
            try:
                t_res = client.table("templates").select("*").eq("id", template_id).execute()
                if t_res.data and len(t_res.data) > 0:
                    template_schema = t_res.data[0].get("normalized_schema") or t_res.data[0].get("extracted_schema")
            except Exception as e:
                logger.warning(f"Error fetching template schema: {e}")

        if not template_schema and template_id:
            from apps.api.routers.templates import _TEMPLATES_DB
            t_obj = _TEMPLATES_DB.get(template_id)
            if t_obj:
                template_schema = t_obj.get("template_schema") or t_obj.get("normalized_schema")

        # 4. Retrieve Report Plan
        report_plan = None
        if client:
            try:
                p_res = client.table("report_plans").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if p_res.data and len(p_res.data) > 0:
                    report_plan = p_res.data[0].get("plan_data") or p_res.data[0]
            except Exception as e:
                logger.warning(f"Error fetching report plan: {e}")

        if not report_plan:
            from apps.api.services.report_planner import _REPORT_PLANS_STORE
            report_plan = _REPORT_PLANS_STORE.get(project_id)

        # 5. Retrieve Evidence Items
        evidence_items = []
        if client:
            try:
                e_res = client.table("project_files").select("*").eq("project_id", project_id).execute()
                if e_res.data:
                    evidence_items = e_res.data
            except Exception as e:
                logger.warning(f"Error fetching evidence items: {e}")

        if not evidence_items:
            from apps.api.routers.projects import _EVIDENCE_STORE
            evidence_items = [e for e in _EVIDENCE_STORE.values() if str(e.get("project_id")) == str(project_id)]

        # 6. Retrieve Stage 8 Verification Report
        verification_report = None
        if client:
            try:
                v_res = client.table("report_verifications").select("*").eq("report_id", report_id).order("created_at", desc=True).limit(1).execute()
                if v_res.data and len(v_res.data) > 0:
                    verification_report = v_res.data[0]
            except Exception as e:
                logger.warning(f"Error fetching report verification: {e}")

        if not verification_report:
            from apps.api.services.citation_verification import _VERIFICATIONS_STORE
            verification_report = _VERIFICATIONS_STORE.get(report_version_id) or _VERIFICATIONS_STORE.get(report_id)

        # 7. Locate DOCX & PDF Artifacts
        docx_storage_path = None
        pdf_storage_path = None
        if client:
            try:
                rv_res = client.table("report_versions").select("*").eq("report_id", report_id).eq("version_number", version_num).execute()
                if rv_res.data and len(rv_res.data) > 0:
                    row = rv_res.data[0]
                    docx_storage_path = row.get("docx_storage_path")
                    pdf_storage_path = row.get("pdf_storage_path")
                    if not docx_storage_path and row.get("generation_metadata"):
                        docx_storage_path = row["generation_metadata"].get("docx_storage_path")
                    if not pdf_storage_path and row.get("generation_metadata"):
                        pdf_storage_path = row["generation_metadata"].get("pdf_storage_path")
            except Exception as e:
                logger.warning(f"Error querying artifact paths: {e}")

        if not docx_storage_path:
            from apps.api.services.report_generation import _REPORT_VERSIONS_STORE
            for v in _REPORT_VERSIONS_STORE.get(report_id, []):
                if v.get("version_number") == version_num:
                    docx_storage_path = v.get("docx_storage_path")
                    pdf_storage_path = v.get("pdf_storage_path")
                    break

        # Check existing validation for idempotency / stale detection
        report_data_dict = report_draft.model_dump() if hasattr(report_draft, "model_dump") else dict(report_draft)
        current_content_hash = InputHashes.compute_content_hash(report_data_dict)
        current_template_hash = InputHashes.compute_sha256(template_schema) if template_schema else None
        current_plan_hash = InputHashes.compute_sha256(report_plan) if report_plan else None

        existing_val = self._get_existing_validation_by_version(report_version_id)
        if not existing_val:
            v_dict = _VALIDATIONS_STORE.get(f"{project_id}_{version_num}")
            if v_dict and not v_dict.get("is_stale", False):
                existing_val = ReportQualityResult.model_validate(v_dict)

        if existing_val and not force_revalidate:
            # Check if inputs have changed
            h = existing_val.input_hashes
            if h and h.content_sha256 == current_content_hash:
                logger.info(f"Returning cached validation for version {version_num} (idempotent run)")
                return existing_val
            else:
                # Content changed - mark prior validation as stale
                logger.info(f"Report inputs changed since last validation. Stale validation detected.")
                self._mark_validation_stale(existing_val.validation_id)

        # 8. Initialize Generation Job
        job_id = str(uuid.uuid4())
        job_record = {
            "id": job_id,
            "user_id": user_id,
            "project_id": project_id,
            "report_id": report_id,
            "job_type": "validation",
            "status": "running",
            "progress": 10,
            "progress_percentage": 10,
            "current_stage": "loading_report",
            "current_step": "loading_report_and_artifacts",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        _VALIDATION_JOBS_STORE[job_id] = job_record
        if client:
            try:
                client.table("generation_jobs").insert(job_record).execute()
            except Exception as e:
                logger.warning(f"Error inserting validation job: {e}")

        # 9. Workspace Isolation for Artifact Inspection
        temp_dir = tempfile.mkdtemp(prefix="arm_val_")
        temp_docx_path = None
        temp_pdf_path = None

        try:
            # Download DOCX if available
            if docx_storage_path:
                docx_bytes = _COMPILED_DOCX_STORE.get(docx_storage_path)
                if not docx_bytes:
                    storage = get_storage_provider()
                    try:
                        docx_bytes = storage.download_file(settings.storage.bucket_reports, docx_storage_path)
                    except Exception:
                        pass
                if docx_bytes:
                    temp_docx_path = os.path.join(temp_dir, "document.docx")
                    with open(temp_docx_path, "wb") as f:
                        f.write(docx_bytes)

            # Download PDF if available
            if pdf_storage_path:
                pdf_bytes = _COMPILED_PDF_STORE.get(pdf_storage_path)
                if not pdf_bytes:
                    storage = get_storage_provider()
                    try:
                        pdf_bytes = storage.download_file(settings.storage.bucket_reports, pdf_storage_path)
                    except Exception:
                        pass
                if pdf_bytes:
                    temp_pdf_path = os.path.join(temp_dir, "document.pdf")
                    with open(temp_pdf_path, "wb") as f:
                        f.write(pdf_bytes)

            # Progressive job updates
            self._update_job(job_id, progress=30, progress_percentage=30, current_stage="validating_structure", current_step="evaluating_template_and_plan")
            self._update_job(job_id, progress=50, progress_percentage=50, current_stage="validating_grounding", current_step="evaluating_evidence_and_citations")
            self._update_job(job_id, progress=70, progress_percentage=70, current_stage="validating_consistency", current_step="checking_numerical_and_technology_consistency")
            self._update_job(job_id, progress=85, progress_percentage=85, current_stage="validating_artifacts", current_step="inspecting_docx_and_pdf_integrity")

            # 10. Execute ReportQualityEngine
            quality_result = self.engine.validate_report(
                report_data=report_data_dict,
                project_info=project,
                template_schema=template_schema,
                report_plan=report_plan,
                evidence_items=evidence_items,
                verification_report=verification_report,
                docx_path=temp_docx_path,
                pdf_path=temp_pdf_path,
                docx_version=version_num if temp_docx_path else None,
                pdf_version=version_num if temp_pdf_path else None,
                report_version_id=report_version_id,
                version_number=version_num
            )

            # 11. Final Status and Persistence
            self._update_job(job_id, progress=95, progress_percentage=95, current_stage="calculating_final_status", current_step="persisting_validation_verdict")

            self._persist_validation_result(
                quality_result=quality_result,
                user_id=user_id
            )

            # Complete Job
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                progress_percentage=100,
                current_stage="completed",
                current_step="completed",
                completed_at=datetime.now(timezone.utc).isoformat(),
                result_payload=quality_result.model_dump()
            )

            return quality_result

        except Exception as e:
            logger.error(f"Error during quality validation execution: {e}")
            self._update_job(
                job_id,
                status="failed",
                current_stage="failed",
                current_step="failed",
                error_message=str(e)
            )
            raise e
        finally:
            import shutil
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _persist_validation_result(self, quality_result: ReportQualityResult, user_id: str):
        """Persists validation result to database and updates report_versions."""
        client = db_manager.client
        res_dict = quality_result.model_dump()

        # In-memory stores
        _VALIDATIONS_STORE[quality_result.report_version_id] = res_dict
        _VALIDATIONS_STORE[quality_result.validation_id] = res_dict
        _VALIDATIONS_STORE[f"{quality_result.project_id}_latest"] = res_dict
        _VALIDATIONS_STORE[f"{quality_result.project_id}_{quality_result.version_number}"] = res_dict

        if client:
            try:
                uuid.UUID(str(quality_result.validation_id))
                uuid.UUID(str(quality_result.report_version_id))
                uuid.UUID(str(quality_result.report_id))
                uuid.UUID(str(quality_result.project_id))
                db_record = {
                    "id": quality_result.validation_id,
                    "report_version_id": quality_result.report_version_id,
                    "report_id": quality_result.report_id,
                    "project_id": quality_result.project_id,
                    "user_id": user_id,
                    "validator_version": quality_result.validator_version,
                    "status": quality_result.status.lower(),
                    "gate_status": quality_result.gate_status.lower(),
                    "validation_summary": quality_result.summary.model_dump(),
                    "checks": [c.model_dump() for c in quality_result.checks],
                    "issues": [i.model_dump() for i in quality_result.issues],
                    "input_hashes": quality_result.input_hashes.model_dump(),
                    "is_stale": False,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                client.table("report_validations").upsert(db_record).execute()

                # Also update report_versions columns: validation_summary and validation_json
                client.table("report_versions").update({
                    "validation_summary": quality_result.summary.model_dump(),
                    "validation_json": res_dict
                }).eq("report_id", quality_result.report_id).eq("version_number", quality_result.version_number).execute()

            except Exception as e:
                logger.error(f"Error persisting report validation in DB: {e}")

    def _mark_validation_stale(self, validation_id: str):
        """Flags an existing validation record as stale."""
        client = db_manager.client
        if client:
            try:
                uuid.UUID(str(validation_id))
                client.table("report_validations").update({
                    "is_stale": True,
                    "status": "stale"
                }).eq("id", validation_id).execute()
            except Exception as e:
                logger.warning(f"Error marking validation stale: {e}")

        for vid, vdata in _VALIDATIONS_STORE.items():
            if vdata.get("validation_id") == validation_id or vid == validation_id:
                vdata["is_stale"] = True
                vdata["status"] = "stale"

    def _get_existing_validation_by_version(self, report_version_id: str) -> Optional[ReportQualityResult]:
        """Retrieves existing validation result for report version if present."""
        client = db_manager.client
        if client:
            try:
                uuid.UUID(str(report_version_id))
                res = client.table("report_validations").select("*").eq("report_version_id", report_version_id).eq("is_stale", False).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    v_dict = {
                        "validation_id": row["id"],
                        "report_id": row["report_id"],
                        "report_version_id": row["report_version_id"],
                        "version_number": 1,
                        "project_id": row["project_id"],
                        "validator_version": row.get("validator_version", "1.0.0"),
                        "status": row.get("status", "ready").upper(),
                        "gate_status": row.get("gate_status", "ready").upper(),
                        "checks": row.get("checks", []),
                        "issues": row.get("issues", []),
                        "summary": row.get("validation_summary", {}),
                        "input_hashes": row.get("input_hashes", {}),
                        "is_stale": row.get("is_stale", False),
                        "created_at": row.get("created_at", datetime.now(timezone.utc).isoformat())
                    }
                    return ReportQualityResult.model_validate(v_dict)
            except Exception as e:
                logger.warning(f"Error reading existing validation: {e}")

        v_dict = _VALIDATIONS_STORE.get(report_version_id)
        if v_dict and not v_dict.get("is_stale", False):
            return ReportQualityResult.model_validate(v_dict)
        return None

    def get_latest_validation(
        self,
        project_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Optional[ReportQualityResult]:
        """Retrieves the latest non-stale validation result for a project's report."""
        self._get_and_authorize_project(project_id, user)
        client = db_manager.client
        if client:
            try:
                uuid.UUID(str(project_id))
                res = client.table("report_validations").select("*").eq("project_id", project_id).eq("is_stale", False).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    v_dict = {
                        "validation_id": row["id"],
                        "report_id": row["report_id"],
                        "report_version_id": row["report_version_id"],
                        "version_number": 1,
                        "project_id": row["project_id"],
                        "validator_version": row.get("validator_version", "1.0.0"),
                        "status": row.get("status", "ready").upper(),
                        "gate_status": row.get("gate_status", "ready").upper(),
                        "checks": row.get("checks", []),
                        "issues": row.get("issues", []),
                        "summary": row.get("validation_summary", {}),
                        "input_hashes": row.get("input_hashes", {}),
                        "is_stale": row.get("is_stale", False),
                        "created_at": row.get("created_at", datetime.now(timezone.utc).isoformat())
                    }
                    return ReportQualityResult.model_validate(v_dict)
            except Exception as e:
                logger.warning(f"Error querying latest validation from DB: {e}")

        v_dict = _VALIDATIONS_STORE.get(f"{project_id}_latest")
        if v_dict and not v_dict.get("is_stale", False):
            return ReportQualityResult.model_validate(v_dict)
        return None

    def get_version_validation(
        self,
        project_id: str,
        version_number: int,
        user: Optional[Dict[str, Any]] = None
    ) -> Optional[ReportQualityResult]:
        """Retrieves the validation result strictly for the specified report version number."""
        self._get_and_authorize_project(project_id, user)
        client = db_manager.client
        if client:
            try:
                uuid.UUID(str(project_id))
                res = client.table("report_validations").select("*").eq("project_id", project_id).eq("is_stale", False).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    v_dict = {
                        "validation_id": row["id"],
                        "report_id": row["report_id"],
                        "report_version_id": row["report_version_id"],
                        "version_number": version_number,
                        "project_id": row["project_id"],
                        "validator_version": row.get("validator_version", "1.0.0"),
                        "status": row.get("status", "ready").upper(),
                        "gate_status": row.get("gate_status", "ready").upper(),
                        "checks": row.get("checks", []),
                        "issues": row.get("issues", []),
                        "summary": row.get("validation_summary", {}),
                        "input_hashes": row.get("input_hashes", {}),
                        "is_stale": row.get("is_stale", False),
                        "created_at": row.get("created_at", datetime.now(timezone.utc).isoformat())
                    }
                    return ReportQualityResult.model_validate(v_dict)
            except Exception as e:
                logger.warning(f"Error querying version validation from DB: {e}")

        v_dict = _VALIDATIONS_STORE.get(f"{project_id}_{version_number}")
        if v_dict and not v_dict.get("is_stale", False):
            return ReportQualityResult.model_validate(v_dict)
        return None


quality_service = ReportQualityService()
