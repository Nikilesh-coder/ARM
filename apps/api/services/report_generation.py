"""
ARM Stage 7 - Section-by-Section Report Generation Service
Coordinates project information, locked templates, approved report plans,
generation jobs, bounded retries, and versioned report draft persistence.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status

from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.services.template_intelligence import template_intelligence_service
from apps.api.services.report_planner import report_planner_service
from apps.api.services.ai import get_ai_provider, AIProvider
from packages.report_generator import (
    AIReportGenerator,
    GeneratedReport,
    SectionGenerationOutput,
    GenerationMetadata
)

logger = get_logger("report_generation_service")

# In-memory storage for test/offline fallback
_REPORTS_STORE: Dict[str, Dict[str, Any]] = {}
_REPORT_VERSIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}
_GENERATION_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class ReportGenerationService:
    """Service orchestrating section-by-section AI report generation and versioning."""

    @staticmethod
    def _is_valid_uuid(val: Any) -> bool:
        if not val:
            return False
        try:
            uuid.UUID(str(val))
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    @classmethod
    def get_latest_report(
        cls,
        project_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Optional[GeneratedReport]:
        """Retrieves the latest generated report draft for a project."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        report_row = None
        version_row = None

        if client:
            try:
                res = client.table("reports").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    report_row = res.data[0]
                    v_res = client.table("report_versions").select("*").eq("report_id", report_row["id"]).order("version_number", desc=True).limit(1).execute()
                    if v_res.data and len(v_res.data) > 0:
                        version_row = v_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching latest report from DB for {project_id}: {e}")

        if not report_row:
            for r in sorted(_REPORTS_STORE.values(), key=lambda x: str(x.get("created_at", "")), reverse=True):
                if str(r.get("project_id")) == str(project_id):
                    report_row = r
                    versions = _REPORT_VERSIONS_STORE.get(str(r["id"]), [])
                    if versions:
                        version_row = sorted(versions, key=lambda x: x.get("version_number", 1), reverse=True)[0]
                    break

        if not report_row or not version_row:
            return None

        # Build GeneratedReport from version content
        content_json = version_row.get("content_json") or []
        sections = [SectionGenerationOutput.model_validate(s) for s in content_json]

        v_summary = version_row.get("validation_json") or {}
        g_meta = version_row.get("generation_metadata") or {}

        return GeneratedReport(
            report_id=str(report_row["id"]),
            project_id=str(report_row["project_id"]),
            template_id=str(report_row.get("template_id") or ""),
            template_schema_version=str(g_meta.get("template_schema_version", "1.0.0")),
            report_plan_id=str(g_meta.get("report_plan_id", "")),
            report_plan_version=str(g_meta.get("report_plan_version", "1.0.0")),
            version_number=version_row.get("version_number", 1),
            title=report_row.get("title", "Academic Report"),
            sections=sections,
            overall_grounding=v_summary.get("overall_grounding", "grounded"),
            total_word_count=v_summary.get("total_word_count", sum(s.word_count for s in sections)),
            status=report_row.get("status", "completed"),
            metadata=GenerationMetadata.model_validate(g_meta) if g_meta else GenerationMetadata(),
            created_at=str(version_row.get("created_at", report_row.get("created_at", "")))
        )

    @classmethod
    def get_report_versions(
        cls,
        project_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Lists all version history summaries for a project report."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        report_row = None

        if client:
            try:
                res = client.table("reports").select("id").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    report_row = res.data[0]
                    v_res = client.table("report_versions").select("id, version_number, created_at, validation_json, generation_metadata").eq("report_id", report_row["id"]).order("version_number", desc=True).execute()
                    if v_res.data:
                        return v_res.data
            except Exception as e:
                logger.error(f"Error fetching report versions from DB: {e}")

        for r in _REPORTS_STORE.values():
            if str(r.get("project_id")) == str(project_id):
                rep_id = str(r["id"])
                return [
                    {
                        "id": str(v.get("id")),
                        "version_number": v.get("version_number"),
                        "created_at": v.get("created_at"),
                        "validation_json": v.get("validation_json"),
                        "generation_metadata": v.get("generation_metadata")
                    }
                    for v in _REPORT_VERSIONS_STORE.get(rep_id, [])
                ]

        return []

    @classmethod
    def get_report_version(
        cls,
        project_id: str,
        version_number: int,
        user: Optional[Dict[str, Any]] = None
    ) -> Optional[GeneratedReport]:
        """Retrieves a specific historical version of the report."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        report_row = None
        version_row = None

        if client:
            try:
                res = client.table("reports").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    report_row = res.data[0]
                    v_res = client.table("report_versions").select("*").eq("report_id", report_row["id"]).eq("version_number", version_number).limit(1).execute()
                    if v_res.data and len(v_res.data) > 0:
                        version_row = v_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching version {version_number} from DB: {e}")

        if not report_row:
            for r in _REPORTS_STORE.values():
                if str(r.get("project_id")) == str(project_id):
                    report_row = r
                    versions = _REPORT_VERSIONS_STORE.get(str(r["id"]), [])
                    for v in versions:
                        if v.get("version_number") == version_number:
                            version_row = v
                            break
                    break

        if not report_row or not version_row:
            return None

        content_json = version_row.get("content_json") or []
        sections = [SectionGenerationOutput.model_validate(s) for s in content_json]
        v_summary = version_row.get("validation_json") or {}
        g_meta = version_row.get("generation_metadata") or {}

        return GeneratedReport(
            report_id=str(report_row["id"]),
            project_id=str(report_row["project_id"]),
            template_id=str(report_row.get("template_id") or ""),
            template_schema_version=str(g_meta.get("template_schema_version", "1.0.0")),
            report_plan_id=str(g_meta.get("report_plan_id", "")),
            report_plan_version=str(g_meta.get("report_plan_version", "1.0.0")),
            version_number=version_row.get("version_number", version_number),
            title=report_row.get("title", "Academic Report"),
            sections=sections,
            overall_grounding=v_summary.get("overall_grounding", "grounded"),
            total_word_count=v_summary.get("total_word_count", sum(s.word_count for s in sections)),
            status=report_row.get("status", "completed"),
            metadata=GenerationMetadata.model_validate(g_meta) if g_meta else GenerationMetadata(),
            created_at=str(version_row.get("created_at", report_row.get("created_at", "")))
        )

    @classmethod
    def generate_report(
        cls,
        project_id: str,
        user: Optional[Dict[str, Any]] = None,
        force: bool = False,
        ai_provider: Optional[AIProvider] = None
    ) -> GeneratedReport:
        """
        Coordinates the complete Stage 7 Section-by-Section AI Report Generation.
        Enforces:
        - Project ownership & IDOR protection
        - Locked Template prerequisite (Stage 4)
        - Approved Report Plan prerequisite (Stage 6)
        - Stale plan protection (detects project changes after plan approval)
        - Project grounding (Stage 5 project info + evidence)
        - Generation job lifecycle with real section-by-section steps
        - Safe versioning (increments version_number on regeneration)
        """
        from apps.api.routers.projects import _verify_project_ownership

        # 1. Verify Project Ownership & Existence
        project = _verify_project_ownership(project_id, user)
        owner_id = user["id"] if user else (project.get("user_id") or project.get("owner_id") or "usr_demo_student")

        # 2. Retrieve Locked Template (Stage 4 Output)
        client = db_manager.client
        template = None
        template_id = project.get("template_id")

        if client:
            try:
                t_query = client.table("templates").select("*").eq("project_id", project_id)
                if template_id:
                    t_query = t_query.eq("id", template_id)
                t_res = t_query.order("created_at", desc=True).limit(1).execute()
                if t_res.data and len(t_res.data) > 0:
                    template = t_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching template for project {project_id}: {e}")

        if not template:
            from apps.api.routers.templates import _TEMPLATES_DB
            for t in sorted(_TEMPLATES_DB.values(), key=lambda x: str(x.get("created_at", "")), reverse=True):
                if str(t.get("project_id")) == str(project_id):
                    template = t
                    break

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No template found for this project. Please upload and lock a template first."
            )

        template_id = str(template.get("id"))
        is_locked = template.get("is_locked") is True or template.get("status") == "locked"
        if not is_locked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="TEMPLATE_NOT_LOCKED: Template must be locked in Stage 4 before generating report content."
            )

        locked_schema = template_intelligence_service.get_locked_template(template_id)
        if not locked_schema or not locked_schema.get("sections"):
            analysis = template_intelligence_service.get_template_analysis(template_id)
            locked_schema = analysis.get("locked_schema") or analysis.get("reviewed_schema") or analysis.get("schema_json") or {}

        t_version = str(locked_schema.get("schema_version") or template.get("locked_schema_version") or "1.0.0")

        # 3. Retrieve Approved Report Plan (Stage 6 Output)
        report_plan = report_planner_service.get_latest_plan(project_id, user)
        if not report_plan:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="REPORT_PLAN_NOT_FOUND: An approved report plan from Stage 6 is required before generating content."
            )

        if not report_plan.is_approved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PLAN_NOT_APPROVED: The report plan must be reviewed and approved by the student before generation."
            )

        if report_plan.is_stale:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PLAN_STALE: Project information or evidence changed since plan approval. Please regenerate and re-approve the report plan."
            )

        # 4. Retrieve Evidence Locker Inventory (Stage 5)
        evidence_items: List[Dict[str, Any]] = []
        if client:
            try:
                ev_res = client.table("project_files").select("*").eq("project_id", project_id).execute()
                if ev_res.data:
                    evidence_items = ev_res.data
            except Exception as e:
                logger.error(f"Error fetching evidence items for {project_id}: {e}")

        if not evidence_items:
            from apps.api.routers.projects import _EVIDENCE_STORE
            evidence_items = [e for e in _EVIDENCE_STORE.values() if str(e.get("project_id")) == str(project_id)]

        # 5. Look up existing report or initialize new report record
        report_row = None
        if client:
            try:
                res = client.table("reports").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    report_row = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching report: {e}")

        if not report_row:
            for r in _REPORTS_STORE.values():
                if str(r.get("project_id")) == str(project_id):
                    report_row = r
                    break

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        if report_row:
            report_id = str(report_row["id"])
            next_version = (report_row.get("current_version") or 1) + 1
        else:
            report_id = str(uuid.uuid4())
            next_version = 1
            report_row = {
                "id": report_id,
                "project_id": project_id,
                "user_id": owner_id if cls._is_valid_uuid(owner_id) else None,
                "template_id": template_id,
                "title": report_plan.title,
                "status": "generating",
                "current_version": next_version,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            if client:
                try:
                    client.table("reports").insert(report_row).execute()
                except Exception as e:
                    logger.error(f"Error inserting reports record: {e}")
            _REPORTS_STORE[report_id] = report_row

        # 6. Initialize generation job in generation_jobs
        job_id = str(uuid.uuid4())
        job_row = {
            "id": job_id,
            "project_id": project_id,
            "report_id": report_id,
            "user_id": owner_id if cls._is_valid_uuid(owner_id) else None,
            "job_type": "content_generation",
            "status": "running",
            "current_stage": "loading_context",
            "current_step": "Initializing section-by-section generator with approved plan",
            "progress_percentage": 5,
            "metadata": {
                "report_id": report_id,
                "project_id": project_id,
                "version_number": next_version,
                "plan_id": str(report_plan.plan_id or ""),
                "template_id": template_id,
            },
            "created_at": now_iso,
            "updated_at": now_iso
        }

        if client:
            try:
                client.table("generation_jobs").insert(job_row).execute()
            except Exception as e:
                logger.warning(f"Error inserting generation_job: {e}")
        _GENERATION_JOBS_STORE[job_id] = job_row

        # Progress callback for section generation
        def update_job_progress(step_index: int, total_steps: int, section_title: str, stage: str):
            pct = int((step_index / max(total_steps, 1)) * 85) + 10
            job_row["current_stage"] = stage
            job_row["current_step"] = f"{stage.replace('_', ' ').capitalize()}: {section_title} ({step_index}/{total_steps})"
            job_row["progress_percentage"] = min(pct, 95)
            job_row["updated_at"] = datetime.now(timezone.utc).isoformat()
            if client:
                try:
                    client.table("generation_jobs").update({
                        "current_stage": job_row["current_stage"],
                        "current_step": job_row["current_step"],
                        "progress_percentage": job_row["progress_percentage"],
                        "updated_at": job_row["updated_at"]
                    }).eq("id", job_id).execute()
                except Exception:
                    pass

        # 7. Execute Section-by-Section Report Generation
        try:
            generated_report = AIReportGenerator.generate_report(
                report_plan=report_plan,
                project_data=project,
                evidence_items=evidence_items,
                template_id=template_id,
                template_schema_version=t_version,
                ai_provider=ai_provider,
                job_callback=update_job_progress,
                version_number=next_version,
                report_id=report_id
            )

            # 8. Persist Report Version
            version_id = str(uuid.uuid4())
            version_row = {
                "id": version_id,
                "report_id": report_id,
                "version_number": next_version,
                "content_json": [s.model_dump() for s in generated_report.sections],
                "validation_json": {
                    "overall_grounding": generated_report.overall_grounding,
                    "total_word_count": generated_report.total_word_count,
                    "status": "completed"
                },
                "generation_metadata": generated_report.metadata.model_dump(),
                "created_at": now_iso
            }

            if client:
                try:
                    client.table("report_versions").insert(version_row).execute()
                except Exception as e:
                    logger.error(f"Error persisting report_version: {e}")

            if report_id not in _REPORT_VERSIONS_STORE:
                _REPORT_VERSIONS_STORE[report_id] = []
            _REPORT_VERSIONS_STORE[report_id].append(version_row)

            # Update parent report
            report_update = {
                "status": "completed",
                "current_version": next_version,
                "current_version_id": version_id if cls._is_valid_uuid(version_id) else None,
                "updated_at": now_iso
            }
            if client:
                try:
                    client.table("reports").update(report_update).eq("id", report_id).execute()
                except Exception as e:
                    logger.error(f"Error updating report: {e}")
            if report_id in _REPORTS_STORE:
                _REPORTS_STORE[report_id].update(report_update)

            # Complete generation job
            job_row["status"] = "completed"
            job_row["current_stage"] = "completed"
            job_row["current_step"] = "All sections generated and validated successfully"
            job_row["progress_percentage"] = 100
            job_row["completed_at"] = now_iso
            job_row["result_payload"] = {
                "report_id": report_id,
                "version_number": next_version,
                "version_id": version_id,
                "total_sections": len(generated_report.sections),
                "total_words": generated_report.total_word_count
            }

            if client:
                try:
                    client.table("generation_jobs").update(job_row).eq("id", job_id).execute()
                except Exception:
                    pass

            return generated_report

        except Exception as e:
            logger.error(f"Report generation pipeline failure: {e}")
            job_row["status"] = "failed"
            job_row["current_stage"] = "failed"
            job_row["error_message"] = str(e)
            job_row["completed_at"] = now_iso

            if client:
                try:
                    client.table("generation_jobs").update(job_row).eq("id", job_id).execute()
                except Exception:
                    pass

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Report content generation failed: {str(e)}"
            )

    @classmethod
    def get_job(
        cls,
        project_id: str,
        job_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieves status and logs for a content generation job."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        job_data = None
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).eq("project_id", project_id).execute()
                if res.data and len(res.data) > 0:
                    job_data = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching job {job_id}: {e}")

        if not job_data:
            job_data = _GENERATION_JOBS_STORE.get(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail="Generation job not found.")

        return job_data


report_generation_service = ReportGenerationService()
