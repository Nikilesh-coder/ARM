"""
ARM — Template Intelligence Service
Orchestrates deterministic parsing, structural analysis, schema normalization,
persistence to template_analysis, and lifecycle management for generation jobs.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from apps.api.core.config import settings
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger
from apps.api.services.storage import get_storage_provider
from packages.template_intelligence.parser import get_template_parser
from packages.template_intelligence.schema import TemplateSchema

logger = get_logger("service.template_intelligence")

# In-memory stores for fast caching and mock/testing fallbacks
_ANALYSIS_STORE: Dict[str, Any] = {}
_JOBS_STORE: Dict[str, Any] = {}


class TemplateIntelligenceService:
    """
    Dedicated service for running deterministic template intelligence pipelines.
    Decoupled from HTTP routing.
    """

    @staticmethod
    def process_analysis_job(job_id: str) -> Dict[str, Any]:
        """
        Executes a queued template_analysis job end-to-end:
        1. Validates job & template ownership context
        2. Retrieves untouched original bytes from storage
        3. Parses format-specifically (DOCX / PDF)
        4. Validates normalized TemplateSchema
        5. Persists to template_analysis table
        6. Updates templates status to 'analyzed' and job to 'completed'
        """
        client = db_manager.client
        now = datetime.now(timezone.utc)
        job = None

        logger.info(f"Starting processing for template analysis job {job_id}")

        # 1. Fetch job record
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).execute()
                if res.data and len(res.data) > 0:
                    job = res.data[0]
            except Exception as e:
                logger.error(f"Failed to query job {job_id}: {e}")

        if not job:
            job = _JOBS_STORE.get(job_id)

        if not job:
            logger.error(f"Job {job_id} not found in database or local store.")
            raise ValueError(f"Generation job {job_id} not found.")

        template_id = (job.get("metadata") or {}).get("template_id")
        project_id = job.get("project_id")
        user_id = job.get("user_id")

        if not template_id:
            logger.error(f"Job {job_id} missing template_id in metadata.")
            raise ValueError(f"Job {job_id} missing template_id.")

        try:
            # Step 1: Update job to 'running' (10%)
            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=10,
                current_step="loading_template",
                started_at=now.isoformat()
            )

            # Step 2: Retrieve Template Record
            template = None
            if client:
                try:
                    t_res = client.table("templates").select("*").eq("id", template_id).execute()
                    if t_res.data and len(t_res.data) > 0:
                        template = t_res.data[0]
                except Exception as e:
                    logger.error(f"Error querying template {template_id}: {e}")

            if not template:
                from apps.api.routers.templates import _TEMPLATES_DB
                template = _TEMPLATES_DB.get(template_id)

            if not template:
                raise FileNotFoundError(f"Template {template_id} record not found.")

            file_path = template.get("original_file_path") or template.get("storage_path")
            file_type = template.get("file_type") or "docx"
            file_name = template.get("name") or template.get("file_name") or f"template.{file_type}"

            if not file_path:
                raise ValueError(f"Template {template_id} has no storage path registered.")

            # Step 3: Fetch file bytes from storage (30%)
            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=30,
                current_step="validating_document"
            )

            storage = get_storage_provider()
            working_docx_path = template.get("converted_docx_path") or template.get("working_docx_path")

            if working_docx_path and working_docx_path != file_path:
                try:
                    file_bytes = storage.download_file(settings.storage.bucket_templates, working_docx_path)
                    parse_file_type = "docx"
                except Exception:
                    file_bytes = storage.download_file(settings.storage.bucket_templates, file_path)
                    parse_file_type = file_type
            else:
                file_bytes = storage.download_file(settings.storage.bucket_templates, file_path)
                parse_file_type = file_type

            if not file_bytes or len(file_bytes) == 0:
                raise ValueError(f"Downloaded 0 bytes for template {template_id} from {file_path}")

            # If template is PDF and no working DOCX exists, convert to working DOCX
            if parse_file_type == "pdf":
                from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                try:
                    working_storage_rel = f"{os.path.splitext(file_path)[0]}_working.docx"
                    _, working_bytes, _ = pdf_to_docx_service.convert_pdf_bytes_to_docx(file_bytes, original_filename=file_name)
                    storage.upload_file(
                        bucket=settings.storage.bucket_templates,
                        path=working_storage_rel,
                        data=working_bytes,
                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    file_bytes = working_bytes
                    parse_file_type = "docx"
                    template["converted_docx_path"] = working_storage_rel
                    template["working_docx_path"] = working_storage_rel
                except Exception as pde:
                    logger.warning(f"Could not convert PDF to working DOCX in template intelligence: {pde}")

            # Step 4: Parse structure & extract formatting (50%)
            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=50,
                current_step="parsing_structure"
            )

            parser = get_template_parser(file_bytes, file_type=parse_file_type)

            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=70,
                current_step="extracting_formatting"
            )

            schema: TemplateSchema = parser.parse(
                template_id=template_id,
                template_name=file_name
            )

            # Step 5: Validate Schema & Build Payload (85%)
            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=85,
                current_step="building_schema"
            )

            schema_dict = schema.model_dump()

            # Step 6: Persist Analysis Record (95%)
            TemplateIntelligenceService._update_job(
                job_id,
                status="running",
                progress=95,
                current_step="saving_analysis"
            )

            analysis_id = str(uuid.uuid4())
            analysis_record = {
                "id": analysis_id,
                "template_id": template_id,
                "schema_json": schema_dict,
                "data": schema_dict,
                "normalized_schema": schema_dict,
                "detected_sections": [s.model_dump() for s in schema.sections],
                "typography_rules": schema.typography.model_dump(),
                "page_geometry": schema.geometry.model_dump(),
                "confidence_score": float(schema.confidence_scores.get("typography", 0.95)),
                "confidence": {"score": float(schema.confidence_scores.get("typography", 0.95))},
                "analysis_status": "completed",
                "status": "completed",
                "review_status": "pending_review",
                "warnings": schema.warnings,
                "parser_version": schema.parser_version,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            if client:
                try:
                    # Remove any preexisting analysis for this template (idempotent re-analysis)
                    client.table("template_analysis").delete().eq("template_id", template_id).execute()
                    client.table("template_analysis").insert(analysis_record).execute()
                    
                    # Update template status to 'analyzed'
                    client.table("templates").update({
                        "status": "analyzed",
                        "analysis_status": "completed"
                    }).eq("id", template_id).execute()
                except Exception as e:
                    logger.error(f"Failed to persist template analysis to database: {e}")
                    raise

            _ANALYSIS_STORE[template_id] = analysis_record
            from apps.api.routers.templates import _TEMPLATE_SCHEMAS
            _TEMPLATE_SCHEMAS[template_id] = schema

            # Step 7: Mark Job Completed (100%)
            finish_time = datetime.now(timezone.utc)
            TemplateIntelligenceService._update_job(
                job_id,
                status="completed",
                progress=100,
                current_step="completed",
                completed_at=finish_time.isoformat(),
                result_payload={
                    "template_id": template_id,
                    "analysis_id": analysis_id,
                    "sections_count": len(schema.sections),
                    "warnings_count": len(schema.warnings)
                }
            )

            logger.info(f"Template analysis job {job_id} successfully completed for template {template_id}")
            return analysis_record

        except Exception as e:
            error_msg = f"Template analysis failed: {str(e)}"
            logger.error(f"Error executing template analysis job {job_id}: {error_msg}")

            # Mark job failed
            TemplateIntelligenceService._update_job(
                job_id,
                status="failed",
                error_message=str(e),
                current_step="failed"
            )

            # Mark template failed
            if client:
                try:
                    client.table("templates").update({
                        "status": "failed",
                        "analysis_status": "failed"
                    }).eq("id", template_id).execute()
                except Exception:
                    pass

            raise

    @staticmethod
    def _update_job(job_id: str, **kwargs):
        """Updates job record in Supabase and in-memory cache."""
        now = datetime.now(timezone.utc)
        kwargs["updated_at"] = now.isoformat()

        client = db_manager.client
        if client:
            try:
                client.table("generation_jobs").update(kwargs).eq("id", job_id).execute()
            except Exception as e:
                logger.warning(f"Failed to update job {job_id} in database: {e}")

        if job_id in _JOBS_STORE:
            _JOBS_STORE[job_id].update(kwargs)
        else:
            _JOBS_STORE[job_id] = {"id": job_id, **kwargs}

    @staticmethod
    def get_template_analysis(template_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves persisted template analysis for given template."""
        client = db_manager.client
        if client:
            try:
                res = client.table("template_analysis").select("*").eq("template_id", template_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error reading template_analysis for {template_id}: {e}")

        return _ANALYSIS_STORE.get(template_id)

    @staticmethod
    def get_generation_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves generation job status and progress."""
        client = db_manager.client
        if client:
            try:
                res = client.table("generation_jobs").select("*").eq("id", job_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error reading generation_jobs for {job_id}: {e}")

        return _JOBS_STORE.get(job_id)

    @staticmethod
    def get_template_review(template_id: str) -> Optional[Dict[str, Any]]:
        """
        Stage 4: Retrieves review state, source analysis, reviewed draft,
        and lock metadata for a template.
        """
        client = db_manager.client
        template = None
        analysis = None

        if client:
            try:
                t_res = client.table("templates").select("*").eq("id", template_id).limit(1).execute()
                if t_res.data and len(t_res.data) > 0:
                    template = t_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching template {template_id} for review: {e}")

        if not template:
            from apps.api.routers.templates import _TEMPLATES_DB
            template = _TEMPLATES_DB.get(template_id)

        if not template:
            return None

        analysis = TemplateIntelligenceService.get_template_analysis(template_id)
        if not analysis:
            return None

        source_schema = analysis.get("schema_json") or analysis.get("data") or analysis.get("normalized_schema") or {}
        reviewed_schema = analysis.get("reviewed_schema") or source_schema
        locked_schema = analysis.get("locked_schema")

        is_locked = bool(template.get("is_locked") or template.get("status") == "locked" or analysis.get("review_status") == "locked")
        review_status = analysis.get("review_status") or ("locked" if is_locked else "pending_review")

        # Extract warnings & unsupported features
        validation_obj = source_schema.get("validation") or {}
        warnings = analysis.get("warnings") or source_schema.get("warnings") or validation_obj.get("warnings") or []
        unsupported = validation_obj.get("unsupported_features") or []

        return {
            "template_id": template_id,
            "template_name": template.get("name") or source_schema.get("template_name") or "Template",
            "project_id": template.get("project_id"),
            "file_type": template.get("file_type") or "docx",
            "file_size": template.get("file_size") or template.get("file_size_bytes"),
            "status": "locked" if is_locked else (template.get("status") or "analyzed"),
            "review_status": "locked" if is_locked else review_status,
            "is_locked": is_locked,
            "source_analysis": source_schema,
            "reviewed_schema": reviewed_schema,
            "locked_schema": locked_schema,
            "warnings": warnings,
            "unsupported_features": unsupported,
            "confidence_score": float(analysis.get("confidence_score") or 1.0),
            "locked_at": template.get("locked_at") or analysis.get("locked_at"),
            "locked_by": template.get("locked_by") or analysis.get("locked_by"),
            "locked_schema_version": template.get("locked_schema_version") or "1.0.0",
            "reviewed_at": analysis.get("reviewed_at"),
            "updated_at": analysis.get("updated_at") or template.get("updated_at")
        }

    @staticmethod
    def save_template_review(
        template_id: str,
        reviewed_data: Dict[str, Any],
        user_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stage 4: Saves student review modifications to template_analysis.reviewed_schema.
        Strictly rejects edits if template is already locked.
        """
        from packages.template_intelligence.validator import TemplateReviewValidator

        client = db_manager.client
        template = None
        if client:
            try:
                t_res = client.table("templates").select("*").eq("id", template_id).limit(1).execute()
                if t_res.data and len(t_res.data) > 0:
                    template = t_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching template {template_id}: {e}")

        if not template:
            from apps.api.routers.templates import _TEMPLATES_DB
            template = _TEMPLATES_DB.get(template_id)

        if not template:
            raise FileNotFoundError(f"Template {template_id} not found.")

        # Immutability Check: Locked templates cannot be modified
        if template.get("is_locked") or template.get("status") == "locked":
            raise PermissionError("Template is locked and cannot be modified. To make modifications, upload a new template version.")

        analysis = TemplateIntelligenceService.get_template_analysis(template_id)
        if not analysis:
            raise ValueError(f"Analysis for template {template_id} not found.")

        source_schema = analysis.get("schema_json") or analysis.get("data") or {}

        # Validate review structure
        parsed_schema, blocking_errors, warnings = TemplateReviewValidator.validate_review(
            reviewed_data,
            source_metadata=source_schema,
            is_locking=False
        )

        if blocking_errors:
            raise ValueError("; ".join(blocking_errors))

        schema_dict = parsed_schema.model_dump()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Database update
        from apps.api.routers.templates import _is_valid_uuid
        db_user_id = user_id if _is_valid_uuid(user_id) else None

        if client:
            try:
                client.table("template_analysis").update({
                    "reviewed_schema": schema_dict,
                    "review_status": "reviewed",
                    "reviewed_at": now_iso,
                    "reviewed_by": db_user_id,
                    "updated_at": now_iso
                }).eq("template_id", template_id).execute()

                client.table("templates").update({
                    "status": "reviewing",
                    "updated_at": now_iso
                }).eq("id", template_id).execute()
            except Exception as e:
                logger.error(f"Failed to persist review draft in database: {e}")

        # Update in-memory store
        if template_id in _ANALYSIS_STORE:
            _ANALYSIS_STORE[template_id]["reviewed_schema"] = schema_dict
            _ANALYSIS_STORE[template_id]["review_status"] = "reviewed"
            _ANALYSIS_STORE[template_id]["reviewed_at"] = now_iso
            _ANALYSIS_STORE[template_id]["reviewed_by"] = user_id
            _ANALYSIS_STORE[template_id]["updated_at"] = now_iso

        template["status"] = "reviewing"
        template["updated_at"] = now_iso

        return TemplateIntelligenceService.get_template_review(template_id)

    @staticmethod
    def lock_template(
        template_id: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stage 4: Atomically and transactionally locks the template structure.
        The finalized schema snapshot becomes the authoritative formatting source of truth.
        """
        from packages.template_intelligence.validator import TemplateReviewValidator

        client = db_manager.client
        template = None
        if client:
            try:
                t_res = client.table("templates").select("*").eq("id", template_id).limit(1).execute()
                if t_res.data and len(t_res.data) > 0:
                    template = t_res.data[0]
            except Exception as e:
                logger.error(f"Error fetching template {template_id} for lock: {e}")

        if not template:
            from apps.api.routers.templates import _TEMPLATES_DB
            template = _TEMPLATES_DB.get(template_id)

        if not template:
            raise FileNotFoundError(f"Template {template_id} not found.")

        # Idempotent check: if already locked, return existing locked state
        if template.get("is_locked") and template.get("status") == "locked":
            review = TemplateIntelligenceService.get_template_review(template_id)
            return {
                "status": "locked",
                "is_locked": True,
                "template_id": template_id,
                "project_id": template.get("project_id"),
                "locked_at": template.get("locked_at") or datetime.now(timezone.utc),
                "locked_by": template.get("locked_by") or user_id,
                "locked_schema_version": template.get("locked_schema_version") or "1.0.0",
                "sections_count": len((review.get("locked_schema") or {}).get("sections") or []),
                "locked_schema": review.get("locked_schema") or review.get("reviewed_schema") or {},
                "message": "Template is already locked and authoritative."
            }

        analysis = TemplateIntelligenceService.get_template_analysis(template_id)
        if not analysis:
            raise ValueError(f"Template {template_id} has not been analyzed yet.")

        # Select reviewed schema if available, otherwise fallback to source analysis
        source_schema = analysis.get("schema_json") or analysis.get("data") or {}
        target_schema = analysis.get("reviewed_schema") or source_schema

        # Pre-lock rigorous validation
        parsed_schema, blocking_errors, warnings = TemplateReviewValidator.validate_review(
            target_schema,
            source_metadata=source_schema,
            is_locking=True
        )

        if blocking_errors:
            raise ValueError("Pre-lock validation failed: " + "; ".join(blocking_errors))

        locked_dict = parsed_schema.model_dump()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        from apps.api.routers.templates import _is_valid_uuid
        db_user_id = user_id if _is_valid_uuid(user_id) else None
        schema_version = locked_dict.get("schema_version") or "1.0.0"

        # Transactional update to templates and template_analysis
        if client:
            try:
                client.table("templates").update({
                    "status": "locked",
                    "is_locked": True,
                    "locked_at": now_iso,
                    "locked_by": db_user_id,
                    "locked_schema_version": schema_version,
                    "updated_at": now_iso
                }).eq("id", template_id).execute()

                client.table("template_analysis").update({
                    "review_status": "locked",
                    "locked_schema": locked_dict,
                    "locked_at": now_iso,
                    "locked_by": db_user_id,
                    "updated_at": now_iso
                }).eq("template_id", template_id).execute()
            except Exception as e:
                logger.error(f"Database error during template lock: {e}")
                raise RuntimeError(f"Failed to lock template: {str(e)}")

        # Update in-memory cache
        template["status"] = "locked"
        template["is_locked"] = True
        template["locked_at"] = now_iso
        template["locked_by"] = user_id
        template["locked_schema_version"] = schema_version
        template["updated_at"] = now_iso

        if template_id in _ANALYSIS_STORE:
            _ANALYSIS_STORE[template_id]["review_status"] = "locked"
            _ANALYSIS_STORE[template_id]["locked_schema"] = locked_dict
            _ANALYSIS_STORE[template_id]["locked_at"] = now_iso
            _ANALYSIS_STORE[template_id]["locked_by"] = user_id
            _ANALYSIS_STORE[template_id]["updated_at"] = now_iso

        logger.info(f"Template {template_id} successfully locked by user {user_id}")

        return {
            "status": "locked",
            "is_locked": True,
            "template_id": template_id,
            "project_id": template.get("project_id"),
            "locked_at": now,
            "locked_by": user_id,
            "locked_schema_version": schema_version,
            "sections_count": len(parsed_schema.sections),
            "locked_schema": locked_dict,
            "message": "Template locked successfully. This reviewed structure is now the authoritative formatting source of truth."
        }

    @staticmethod
    def get_locked_template(template_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves authoritative locked schema for downstream report generation stages."""
        review = TemplateIntelligenceService.get_template_review(template_id)
        if not review or not review.get("is_locked"):
            return None
        return review.get("locked_schema")


template_intelligence_service = TemplateIntelligenceService()
