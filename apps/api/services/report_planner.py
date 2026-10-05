"""
ReportForge AI - Report Planner Service
Stage 6: Coordinates project facts, locked template retrieval, evidence inventory,
job lifecycle, and report plan persistence.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status

from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.services.template_intelligence import template_intelligence_service
from apps.api.services.ai import get_ai_provider, AIProvider
from packages.report_planner import (
    ReportPlan,
    AIReportPlanner,
    ReportPlanValidator
)

logger = get_logger("report_planner_service")

# In-memory storage for test/offline fallback
_REPORT_PLANS_STORE: Dict[str, Dict[str, Any]] = {}
_PLANNER_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class ReportPlannerService:
    """Service orchestrating AI Report Planning execution, validation, and storage."""

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
    def get_latest_plan(cls, project_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[ReportPlan]:
        """Retrieves the latest ReportPlan for a project, evaluating stale state against project modification."""
        client = db_manager.client
        plan_dict = None

        if client:
            try:
                res = client.table("report_plans").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
                if res.data and len(res.data) > 0:
                    plan_dict = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching latest plan from DB for {project_id}: {e}")

        if not plan_dict:
            # Check in-memory store
            for p in sorted(_REPORT_PLANS_STORE.values(), key=lambda x: str(x.get("created_at", "")), reverse=True):
                if str(p.get("project_id")) == str(project_id):
                    plan_dict = p
                    break

        if not plan_dict:
            return None

        # Build Pydantic model from plan_json or record
        plan_json = plan_dict.get("plan_json") or plan_dict
        plan = ReportPlan.model_validate(plan_json)
        plan.plan_id = str(plan_dict.get("id") or plan.plan_id)
        plan.status = str(plan_dict.get("status") or plan.status)
        plan.is_approved = bool(plan_dict.get("is_approved", False))
        plan.approved_at = str(plan_dict.get("approved_at") or "") if plan_dict.get("approved_at") else None
        plan.approved_by = str(plan_dict.get("approved_by") or "") if plan_dict.get("approved_by") else None

        # Evaluate stale status
        # Compare project updated_at with plan created_at
        project_mod = str(plan_dict.get("project_updated_at") or "")
        from apps.api.routers.projects import _verify_project_ownership
        try:
            proj = _verify_project_ownership(project_id, user)
            current_mod = str(proj.get("updated_at") or "")
            if current_mod and project_mod and current_mod > project_mod:
                plan.is_stale = True
        except Exception:
            pass

        return plan

    @classmethod
    def create_report_plan(
        cls,
        project_id: str,
        user: Optional[Dict[str, Any]] = None,
        force: bool = False,
        ai_provider: Optional[AIProvider] = None,
        target_page_count: Optional[int] = None
    ) -> ReportPlan:
        """
        Coordinates the complete Stage 6 AI Report Planning pipeline.
        Enforces locked template prerequisite, project grounding, and deterministic validation.
        """
        from apps.api.routers.projects import _verify_project_ownership, ALLOWED_EVIDENCE_EXTENSIONS

        # 1. Verify Project Ownership & Existence
        project = _verify_project_ownership(project_id, user)
        owner_id = user["id"] if user else (project.get("user_id") or project.get("owner_id") or "usr_demo_student")

        # 2. Retrieve Locked Template (Stage 4 Output)
        client = db_manager.client
        template = None
        template_id = project.get("template_id")

        if client:
            try:
                # Query templates for this project
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
                detail="No template found for this project. Please upload a template first."
            )

        template_id = str(template.get("id"))

        # Prerequisite: Template MUST be locked
        is_locked = template.get("is_locked") is True or template.get("status") == "locked"
        if not is_locked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="TEMPLATE_NOT_LOCKED: Template must be reviewed and locked in Stage 4 before creating a report plan."
            )

        # Retrieve authoritative locked schema
        locked_schema = template_intelligence_service.get_locked_template(template_id)
        if not locked_schema or not locked_schema.get("sections"):
            # Fallback to source schema if locked schema is being initialized
            analysis = template_intelligence_service.get_template_analysis(template_id)
            locked_schema = analysis.get("locked_schema") or analysis.get("reviewed_schema") or analysis.get("schema_json") or {}

        if not locked_schema or not locked_schema.get("sections"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Locked template schema has no valid sections to plan from."
            )

        # 3. Retrieve Evidence Locker Inventory (Metadata only)
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

        # 4. Check Idempotency (if not forcing regeneration)
        t_version = str(locked_schema.get("schema_version") or template.get("locked_schema_version") or "1.0.0")
        proj_updated = str(project.get("updated_at") or "")

        if not force:
            existing_plan = cls.get_latest_plan(project_id, user)
            if existing_plan and not existing_plan.is_stale:
                if existing_plan.template_schema_version == t_version:
                    logger.info(f"Returning cached authoritative report plan for project {project_id}")
                    return existing_plan

        # 5. Initialize Planning Job Lifecycle in generation_jobs
        job_id = str(uuid.uuid4())
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        job_row = {
            "id": job_id,
            "project_id": project_id,
            "user_id": owner_id if cls._is_valid_uuid(owner_id) else None,
            "job_type": "report_planning",
            "status": "running",
            "current_stage": "planning",
            "current_step": "Synthesizing template structure and project ground truth",
            "progress_percentage": 50,
            "metadata": {
                "plan_id": plan_id,
                "project_id": project_id,
                "template_id": template_id,
                "template_schema_version": t_version,
            },
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if client:
            try:
                client.table("generation_jobs").insert(job_row).execute()
            except Exception as e:
                logger.warning(f"Note inserting generation_job: {e}")

        _PLANNER_JOBS_STORE[job_id] = job_row

        # 6. Execute AI Report Planning Engine
        pages = target_page_count or project.get("target_page_count") or 30

        try:
            # Transition job to validating
            job_row["current_stage"] = "validating"
            job_row["current_step"] = "Executing deterministic template constraint validation"
            job_row["progress_percentage"] = 80

            plan = AIReportPlanner.plan(
                locked_template_schema=locked_schema,
                project_data=project,
                evidence_items=evidence_items,
                ai_provider=ai_provider,
                target_page_count=pages,
                plan_id=plan_id
            )

            # 7. Persist Validated Plan
            plan_dict = plan.model_dump()
            db_plan_row = {
                "id": plan_id,
                "project_id": project_id,
                "template_id": template_id,
                "user_id": owner_id if cls._is_valid_uuid(owner_id) else None,
                "title": plan.title,
                "template_schema_version": t_version,
                "project_updated_at": proj_updated,
                "planner_version": "1.0.0",
                "ai_provider": plan.planner_metadata.ai_provider,
                "ai_model": plan.planner_metadata.ai_model,
                "status": "completed",
                "plan_json": plan_dict,
                "summary_metrics": plan.summary_metrics.model_dump(),
                "is_approved": False,
                "created_at": now_iso,
                "updated_at": now_iso,
                "completed_at": now_iso,
            }

            if client:
                try:
                    client.table("report_plans").insert(db_plan_row).execute()
                except Exception as e:
                    logger.error(f"Error persisting report_plan to DB: {e}")

            _REPORT_PLANS_STORE[plan_id] = db_plan_row

            # Complete generation job
            job_row["status"] = "completed"
            job_row["current_stage"] = "completed"
            job_row["current_step"] = "Report plan successfully generated and verified"
            job_row["progress_percentage"] = 100
            job_row["completed_at"] = now_iso
            job_row["result_payload"] = {"plan_id": plan_id}

            if client:
                try:
                    client.table("generation_jobs").update(job_row).eq("id", job_id).execute()
                except Exception:
                    pass

            return plan

        except Exception as e:
            logger.error(f"Planning failure: {e}")
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
                detail=f"Report planning failed: {str(e)}"
            )

    @classmethod
    def approve_plan(cls, project_id: str, plan_id: str, user: Optional[Dict[str, Any]] = None) -> ReportPlan:
        """Approves a generated report plan."""
        from apps.api.routers.projects import _verify_project_ownership
        _verify_project_ownership(project_id, user)

        client = db_manager.client
        now = datetime.now(timezone.utc)
        user_id = user["id"] if user else None
        db_user_id = user_id if cls._is_valid_uuid(user_id) else None

        update_fields = {
            "status": "approved",
            "is_approved": True,
            "approved_at": now.isoformat(),
            "approved_by": db_user_id,
            "updated_at": now.isoformat(),
        }

        if client:
            try:
                client.table("report_plans").update(update_fields).eq("id", plan_id).eq("project_id", project_id).execute()
            except Exception as e:
                logger.error(f"Error approving plan in DB: {e}")

        if plan_id in _REPORT_PLANS_STORE:
            _REPORT_PLANS_STORE[plan_id].update(update_fields)

        plan = cls.get_latest_plan(project_id, user)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        return plan

    @classmethod
    def get_job(cls, project_id: str, job_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieves status and logs for a planning generation job."""
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
            job_data = _PLANNER_JOBS_STORE.get(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail="Planning job not found.")

        return job_data


report_planner_service = ReportPlannerService()
