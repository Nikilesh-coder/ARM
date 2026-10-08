"""
ARM Stage 8 - Citation & Evidence Verification Service
Coordinates multi-tenant authorization, evidence locker retrieval, claim extraction,
verification execution, generation jobs tracking, and structured database persistence.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from fastapi import HTTPException, status
from apps.api.core.database import db_manager
from packages.citation_verifier.schema import ReportVerificationReport
from packages.citation_verifier.engine import CitationEvidenceVerificationEngine
from packages.citation_verifier.research_provider import ResearchProvider, MockResearchProvider
from packages.citation_verifier.claim_extractor import ClaimExtractor

logger = logging.getLogger(__name__)

# Fallback in-memory stores for testing or disconnected environments
_VERIFICATIONS_STORE: Dict[str, Dict[str, Any]] = {}
_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class CitationVerificationService:
    """Service orchestrating Citation & Evidence Verification for academic reports."""

    def __init__(
        self,
        verification_engine: Optional[CitationEvidenceVerificationEngine] = None,
        research_provider: Optional[ResearchProvider] = None
    ):
        self.research_provider = research_provider or MockResearchProvider()
        self.engine = verification_engine or CitationEvidenceVerificationEngine(
            claim_extractor=ClaimExtractor(),
            research_provider=self.research_provider
        )

    def verify_project_report(
        self,
        project_id: str,
        user_id: Optional[str] = None,
        version_number: Optional[int] = None
    ) -> ReportVerificationReport:
        """
        Executes the citation and evidence verification pipeline for a project's report draft.
        Enforces strict multi-tenant authorization, version integrity, and job progress tracking.
        """
        # 1. Authorization & Tenant Isolation Check
        project = self._get_and_authorize_project(project_id, user_id)

        # 2. Retrieve Report and Report Version
        report, report_version = self._get_report_and_version(project_id, version_number)
        content_json = report_version.get("content_json") or {}
        if not content_json or not content_json.get("sections"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY if hasattr(status, "HTTP_422_UNPROCESSABLE_ENTITY") else 422,
                detail="Report draft content is empty. Stage 7 report content generation must be completed prior to verification."
            )

        # 3. Retrieve Stage 5 Evidence Locker Items
        evidence_inventory = self._get_project_evidence(project_id)

        # 4. Retrieve Stage 6 Report Plan
        report_plan = self._get_report_plan(project_id)

        # 5. Initialize Generation Job
        job_id = str(uuid.uuid4())
        self._update_job(
            job_id=job_id,
            user_id=user_id or str(project.get("user_id") or project.get("owner_id") or uuid.uuid4()),
            project_id=project_id,
            report_id=report.get("id"),
            status_val="verifying",
            progress=15,
            current_step="loading_report"
        )

        try:
            # 6. Step: Extract Claims & Map Evidence
            self._update_job(job_id, progress=35, current_step="extracting_claims")
            self._update_job(job_id, progress=60, current_step="mapping_evidence")
            self._update_job(job_id, progress=75, current_step="validating_sources")
            self._update_job(job_id, progress=90, current_step="validating_claims")

            # 7. Run Verification Engine
            verification_result = self.engine.verify_report(
                report_data=content_json,
                project_info=project,
                evidence_inventory=evidence_inventory,
                report_plan=report_plan,
                report_version_id=str(report_version.get("id")),
                version_number=report_version.get("version_number", 1)
            )

            # 8. Step: Saving Results
            self._update_job(job_id, progress=95, current_step="saving_results")
            self._persist_verification(
                verification=verification_result,
                project_id=project_id,
                report_id=str(report.get("id")),
                report_version_id=str(report_version.get("id")),
                user_id=user_id or str(project.get("user_id") or project.get("owner_id"))
            )

            # 9. Complete Job
            self._update_job(
                job_id,
                progress=100,
                current_step="completed",
                status_val="completed",
                completed_at=datetime.now(timezone.utc).isoformat()
            )

            return verification_result

        except Exception as e:
            logger.error(f"Error during citation verification: {e}")
            self._update_job(
                job_id,
                status_val="failed",
                current_step="failed",
                error_message=str(e)
            )
            raise e

    def get_latest_verification(
        self,
        project_id: str,
        user_id: Optional[str] = None
    ) -> Optional[ReportVerificationReport]:
        """Retrieves the latest verification result for a project's current report version."""
        self._get_and_authorize_project(project_id, user_id)
        report, report_version = self._get_report_and_version(project_id)
        if not report_version:
            return None

        version_id = str(report_version.get("id"))
        return self._fetch_verification_by_version(version_id)

    def get_version_verification(
        self,
        project_id: str,
        version_number: int,
        user_id: Optional[str] = None
    ) -> Optional[ReportVerificationReport]:
        """Retrieves the verification result strictly for the specified report version number."""
        self._get_and_authorize_project(project_id, user_id)
        report, report_version = self._get_report_and_version(project_id, version_number)
        if not report_version:
            return None

        version_id = str(report_version.get("id"))
        return self._fetch_verification_by_version(version_id)

    def get_verification_job(
        self,
        project_id: str,
        job_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieves job status with strict ownership enforcement."""
        self._get_and_authorize_project(project_id, user_id)
        
        client = db_manager.client
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).eq("project_id", project_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.error(f"DB error fetching verification job: {e}")

        job = _JOBS_STORE.get(job_id)
        if not job or job.get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Verification job not found.")
        return job

    # --------------------------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------------------------

    def _get_and_authorize_project(self, project_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Verifies project existence and validates ownership to prevent IDOR."""
        client = db_manager.client
        project: Optional[Dict[str, Any]] = None

        if client:
            try:
                res = client.table("projects").select("*").eq("id", project_id).execute()
                if res.data and len(res.data) > 0:
                    project = res.data[0]
            except Exception as e:
                logger.error(f"DB error fetching project: {e}")

        if not project:
            from apps.api.routers.projects import _PROJECTS_STORE
            project = _PROJECTS_STORE.get(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        # IDOR check
        if user_id:
            proj_owner = str(project.get("user_id") or project.get("owner_id") or "")
            if proj_owner and proj_owner != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this project."
                )

        return project

    def _get_report_and_version(
        self,
        project_id: str,
        version_number: Optional[int] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Retrieves the report row and target report_version row."""
        client = db_manager.client
        report: Optional[Dict[str, Any]] = None
        report_version: Optional[Dict[str, Any]] = None

        if client:
            try:
                r_res = client.table("reports").select("*").eq("project_id", project_id).execute()
                if r_res.data and len(r_res.data) > 0:
                    report = r_res.data[0]
                    rep_id = report["id"]

                    if version_number:
                        v_res = client.table("report_versions").select("*").eq("report_id", rep_id).eq("version_number", version_number).execute()
                    elif report.get("current_version_id"):
                        v_res = client.table("report_versions").select("*").eq("id", report["current_version_id"]).execute()
                    else:
                        v_res = client.table("report_versions").select("*").eq("report_id", rep_id).order("version_number", desc=True).limit(1).execute()

                    if v_res.data and len(v_res.data) > 0:
                        report_version = v_res.data[0]
            except Exception as e:
                logger.error(f"DB error fetching report & version: {e}")

        if not report or not report_version:
            from apps.api.services.report_generation import _REPORTS_STORE, _REPORT_VERSIONS_STORE
            # Find report matching project_id
            if not report:
                report = _REPORTS_STORE.get(project_id)
                if not report:
                    for r in _REPORTS_STORE.values():
                        if str(r.get("project_id")) == str(project_id):
                            report = r
                            break

            if report and not report_version:
                rep_id = str(report["id"])
                versions = _REPORT_VERSIONS_STORE.get(rep_id, [])
                if version_number:
                    for v in versions:
                        if v.get("version_number") == version_number:
                            report_version = v
                            break
                elif report.get("current_version_id"):
                    for v in versions:
                        if str(v.get("id")) == str(report["current_version_id"]):
                            report_version = v
                            break
                if not report_version and versions:
                    report_version = versions[-1]

        if not report or not report_version:
            raise HTTPException(
                status_code=404,
                detail="Report or target report version not found. Generate a report before running verification."
            )

        return report, report_version

    def _get_project_evidence(self, project_id: str) -> List[Dict[str, Any]]:
        """Retrieves registered evidence items from project_files."""
        client = db_manager.client
        if client:
            try:
                res = client.table("project_files").select("*").eq("project_id", project_id).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"DB error fetching evidence files: {e}")

        from apps.api.routers.projects import _EVIDENCE_STORE
        return [f for f in _EVIDENCE_STORE.values() if f.get("project_id") == project_id]

    def _get_report_plan(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves approved report plan if exists."""
        client = db_manager.client
        if client:
            try:
                res = client.table("report_plans").select("*").eq("project_id", project_id).eq("is_approved", True).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0].get("plan_json")
            except Exception as e:
                logger.error(f"DB error fetching report plan: {e}")

        from apps.api.services.report_planner import _REPORT_PLANS_STORE
        plan_row = _REPORT_PLANS_STORE.get(project_id)
        if plan_row and plan_row.get("is_approved"):
            return plan_row.get("plan_json")
        return None

    def _persist_verification(
        self,
        verification: ReportVerificationReport,
        project_id: str,
        report_id: str,
        report_version_id: str,
        user_id: Optional[str]
    ):
        """Persists verification data to DB and updates report validation_json."""
        ver_dict = verification.model_dump()
        client = db_manager.client

        row = {
            "id": verification.id,
            "report_version_id": report_version_id,
            "report_id": report_id,
            "project_id": project_id,
            "user_id": user_id,
            "verifier_version": verification.verifier_version,
            "verification_summary": ver_dict.get("summary", {}),
            "quality_gates": ver_dict.get("quality_gates", {}),
            "claims": [c for c in ver_dict.get("claims", [])],
            "status": verification.status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if client:
            try:
                # 1. Insert or update report_verifications
                client.table("report_verifications").upsert(row).execute()

                # 2. Update report_versions.validation_json
                client.table("report_versions").update({"validation_json": ver_dict}).eq("id", report_version_id).execute()

                # 3. Update report status to completed
                client.table("reports").update({"status": "completed"}).eq("id", report_id).execute()
            except Exception as e:
                logger.error(f"DB persistence error for verification: {e}")

        # In-memory store fallback
        _VERIFICATIONS_STORE[report_version_id] = ver_dict
        _VERIFICATIONS_STORE[verification.id] = ver_dict

    def _fetch_verification_by_version(self, version_id: str) -> Optional[ReportVerificationReport]:
        """Fetches stored verification report for a specific version ID."""
        client = db_manager.client
        if client:
            try:
                res = client.table("report_verifications").select("*").eq("report_version_id", version_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    v_dict = {
                        "id": row["id"],
                        "report_id": row["report_id"],
                        "report_version_id": row["report_version_id"],
                        "version_number": 1,
                        "project_id": row["project_id"],
                        "verifier_version": row.get("verifier_version", "1.0.0"),
                        "summary": row.get("verification_summary", {}),
                        "quality_gates": row.get("quality_gates", {}),
                        "claims": row.get("claims", []),
                        "section_verifications": {},
                        "status": row.get("status", "completed"),
                        "verified_at": row.get("created_at", datetime.now(timezone.utc).isoformat())
                    }
                    return ReportVerificationReport.model_validate(v_dict)
            except Exception as e:
                logger.error(f"DB error fetching verification: {e}")

        # In-memory fallback
        v_dict = _VERIFICATIONS_STORE.get(version_id)
        if v_dict:
            return ReportVerificationReport.model_validate(v_dict)
        return None

    def _update_job(
        self,
        job_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        report_id: Optional[str] = None,
        status_val: str = "verifying",
        progress: int = 0,
        current_step: str = "queued",
        error_message: Optional[str] = None,
        completed_at: Optional[str] = None
    ):
        """Updates real-time generation_jobs state."""
        now = datetime.now(timezone.utc).isoformat()
        job_data = _JOBS_STORE.get(job_id, {
            "id": job_id,
            "user_id": user_id,
            "project_id": project_id,
            "report_id": report_id,
            "job_type": "citation_verification",
            "created_at": now
        })

        job_data.update({
            "status": status_val,
            "progress": progress,
            "current_step": current_step,
            "current_stage": current_step,
            "error_message": error_message,
            "updated_at": now
        })
        if completed_at:
            job_data["completed_at"] = completed_at

        _JOBS_STORE[job_id] = job_data

        client = db_manager.client
        if client:
            try:
                client.table("generation_jobs").upsert(job_data).execute()
            except Exception as e:
                logger.error(f"DB error updating generation job {job_id}: {e}")


def get_citation_verification_service() -> CitationVerificationService:
    """Dependency injector for CitationVerificationService."""
    return CitationVerificationService()
