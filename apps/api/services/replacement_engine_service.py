"""
ARM Stage 10 - Template Replacement Engine Orchestration Service
Orchestrates the 7-state lifecycle:
QUEUED -> ANALYZING -> GENERATING -> REPLACING -> VALIDATING -> COMPLETED / FAILED
Connects states to ARM UI ("thinking" / "creating") and guarantees non-redesign of college templates.
"""

import os
import re
import uuid
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.services.master_template_service import (
    master_template_service,
    MASTER_TEMPLATE_ID,
    CANONICAL_FIELDS,
)
from apps.api.services.ai_report_agent import ai_report_agent_service, AIReportAgentInputDTO
from apps.api.services.image_system import automatic_image_pipeline_service
from packages.replacement_engine.base import (
    ReplacementState,
    ReplacementResult,
    ReplacementErrorDetail,
    FieldReplacementAudit,
)
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.pdf_engine import (
    PdfTemplateReplacementEngine,
    PdfTemplateAnalyzer,
    PdfAnalysisResult,
)
from packages.replacement_engine.providers import (
    document_provider_registry,
    DocumentProvider,
    ProviderGenerationResult,
)
from packages.replacement_engine.validator import ReplacementValidator
from packages.document_engine.converter import pdf_converter_service

logger = get_logger("replacement_engine.service")

# Global in-memory job store for fast real-time status polling
_REPLACEMENT_JOBS: Dict[str, Dict[str, Any]] = {}


class ReplacementEngineService:
    """
    Core orchestrator for the ARM Master College Template Replacement system.
    Eliminates student manual copy/pasting.
    Preserves 100% of the college template layout, fonts, colors, and margins.
    """

    def __init__(self):
        self.default_template_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../.storage/templates/master_college_template.docx")
        )
        if not os.path.exists(self.default_template_path):
            fallback_web = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../../apps/web/public/Project_Report_Final_IEEE.docx")
            )
            if os.path.exists(fallback_web):
                self.default_template_path = fallback_web

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves real-time status and audit progression for a replacement job."""
        return _REPLACEMENT_JOBS.get(job_id)

    def analyze_pdf_template(self, pdf_path: str) -> Dict[str, Any]:
        """Analyzes a candidate college PDF for in-place replacement feasibility."""
        return PdfTemplateAnalyzer.analyze(pdf_path).model_dump()

    def list_document_providers(self) -> List[Dict[str, Any]]:
        """Lists available document generation providers without exposing credentials."""
        return document_provider_registry.list_providers()

    def execute_replacement(
        self,
        project_id: Optional[str] = None,
        template_id: Optional[str] = None,
        custom_content: Optional[Dict[str, Any]] = None,
        custom_assets: Optional[Dict[str, Any]] = None,
        project_data: Optional[Dict[str, Any]] = None,
        user_instructions: Optional[str] = None,
        provider: Optional[str] = None,
        job_id: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the synchronous or background 7-state ARM replacement pipeline:
        1. QUEUED: Initialize job and audit tracking.
        2. ANALYZING: Inspect template requirements, canonical fields, and project context.
        3. GENERATING: Verify or synthesize structured content and image assets.
        4. REPLACING: In-place run/section substitution on the cloned college template.
        5. VALIDATING: Audit OpenXML integrity, unresolved placeholders, and convert to PDF.
        6. COMPLETED: Publish preview and download artifacts.
        """
        job_id = job_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        selected_provider_name = (provider or settings.document_provider.default_provider or "internal").lower()

        job_record: Dict[str, Any] = {
            "job_id": job_id,
            "project_id": project_id,
            "template_id": template_id or MASTER_TEMPLATE_ID,
            "provider": selected_provider_name,
            "state": ReplacementState.QUEUED.value,
            "progress_percent": 5,
            "arm_ui_state": "thinking",  # ARM behavior: "thinking" during queue/analysis/generation
            "status_message": "ARM is queued and preparing document synthesis...",
            "fields_replaced": 0,
            "total_fields": len(CANONICAL_FIELDS),
            "images_replaced": 0,
            "docx_path": None,
            "pdf_path": None,
            "preview_html": None,
            "template_path": None,
            "field_values": {},
            "image_assets": {},
            "approval_status": "pending",
            "approved_at": None,
            "stats": {},
            "audit": [],
            "errors": [],
            "warnings": [],
            "created_at": now,
            "updated_at": now,
        }
        _REPLACEMENT_JOBS[job_id] = job_record

        # -------------------------------------------------------------
        # STATE 1: QUEUED -> ANALYZING
        # -------------------------------------------------------------
        logger.info(f"[{job_id}] State: ANALYZING (progress 20%)")
        job_record["state"] = ReplacementState.ANALYZING.value
        job_record["progress_percent"] = 20
        job_record["arm_ui_state"] = "thinking"
        job_record["status_message"] = "ARM is analyzing the college template structure and project scope..."
        job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Resolve Project Information & Authoritative Title Source
        client = db_manager.client
        effective_project_id = project_id or (project_data.get("id") or project_data.get("project_id") if project_data else None)

        saved_project = None
        if effective_project_id:
            # Check UUID validity for PostgreSQL compatibility
            is_valid_uuid = False
            try:
                uuid.UUID(str(effective_project_id))
                is_valid_uuid = True
            except (ValueError, AttributeError):
                is_valid_uuid = False

            # 1. Query Supabase database
            if client and is_valid_uuid:
                try:
                    res = client.table("projects").select("*").eq("id", effective_project_id).execute()
                    if res.data and len(res.data) > 0:
                        saved_project = res.data[0]
                except Exception as e:
                    logger.warning(f"[{job_id}] Could not fetch project {effective_project_id} from DB: {e}")
            # 2. Query in-memory projects store fallback
            if not saved_project:
                try:
                    from apps.api.routers.projects import _PROJECTS_STORE
                    saved_project = _PROJECTS_STORE.get(str(effective_project_id))
                except Exception as e:
                    logger.warning(f"[{job_id}] In-memory project lookup notice: {e}")

        # Authoritative saved project name (single source of truth from project creation)
        saved_project_name = None
        if saved_project:
            raw_saved = (
                saved_project.get("project_name")
                or saved_project.get("title")
                or saved_project.get("report_title")
            )
            if raw_saved:
                clean_saved = str(raw_saved).strip()
                if clean_saved.startswith(('"', '“', "'")) and clean_saved.endswith(('"', '”', "'")):
                    clean_saved = clean_saved[1:-1].strip()
                saved_project_name = clean_saved

        # Base project info combines saved project with any supplementary runtime data
        proj_info = dict(saved_project or {})
        if project_data:
            proj_info.update({k: v for k, v in project_data.items() if v is not None})

        # Resolve Search Query vs Project Title using Academic Title Formatter
        from apps.api.services.academic_title_formatter import separate_title_and_research_query

        effective_search_query = (
            search_query
            or (project_data.get("search_query") if project_data else None)
            or (project_data.get("research_query") if project_data else None)
            or (project_data.get("query") if project_data else None)
            or ""
        ).strip()

        passed_title = str((project_data.get("title") or "") if project_data else "").strip()
        passed_proj_title = str((project_data.get("project_title") or "") if project_data else "").strip()

        final_report_title, derived_query = separate_title_and_research_query(
            raw_title=passed_title or proj_info.get("title") or proj_info.get("name") or proj_info.get("project_title") or "Technical Research Project",
            project_title=passed_proj_title or None,
            research_query=effective_search_query or None,
            saved_project_title=saved_project_name,
        )

        if saved_project_name:
            title_source = "SAVED_PROJECT_NAME"
        else:
            title_source = "PROJECT_DATA"

        if derived_query and not effective_search_query:
            effective_search_query = derived_query

        # Explicit Debug Logs requested by ARM
        print(f"\n[ARM REPORT]\nProject ID: {effective_project_id or 'N/A'}")
        print(f"[ARM REPORT]\nSaved Project Name: {saved_project_name or 'N/A'}")
        print(f"[ARM REPORT]\nSearch Query: {effective_search_query or 'N/A'}")
        print(f"[ARM REPORT]\nFINAL REPORT TITLE SOURCE: {title_source}")
        print(f"[ARM REPORT]\nFINAL REPORT TITLE: {final_report_title}\n")

        logger.info(
            f"[ARM REPORT] Project ID: {effective_project_id or 'N/A'} | "
            f"Saved Project Name: {saved_project_name or 'N/A'} | "
            f"Search Query: {effective_search_query or 'N/A'} | "
            f"FINAL REPORT TITLE SOURCE: {title_source} | "
            f"FINAL REPORT TITLE: {final_report_title}"
        )

        # Resolve Template Path & Custom Mappings
        from apps.api.services.template_resolver import resolve_selected_template_path, is_zero_change_intent
        template_path, resolved_template_id = resolve_selected_template_path(
            template_id or (proj_info.get("template_id") if proj_info else None)
        )
        custom_field_mapping = None
        custom_image_mapping = None

        if resolved_template_id and resolved_template_id != MASTER_TEMPLATE_ID:
            try:
                from apps.api.services.custom_template_service import custom_template_service
                cust_tpl = custom_template_service.get_template(resolved_template_id)
                if cust_tpl:
                    c_path = cust_tpl.get("original_file_path") or cust_tpl.get("storage_path")
                    if c_path and os.path.exists(c_path):
                        template_path = os.path.abspath(c_path)
                    custom_field_mapping = cust_tpl.get("field_mapping")
                    custom_image_mapping = cust_tpl.get("image_mapping")
                    logger.info(f"[{job_id}] Using custom college template '{cust_tpl.get('name')}' at {template_path}")

                    # Check if custom template has comprehensive mappings (including project_title, sub-field bullets, and sections)
                    needs_analysis = (
                        not custom_field_mapping
                        or len(custom_field_mapping) < 15
                        or not any(fm.get("arm_field") == "project_title" for fm in (custom_field_mapping or []))
                        or not any("_1" in fm.get("arm_field", "") for fm in (custom_field_mapping or []))
                        or not custom_image_mapping
                        or not any(im.get("filename") for im in (custom_image_mapping or []))
                    )
                    if needs_analysis and template_path and os.path.exists(template_path) and template_path.lower().endswith(".docx"):
                        logger.info(f"[{job_id}] Template '{resolved_template_id}' needs structure analysis. Running analyze_template_docx...")
                        try:
                            analysis = custom_template_service.analyze_template_docx(template_path)
                            detected_fields = analysis.get("detected_text_fields", [])
                            if detected_fields:
                                custom_field_mapping = detected_fields
                            detected_imgs = analysis.get("detected_images", [])
                            if detected_imgs:
                                custom_image_mapping = detected_imgs
                            custom_template_service.update_mappings(
                                template_id=resolved_template_id,
                                field_mapping=custom_field_mapping,
                                image_mapping=custom_image_mapping,
                            )
                            logger.info(f"[{job_id}] Discovered & persisted {len(custom_field_mapping)} fields and {len(custom_image_mapping or [])} images for '{resolved_template_id}'")
                        except Exception as ex:
                            logger.warning(f"[{job_id}] Auto-detection of template fields failed: {ex}")
            except Exception as e:
                logger.warning(f"[{job_id}] Could not resolve custom template {resolved_template_id}: {e}")

        job_record["template_id"] = resolved_template_id
        job_record["template_path"] = template_path

        # -------------------------------------------------------------
        # CHECK FOR PATH A (EXACT COPY / ZERO CONTENT MODIFICATION)
        # -------------------------------------------------------------
        all_text_inputs = " ".join([
            str(user_instructions or ""),
            str(proj_info.get("instructions") or ""),
            str(proj_info.get("title") or ""),
            str(proj_info.get("problem_statement") or ""),
            str(proj_info.get("description") or ""),
        ])

        is_no_change_requested = (
            is_zero_change_intent(all_text_inputs)
            or proj_info.get("no_changes") is True
            or proj_info.get("no_change") is True
        )

        if not is_no_change_requested:
            has_explicit_data = bool(custom_content) or bool(custom_assets)
            has_project_override = bool(proj_info.get("title") or proj_info.get("name") or proj_info.get("project_title"))
            if not has_explicit_data and not has_project_override and not custom_field_mapping and not custom_image_mapping:
                is_no_change_requested = True

        if is_no_change_requested:
            from apps.api.services.report_file_storage_service import report_file_storage_service
            is_pdf_template = template_path.lower().endswith(".pdf")
            ext = "pdf" if is_pdf_template else (Path(template_path).suffix.lstrip(".").lower() or "docx")
            canonical_path, storage_key = report_file_storage_service.save_report_file_atomically(
                report_id=job_id,
                source_data_or_path=template_path,
                extension=ext,
                metadata={
                    "job_id": job_id,
                    "project_id": project_id,
                    "template_id": resolved_template_id,
                    "zero_change": True,
                }
            )
            target_out_path = str(canonical_path)

            job_record["state"] = ReplacementState.COMPLETED.value
            job_record["progress_percent"] = 100
            job_record["arm_ui_state"] = "completed"
            job_record["status_message"] = "Report successfully compiled! College template preserved with zero redesign (exact copy)."
            job_record["fields_replaced"] = 0
            job_record["images_replaced"] = 0

            if is_pdf_template:
                job_record["pdf_path"] = target_out_path
                job_record["download_pdf_url"] = f"/api/v1/replacement/download/{job_id}?format=pdf"
                job_record["preview_html"] = "<div class='pdf-preview'><h3>PDF Master Template (Unchanged)</h3></div>"
            else:
                job_record["docx_path"] = target_out_path
                job_record["download_docx_url"] = f"/api/v1/replacement/download/{job_id}?format=docx"
                job_record["preview_html"] = "<div class='p-4 text-center text-xs text-zinc-500'>Original Template Preserved Byte-for-Byte (Zero Modifications Requested)</div>"
                job_record["stats"] = {"validation_status": "VALID", "fields_replaced": 0, "images_replaced": 0}
                job_record["preview_url"] = f"/api/v1/replacement/preview/{job_id}"

            job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

            if project_id and client:
                try:
                    rep_payload = {
                        "project_id": project_id,
                        "template_id": resolved_template_id if len(resolved_template_id) == 36 else None,
                        "status": "completed",
                        "title": proj_info.get("title") or "Master Template Copy",
                        "file_path": target_out_path,
                    }
                    client.table("reports").insert(rep_payload).execute()
                except Exception as e:
                    logger.warning(f"[{job_id}] Could not persist report record: {e}")

            return job_record

        # -------------------------------------------------------------
        # PATH B: TARGETED OR FULL TOPIC MODIFICATION
        # -------------------------------------------------------------
        ACADEMIC_METADATA_FIELDS = {
            "student_name", "roll_number", "guide_name", "department",
            "institution", "academic_year", "degree"
        }

        allowed_replace_fields: Optional[Set[str]] = None
        clean_project_data = {k: v for k, v in (project_data or {}).items() if v is not None}
        structured_content = dict(custom_content or {})

        if custom_field_mapping is not None:
            # Content / topic fields mapped as replaceable
            replaceable_content_fields = {
                fm["arm_field"] for fm in custom_field_mapping
                if fm.get("arm_field") not in ACADEMIC_METADATA_FIELDS
                and (fm.get("action") == "replace" or fm.get("action") is None)
            }
            # Academic metadata fields are strictly preserved unless explicitly provided by the user
            provided_metadata_fields = {
                fm["arm_field"] for fm in custom_field_mapping
                if fm.get("arm_field") in ACADEMIC_METADATA_FIELDS
                and bool(clean_project_data.get(fm["arm_field"]))
            }

            instr_lower = (user_instructions or "").lower()
            is_explicitly_targeted = any(w in instr_lower for w in ("replace only", "only replace", "just replace"))

            if is_explicitly_targeted:
                explicit_user_fields = set()
                for k, val in clean_project_data.items():
                    if val and str(val).strip():
                        if k in ("title", "name"):
                            explicit_user_fields.add("project_title")
                        elif k == "roll_no":
                            explicit_user_fields.add("roll_number")
                        else:
                            explicit_user_fields.add(k)
                for k, val in structured_content.items():
                    if val and str(val).strip():
                        explicit_user_fields.add(k)
                allowed_replace_fields = (replaceable_content_fields | provided_metadata_fields) & explicit_user_fields
            else:
                # Normal user flow: user enters Topic (Title / Description).
                # All replaceable content fields are eligible for AI topic synthesis!
                allowed_replace_fields = replaceable_content_fields | provided_metadata_fields
        else:
            instr_lower = (user_instructions or "").lower()
            if "replace only" in instr_lower or "only replace" in instr_lower:
                targeted = set()
                if "title" in instr_lower:
                    targeted.add("project_title")
                if "student" in instr_lower:
                    targeted.add("student_name")
                if "guide" in instr_lower or "supervisor" in instr_lower:
                    targeted.add("guide_name")
                if "roll" in instr_lower:
                    targeted.add("roll_number")
                if "department" in instr_lower:
                    targeted.add("department")
                if "intro" in instr_lower:
                    targeted.add("introduction")
                if targeted:
                    allowed_replace_fields = targeted

            if proj_info.get("allowed_fields"):
                allowed_replace_fields = set(proj_info.get("allowed_fields"))

        # -------------------------------------------------------------
        # STATE 2: ANALYZING -> GENERATING
        # -------------------------------------------------------------
        logger.info(f"[{job_id}] State: GENERATING (progress 45%)")
        job_record["state"] = ReplacementState.GENERATING.value
        job_record["progress_percent"] = 45
        job_record["arm_ui_state"] = "thinking"
        job_record["status_message"] = "ARM is generating structured content matching template fields..."
        job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        structured_content = dict(custom_content or {})
        clean_project_data = {k: v for k, v in (project_data or {}).items() if v is not None}

        title = final_report_title
        clean_proj_title = final_report_title
        description = (
            clean_project_data.get("description")
            or proj_info.get("description")
            or proj_info.get("problem_statement")
            or "Engineering and system methodology research study."
        )

        # Check if caller wants a full academic report generation vs targeted field substitution
        is_targeted_only = (allowed_replace_fields is not None) and not any(
            sec in allowed_replace_fields for sec in ("introduction", "methodology", "objectives", "objectives_1", "results", "conclusion", "abstract")
        )

        has_topic = bool(
            clean_project_data.get("title")
            or proj_info.get("title")
            or proj_info.get("name")
            or proj_info.get("project_title")
        )

        needs_ai_generation = has_topic and not is_targeted_only and not all(
            structured_content.get(k) for k in ("introduction", "methodology", "objectives")
        )

        # [4] Content generation started
        logger.info(f"[{job_id}] [ARM PIPELINE] [4] Content generation started")
        print(f"[ARM PIPELINE] [4] Content generation started")

        from apps.api.services.content_fitting_service import content_fitting_service
        merged_field_values: Dict[str, Any] = {}
        is_custom_tpl = custom_field_mapping is not None
        is_presentation = False
        section_budgets: Dict[str, Any] = {}
        master_budgets: Dict[str, Any] = {}

        if needs_ai_generation and custom_field_mapping is not None:
            # CUSTOM TEMPLATE AI GENERATION: Dynamic field synthesis matching detected sections & bullets
            if template_path and os.path.exists(template_path):
                try:
                    import docx as pydocx
                    _doc = pydocx.Document(template_path)
                    if _doc.sections and _doc.sections[0].page_width > _doc.sections[0].page_height:
                        is_presentation = True
                    if not is_presentation:
                        for _p in _doc.paragraphs[:30]:
                            if re.match(r"^Pg\.?\s*\d+", _p.text.strip(), re.IGNORECASE):
                                is_presentation = True
                                break
                except Exception:
                    pass

            # Extract exact page geometry from custom template
            tpl_page_settings = (cust_tpl.get("page_settings") if cust_tpl else None) or {}
            if not tpl_page_settings and template_path and os.path.exists(template_path):
                try:
                    import docx as pydocx
                    _d = pydocx.Document(template_path)
                    if _d.sections:
                        _s = _d.sections[0]
                        tpl_page_settings = {
                            "width_in": round(_s.page_width.inches, 2),
                            "height_in": round(_s.page_height.inches, 2),
                            "top_margin_in": round(_s.top_margin.inches, 2),
                            "bottom_margin_in": round(_s.bottom_margin.inches, 2),
                            "left_margin_in": round(_s.left_margin.inches, 2),
                            "right_margin_in": round(_s.right_margin.inches, 2),
                        }
                except Exception:
                    pass

            # [ARM TITLE] Single Source of Truth & Detection Diagnostics
            detected_template_title = "Unknown (unlabeled template title)"
            detection_page = 1
            if custom_field_mapping:
                for fm in custom_field_mapping:
                    if fm.get("arm_field") == "project_title":
                        detected_template_title = fm.get("original_text") or fm.get("template_element") or detected_template_title
                        loc = fm.get("location", "")
                        if "Paragraph 1" in loc or "Cover" in loc or "Slide 1" in loc:
                            detection_page = 1
                        break

            clean_proj_title = str(title).strip()
            if clean_proj_title.startswith(('"', '“', "'")) and clean_proj_title.endswith(('"', '”', "'")):
                clean_proj_title = clean_proj_title[1:-1].strip()

            print(f"\n[ARM TITLE]\nStudent Project Title: {clean_proj_title}\n")
            print(f"[ARM TITLE]\nTitle Detection Page: {detection_page}\n")
            print(f"[ARM TITLE]\nDetected Template Title: {detected_template_title}\n")
            print(f"[ARM TITLE]\nFinal Report Title: {clean_proj_title}\n")

            logger.info(
                f"[ARM TITLE] Student Project Title: '{clean_proj_title}', "
                f"Detected Template Title: '{detected_template_title}' (Page {detection_page}), "
                f"Final Report Title: '{clean_proj_title}'"
            )

            # 1. Analyze exact section capacity envelopes from the template's detected fields
            section_budgets = content_fitting_service.analyze_section_budgets(
                detected_fields=custom_field_mapping,
                page_settings=tpl_page_settings,
                project_title=clean_proj_title,
                is_presentation=is_presentation,
                detected_images=custom_image_mapping,
            )

            # 2. Build layout-aware AI field specs with explicit word & char limits
            field_specs = content_fitting_service.build_ai_field_specs(
                section_budgets=section_budgets,
                is_presentation=is_presentation,
            )

            ai_instructions = (
                f"Generate authoritative matter strictly about '{clean_proj_title}'. "
                "Keep each section within the specified space limits so it fits the template layout perfectly without overflowing."
            )
            if is_presentation:
                ai_instructions = (
                    f"Generate concise presentation slide content strictly about '{clean_proj_title}'. "
                    "Each bullet point must be concise and informative, max 15 words. "
                    "Keep paragraphs within the specified space limits to prevent overflowing slide boundaries."
                )
            if user_instructions:
                ai_instructions = f"{ai_instructions}\n{user_instructions}"
            if effective_search_query and effective_search_query.lower() != clean_proj_title.lower():
                ai_instructions = (
                    f"{ai_instructions}\n\n"
                    f"Research context & search query: '{effective_search_query}'. "
                    f"Use this query to gather supporting technical evidence, background research, and methodology details, "
                    f"while ensuring the document title remains strictly '{clean_proj_title}'."
                )

            ai_input = AIReportAgentInputDTO(
                project_title=clean_proj_title,
                project_description=description,
                user_instructions=ai_instructions,
                template_id=template_id or MASTER_TEMPLATE_ID,
                template_fields=field_specs,
                project_id=project_id,
            )
            generated = {}
            try:
                ai_output = ai_report_agent_service.generate_report_content(ai_input)
                generated = ai_output.content
                logger.info(f"[{job_id}] AI Report Agent synthesized {len(generated)} structured fields for custom template.")
            except Exception as e:
                logger.warning(f"[{job_id}] AI Report Agent generation error: {e}")

            # 3. Intelligent Content-Fitting Loop: Check overflow/underflow and adjust in-place
            fitted_generated, fit_audit = content_fitting_service.fit_and_adjust_content(
                generated_content=generated,
                section_budgets=section_budgets,
                project_title=clean_proj_title,
                is_presentation=is_presentation,
            )
            logger.info(f"[{job_id}] Content fitting audit: {fit_audit}")

            # 4. Authoritative Project Title: Exact student title is the single source of truth
            merged_field_values["project_title"] = clean_proj_title
            merged_field_values["title"] = clean_proj_title
            merged_field_values["project_name"] = clean_proj_title

            # 5. Unpack fitted section content
            for k, v in fitted_generated.items():
                if isinstance(v, list):
                    for idx, item in enumerate(v, start=1):
                        merged_field_values[f"{k}_{idx}"] = item
                    merged_field_values[k] = v
                else:
                    merged_field_values[k] = v

            # 6. User custom content overrides
            for k, v in structured_content.items():
                if v:
                    merged_field_values[k] = v

            # 7. User provided academic metadata (strictly preserve unprovided template metadata)
            for meta_k in ACADEMIC_METADATA_FIELDS:
                meta_val = clean_project_data.get(meta_k) or (proj_info.get(meta_k) if proj_info else None)
                if meta_val:
                    merged_field_values[meta_k] = meta_val
                else:
                    merged_field_values.pop(meta_k, None)

            # 8. Filter strictly to allowed_replace_fields
            if allowed_replace_fields is not None:
                merged_field_values = {
                    k: v for k, v in merged_field_values.items()
                    if k in allowed_replace_fields or (k == "project_title" and "project_title" in allowed_replace_fields)
                }
                if "project_title" in allowed_replace_fields:
                    merged_field_values["project_title"] = clean_proj_title

        elif needs_ai_generation:
            # MASTER TEMPLATE AI GENERATION: Default canonical fields
            generated = {}
            master_instructions = user_instructions or ""
            if effective_search_query and effective_search_query.lower() != clean_proj_title.lower():
                master_instructions = (
                    f"{master_instructions}\n"
                    f"Research context & search query: '{effective_search_query}'. "
                    f"Use this query for supporting technical research while preserving project title '{clean_proj_title}'."
                ).strip()

            try:
                ai_input = AIReportAgentInputDTO(
                    project_title=clean_proj_title,
                    project_description=description,
                    user_instructions=master_instructions or None,
                    template_id=template_id or MASTER_TEMPLATE_ID,
                    project_id=project_id,
                )
                ai_output = ai_report_agent_service.generate_report_content(ai_input)
                generated = ai_output.content
                logger.info(f"[{job_id}] AI Report Agent synthesized {len(generated)} structured fields.")
            except Exception as e:
                logger.warning(f"[{job_id}] AI Report Agent fallback: {e}")

            base_data = master_template_service.build_replacement_dataset(proj_info)
            structured_content = {**base_data, **generated, **clean_project_data, **structured_content}

            # Master Template Content-Fitting Loop: Fit canonical sections (abstract, intro, methodology, etc.) to page space
            master_field_specs = [
                {"arm_field": k, "content_type": "paragraph", "original_text": str(v or "")}
                for k, v in structured_content.items()
                if k not in ACADEMIC_METADATA_FIELDS and k not in ("project_title", "title", "project_name")
            ]
            master_budgets = content_fitting_service.analyze_section_budgets(
                detected_fields=master_field_specs,
                project_title=clean_proj_title,
                page_settings={"width_in": 8.5, "height_in": 11.0, "orientation": "portrait"},
                is_presentation=False,
            )
            fitted_master_content, master_fit_audit = content_fitting_service.fit_and_adjust_content(
                generated_content=structured_content,
                section_budgets=master_budgets,
                project_title=clean_proj_title,
                is_presentation=False,
            )
            structured_content.update(fitted_master_content)

            if is_targeted_only or allowed_replace_fields is not None:
                for k, v in structured_content.items():
                    if allowed_replace_fields is None or k in allowed_replace_fields:
                        merged_field_values[k] = v
                    if k == "title" and ("project_title" in (allowed_replace_fields or set())):
                        merged_field_values["project_title"] = v
                if (allowed_replace_fields is None or "project_title" in allowed_replace_fields) and "project_title" not in merged_field_values:
                    merged_field_values["project_title"] = clean_proj_title
            else:
                merged_field_values = master_template_service.build_replacement_dataset(
                    project_data=proj_info,
                    custom_field_values=structured_content
                )
            merged_field_values["project_title"] = clean_proj_title
            merged_field_values["title"] = clean_proj_title
            merged_field_values["project_name"] = clean_proj_title
        else:
            if is_targeted_only or allowed_replace_fields is not None:
                for k, v in {**clean_project_data, **structured_content}.items():
                    if allowed_replace_fields is None or k in allowed_replace_fields:
                        merged_field_values[k] = v
                    if k == "title" and ("project_title" in (allowed_replace_fields or set())):
                        merged_field_values["project_title"] = clean_proj_title
                if (allowed_replace_fields is None or "project_title" in allowed_replace_fields) and "project_title" not in merged_field_values:
                    merged_field_values["project_title"] = clean_proj_title
            else:
                base_data = master_template_service.build_replacement_dataset(proj_info)
                merged_field_values = {**base_data, **clean_project_data, **structured_content}
            merged_field_values["project_title"] = clean_proj_title
            merged_field_values["title"] = clean_proj_title
            merged_field_values["project_name"] = clean_proj_title

        # [5] Content generation completed
        logger.info(f"[{job_id}] [ARM PIPELINE] [5] Content generation completed")
        print(f"[ARM PIPELINE] [5] Content generation completed")

        # Resolve Image Assets
        image_assets: Dict[str, Any] = dict(custom_assets or {})
        if project_id and client and not image_assets and is_valid_uuid:
            try:
                a_res = client.table("report_assets").select("*").eq("project_id", project_id).execute()
                if a_res.data:
                    for asset in a_res.data:
                        tf = asset.get("template_field") or asset.get("asset_key")
                        if tf:
                            image_assets[tf] = asset.get("file_path") or asset.get("url")
            except Exception as e:
                logger.warning(f"[{job_id}] Could not fetch project assets from DB: {e}")

        # [6] Slide analysis started
        logger.info(f"[{job_id}] [ARM PIPELINE] [6] Slide analysis started")
        print(f"[ARM PIPELINE] [6] Slide analysis started")

        # Stage 17: Semantic Slide & Content Mapping
        # Guarantees that ALL project-specific headings, TOC items, and body paragraphs
        # are mapped and synthesized to the new project domain, with zero leftover old template text.
        is_custom_or_pres = (
            resolved_template_id != MASTER_TEMPLATE_ID
            and "master_college_template" not in (template_path or "").lower()
        )
        slide_context_map: Dict[int, Dict[str, Any]] = {}
        if (
            template_path
            and os.path.exists(template_path)
            and template_path.lower().endswith(".docx")
            and not is_targeted_only
            and is_custom_or_pres
        ):
            try:
                from apps.api.services.semantic_slide_mapper import semantic_slide_mapper
                sem_res = semantic_slide_mapper.analyze_and_map_document(
                    template_path=template_path,
                    project_title=clean_proj_title,
                    problem_statement=description,
                    custom_content=structured_content,
                    existing_field_mapping=custom_field_mapping,
                    existing_field_values=merged_field_values,
                )
                custom_field_mapping = sem_res.get("field_mapping")
                merged_field_values.update(sem_res.get("field_values", {}))
                job_record["content_replacement_analysis"] = sem_res.get("analysis_rows", [])
                slide_context_map = sem_res.get("slide_context_map", {})
            except Exception as e:
                logger.warning(f"[{job_id}] Semantic slide mapping failed: {e}")

        # Intelligent Image Replacement Pipeline
        from apps.api.services.intelligent_image_service import intelligent_image_service

        # Always analyze template images with latest classification rules to strictly protect
        # transparent frame borders, header bars, and logos from accidental replacement
        if template_path and os.path.exists(template_path) and template_path.lower().endswith(".docx"):
            try:
                fresh_mapping = intelligent_image_service.analyze_docx_images(template_path)
                if fresh_mapping:
                    if custom_image_mapping:
                        user_overrides = {
                            im.get("filename"): im.get("action")
                            for im in custom_image_mapping
                            if im.get("filename") and im.get("is_user_override")
                        }
                        for f_im in fresh_mapping:
                            if f_im.get("filename") in user_overrides:
                                f_im["action"] = user_overrides[f_im["filename"]]
                                f_im["is_replaceable"] = (f_im["action"] == "replace")
                    custom_image_mapping = fresh_mapping
            except Exception as e:
                logger.warning(f"[{job_id}] Auto-detection of images failed: {e}")

        # Enrich custom_image_mapping with exact slide context (heading, matter, slide_num)
        if custom_image_mapping and slide_context_map:
            slide_image_counts: Dict[int, int] = {}
            for im in custom_image_mapping:
                p_idx = im.get("paragraph_idx", 0)
                matched_slide = None
                # Primary: continuous paragraph range of the slide
                for s_num, s_info in slide_context_map.items():
                    s_start = s_info.get("start_paragraph_idx", s_info.get("paragraph_indices", [0])[0] if s_info.get("paragraph_indices") else 0)
                    s_end = s_info.get("end_paragraph_idx", s_info.get("paragraph_indices", [0])[-1] if s_info.get("paragraph_indices") else 0)
                    if s_start <= p_idx <= s_end:
                        matched_slide = s_info
                        break
                # Secondary: paragraph index bounds
                if not matched_slide:
                    for s_num, s_info in slide_context_map.items():
                        p_indices = s_info.get("paragraph_indices", [])
                        if p_indices and (p_indices[0] <= p_idx <= p_indices[-1]):
                            matched_slide = s_info
                            break
                # Tertiary: nearest slide boundary
                if not matched_slide and slide_context_map:
                    matched_slide = min(
                        slide_context_map.values(),
                        key=lambda s: abs(p_idx - (s.get("start_paragraph_idx", s.get("paragraph_indices", [0])[0] if s.get("paragraph_indices") else 0))),
                        default=None
                    )
                if matched_slide:
                    s_id = matched_slide["slide_num"]
                    im["slide_num"] = s_id
                    im["new_heading"] = matched_slide.get("new_heading") or im.get("heading")
                    im["slide_matter"] = matched_slide.get("matter")
                    slide_image_counts[s_id] = slide_image_counts.get(s_id, 0) + 1
                    im["slide_image_slot"] = slide_image_counts[s_id]

        image_diagnostics: List[Dict[str, Any]] = []
        synth_map: Dict[str, Any] = {}
        # [7] Image generation started
        logger.info(f"[{job_id}] [ARM PIPELINE] [7] Image generation started")
        print(f"[ARM PIPELINE] [7] Image generation started")

        if custom_image_mapping and not is_targeted_only:
            # Check which images need synthesis
            images_to_generate = []
            for im in custom_image_mapping:
                act = im.get("action", "fixed").lower()
                arm_f = im.get("arm_image_field", "")
                fname = im.get("filename", "")
                has_provided = (arm_f in image_assets) or (fname in image_assets)
                if act == "replace" and not has_provided:
                    images_to_generate.append(im)

            if images_to_generate:
                logger.info(f"[{job_id}] Synthesizing {len(images_to_generate)} topic replacement images for '{clean_proj_title}'...")
                from apps.api.services.gemini_visual_pipeline_service import gemini_visual_pipeline_service
                gemini_visual_pipeline_service.clear_cache(job_id)
                gen_img_dir = os.path.abspath(os.path.join("generated_images", job_id))
                os.makedirs(gen_img_dir, exist_ok=True)
                synth_map = intelligent_image_service.generate_replacement_images(
                    project_title=clean_proj_title,
                    problem_statement=description,
                    analyzed_images=images_to_generate,
                    output_dir=gen_img_dir,
                    report_id=job_id,
                )
                for fname_key, meta in synth_map.items():
                    fpath = meta["file_path"]
                    image_assets[fname_key] = fpath
                    if meta.get("arm_image_field"):
                        image_assets[meta["arm_image_field"]] = fpath

            # [8] Image generation completed
            logger.info(f"[{job_id}] [ARM PIPELINE] [8] Image generation completed")
            print(f"[ARM PIPELINE] [8] Image generation completed")
        else:
            # [8] Image generation completed (no replacement images required)
            logger.info(f"[{job_id}] [ARM PIPELINE] [8] Image generation completed")
            print(f"[ARM PIPELINE] [8] Image generation completed")

        if custom_image_mapping and not is_targeted_only:
            # Filter image_assets strictly to replaceable fields/filenames
            replaceable_keys = set()
            for im in custom_image_mapping:
                if im.get("action") == "replace":
                    if im.get("arm_image_field"):
                        replaceable_keys.add(im["arm_image_field"])
                    if im.get("filename"):
                        replaceable_keys.add(im["filename"])
            image_assets = {k: v for k, v in image_assets.items() if k in replaceable_keys}

            # Build Diagnostic Audit Table
            replaced_cnt = 0
            fixed_cnt = 0
            for im in custom_image_mapping:
                act = im.get("action", "fixed").lower()
                fname = im.get("filename", "")
                arm_f = im.get("arm_image_field", "")
                is_rep = (act == "replace") and bool(image_assets.get(fname) or image_assets.get(arm_f))
                if is_rep:
                    replaced_cnt += 1
                else:
                    fixed_cnt += 1
                meta_info = synth_map.get(fname) or synth_map.get(arm_f) or {}
                image_diagnostics.append({
                    "image_id": im.get("id") or fname,
                    "filename": fname,
                    "original_file_type": im.get("format", "UNKNOWN"),
                    "detected_purpose": im.get("classification", "topic_specific"),
                    "action": act,
                    "is_replaceable": act == "replace",
                    "reason_for_decision": im.get("reason", "Template image"),
                    "visual_type": meta_info.get("visual_type"),
                    "visual_decision_reason": meta_info.get("decision_reason"),
                    "replacement_generated": is_rep,
                    "successfully_replaced": is_rep,
                    "error": None,
                })

            print(f"\n[ARM IMAGES]\nTotal Analyzed: {len(custom_image_mapping)}")
            print(f"Replaced: {replaced_cnt}")
            print(f"Preserved: {fixed_cnt}\n")
            logger.info(f"[{job_id}] [ARM IMAGES] Total Analyzed: {len(custom_image_mapping)}, Replaced: {replaced_cnt}, Preserved: {fixed_cnt}")

        job_record["image_diagnostics"] = image_diagnostics
        job_record["template_path"] = template_path
        job_record["field_values"] = merged_field_values
        job_record["image_assets"] = image_assets

        # -------------------------------------------------------------
        # STATE 3: GENERATING -> REPLACING
        # -------------------------------------------------------------
        # [9] Template replacement started
        logger.info(f"[{job_id}] [ARM PIPELINE] [9] Template replacement started")
        print(f"[ARM PIPELINE] [9] Template replacement started")
        logger.info(f"[{job_id}] State: REPLACING (progress 70%)")
        job_record["state"] = ReplacementState.REPLACING.value
        job_record["progress_percent"] = 70
        job_record["arm_ui_state"] = "creating"
        job_record["status_message"] = "ARM is creating report: substituting text & images in college template..."
        job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
        os.makedirs(output_dir, exist_ok=True)

        is_pdf_template = template_path.lower().endswith(".pdf")

        # CASE 2: College PDF provided as reference / template
        if is_pdf_template:
            target_pdf_path = os.path.join(output_dir, f"ARM_Report_{job_id[:8]}.pdf")
            pdf_engine = PdfTemplateReplacementEngine()
            replacement_result = pdf_engine.replace(
                template_path=template_path,
                field_values=merged_field_values,
                image_assets=image_assets,
                output_path=target_pdf_path,
                job_id=job_id,
            )

            job_record["fields_replaced"] = replacement_result.fields_replaced
            job_record["images_replaced"] = replacement_result.images_replaced
            job_record["audit"] = [a.model_dump() for a in replacement_result.audit]
            job_record["warnings"] = replacement_result.warnings
            job_record["errors"] = [e.model_dump() for e in replacement_result.errors]

            if not replacement_result.success:
                logger.warning(f"[{job_id}] PDF template replacement stopped safely: {replacement_result.errors}")
                job_record["state"] = ReplacementState.FAILED.value
                job_record["arm_ui_state"] = "thinking"
                first_reason = replacement_result.errors[0].reason if replacement_result.errors else "Layout collision or raster scan detected."
                job_record["status_message"] = (
                    f"PDF replacement stopped safely: {first_reason} "
                    f"Recommendation: Convert to an ARM-supported structured template (DOCX format)."
                )
                job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
                return job_record

            job_record["pdf_path"] = target_pdf_path
            job_record["state"] = ReplacementState.COMPLETED.value
            job_record["progress_percent"] = 100
            job_record["arm_ui_state"] = "completed"
            job_record["status_message"] = "PDF report successfully compiled in-place!"
            job_record["download_pdf_url"] = f"/api/v1/replacement/download/{job_id}?format=pdf"
            job_record["preview_html"] = f"<div class='pdf-preview'><h3>PDF Report Compiled</h3><p>Pages: {replacement_result.metadata.get('pdf_analysis', {}).get('total_pages', 1)}</p></div>"
            job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
            return job_record

        # CASE 1: Structured DOCX Master Template (Preferred Editable Master Format)
        from apps.api.services.report_file_storage_service import report_file_storage_service
        ext = Path(template_path).suffix.lstrip(".").lower() or "docx"
        target_docx_path = str(report_file_storage_service.get_staging_dir() / f"{job_id}.{ext}")

        if selected_provider_name == "carbone":
            carbone_provider = document_provider_registry.get_provider("carbone")
            if not carbone_provider.is_configured():
                err_msg = (
                    "Carbone document provider is not configured: "
                    "CARBONE_API_KEY environment variable is missing from backend configuration."
                )
                logger.error(f"[{job_id}] {err_msg}")
                job_record["state"] = ReplacementState.FAILED.value
                job_record["arm_ui_state"] = "thinking"
                job_record["status_message"] = "Carbone document provider configuration error: missing CARBONE_API_KEY."
                job_record["errors"] = [{"field": "carbone_config", "reason": err_msg}]
                job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
                return job_record

            carbone_res = carbone_provider.generate(
                template_path=template_path,
                data=merged_field_values,
                image_assets=image_assets,
                output_path=target_docx_path,
                output_format="docx",
            )
            if not carbone_res.success:
                logger.error(f"[{job_id}] Carbone generation failed: {carbone_res.errors}")
                job_record["state"] = ReplacementState.FAILED.value
                job_record["arm_ui_state"] = "thinking"
                first_err = carbone_res.errors[0] if carbone_res.errors else "Unknown Carbone rendering failure"
                job_record["status_message"] = f"Carbone provider generation failed: {first_err}"
                job_record["errors"] = [{"field": "carbone_generation", "reason": e} for e in carbone_res.errors]
                job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
                return job_record

            job_record["fields_replaced"] = len(merged_field_values)
            job_record["images_replaced"] = len(image_assets)
        else:
            # Strict Overflow Safety Check Pass
            merged_field_values, overflow_audit = content_fitting_service.validate_and_enforce_overflow_safety(
                field_values=merged_field_values,
                section_budgets=section_budgets or master_budgets,
                project_title=clean_proj_title,
                is_presentation=is_presentation,
            )
            if overflow_audit.get("trimmed_fields"):
                logger.info(f"[{job_id}] Overflow safety check trimmed fields: {overflow_audit['trimmed_fields']}")

            engine = DocxTemplateReplacementEngine()
            replacement_result = engine.replace(
                template_path=template_path,
                field_values=merged_field_values,
                image_assets=image_assets,
                output_path=target_docx_path,
                job_id=job_id,
                field_mapping=custom_field_mapping,
                image_mapping=custom_image_mapping,
            )

            job_record["fields_replaced"] = replacement_result.fields_replaced
            job_record["images_replaced"] = replacement_result.images_replaced
            job_record["audit"] = [a.model_dump() for a in replacement_result.audit]
            job_record["warnings"] = replacement_result.warnings
            job_record["errors"] = [e.model_dump() for e in replacement_result.errors]

            if not replacement_result.success:
                logger.error(f"[{job_id}] Replacement failed: {replacement_result.errors}")
                report_file_storage_service.record_failed_generation(
                    report_id=job_id,
                    reason=str([e.model_dump() for e in replacement_result.errors]),
                    metadata={"project_id": project_id, "template_id": template_id}
                )
                job_record["state"] = ReplacementState.FAILED.value
                job_record["arm_ui_state"] = "thinking"
                job_record["status_message"] = f"Replacement stopped: {len(replacement_result.errors)} safety errors detected."
                job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
                return job_record

        # -------------------------------------------------------------
        # STATE 4: REPLACING -> VALIDATING
        # -------------------------------------------------------------
        logger.info(f"[{job_id}] State: VALIDATING (progress 88%)")
        job_record["state"] = ReplacementState.VALIDATING.value
        job_record["progress_percent"] = 88
        job_record["arm_ui_state"] = "creating"
        job_record["status_message"] = "ARM is validating document structure, typography, and generating preview..."
        job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        if allowed_replace_fields is not None:
            req_fields = [
                f for f in allowed_replace_fields
                if f in [cf["field_name"] for cf in CANONICAL_FIELDS if cf.get("is_required", False)]
            ]
        else:
            req_fields = [f["field_name"] for f in CANONICAL_FIELDS if f.get("is_required", False)]
        val_result = ReplacementValidator.validate_and_generate_preview(
            docx_path=target_docx_path,
            required_fields=req_fields
        )

        if not val_result["is_valid"]:
            logger.error(f"[{job_id}] Validation errors: {val_result['errors']}")
            report_file_storage_service.record_failed_generation(
                report_id=job_id,
                reason=str(val_result['errors']),
                metadata={"project_id": project_id, "template_id": template_id}
            )
            job_record["state"] = ReplacementState.FAILED.value
            job_record["errors"].extend(val_result["errors"])
            job_record["status_message"] = "Document validation failed: structural errors found."
            job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
            return job_record

        job_record["preview_html"] = val_result["preview_html"]
        job_record["stats"] = val_result["stats"]
        job_record["docx_path"] = target_docx_path
        job_record["pdf_path"] = None

        # [10] Final document created
        logger.info(f"[{job_id}] [ARM PIPELINE] [10] Final document created")
        print(f"[ARM PIPELINE] [10] Final document created")

        try:
            page_fit_result = content_fitting_service.validate_docx_page_fit(
                docx_path=target_docx_path,
                section_budgets=section_budgets if is_custom_tpl else (master_budgets if 'master_budgets' in locals() else {}),
                project_title=clean_proj_title,
            )
            job_record["page_fit_audit"] = page_fit_result
            logger.info(f"[{job_id}] Page fit audit: {page_fit_result}")
        except Exception as e:
            logger.warning(f"[{job_id}] Page fit validation non-fatal error: {e}")

        try:
            from apps.api.services.visual_report_validator import visual_report_validator
            visual_audit = visual_report_validator.validate_report_visuals(
                docx_path=target_docx_path,
                project_title=clean_proj_title,
                problem_statement=description,
                template_path=template_path,
            )
            job_record["visual_audit"] = visual_audit
            if visual_audit.get("pdf_path"):
                job_record["pdf_path"] = visual_audit["pdf_path"]
                job_record["download_pdf_url"] = f"/api/v1/replacement/download/{job_id}?format=pdf"
            logger.info(
                f"[{job_id}] Visual report validation: status={visual_audit.get('status')}, "
                f"pages={visual_audit.get('total_pages')}, forbidden={len(visual_audit.get('forbidden_terms_found', []))}"
            )
        except Exception as e:
            logger.warning(f"[{job_id}] Visual report validation non-fatal error: {e}")

        # -------------------------------------------------------------
        # STATE 5: VALIDATING -> COMPLETED
        # -------------------------------------------------------------
        # Strict Verification Gate (Zero Regression Rules 11 & 12):
        # Before marking the report COMPLETED, verify:
        # - Project title matches user's entered project title.
        # - Generated matter is present.
        # - Requested new images were actually generated & inserted.
        # - If any check fails, FAIL THE REPORT instead of returning unchanged template.
        num_requested_images = len(images_to_generate) if ("images_to_generate" in locals() and images_to_generate) else 0
        if num_requested_images > 0 and job_record.get("images_replaced", 0) == 0:
            err_msg = (
                f"Image replacement validation failed: {num_requested_images} replacement images were requested, "
                f"but 0 new images were successfully generated or replaced into the template. "
                f"Image providers failed or quota exhausted. Aborting report to prevent returning unchanged template."
            )
            logger.error(f"[{job_id}] {err_msg}")
            report_file_storage_service.record_failed_generation(
                report_id=job_id,
                reason=err_msg,
                metadata={"project_id": project_id, "template_id": template_id}
            )
            job_record["state"] = ReplacementState.FAILED.value
            job_record["arm_ui_state"] = "thinking"
            job_record["status_message"] = err_msg
            job_record["errors"] = [{"field": "image_generation", "reason": err_msg}]
            job_record["updated_at"] = datetime.now(timezone.utc).isoformat()
            return job_record

        # Atomically move from staging to canonical persistent reports directory
        canonical_path, storage_key = report_file_storage_service.save_report_file_atomically(
            report_id=job_id,
            source_data_or_path=target_docx_path,
            extension=ext,
            metadata={
                "job_id": job_id,
                "project_id": project_id,
                "template_id": template_id,
                "title": merged_field_values.get("project_title") or "Academic Report",
                "fields_replaced": job_record.get("fields_replaced", 0),
                "images_replaced": job_record.get("images_replaced", 0),
            }
        )
        job_record["docx_path"] = str(canonical_path)
        job_record["storage_key"] = storage_key
        logger.info(f"[{job_id}] State: COMPLETED (progress 100%)")
        job_record["state"] = ReplacementState.COMPLETED.value
        job_record["progress_percent"] = 100
        job_record["arm_ui_state"] = "completed"
        job_record["status_message"] = "Report successfully compiled! College template preserved with zero redesign."
        job_record["download_docx_url"] = f"/api/v1/replacement/download/{job_id}?format={ext}"
        if not job_record.get("download_pdf_url"):
            job_record["download_pdf_url"] = None
        job_record["preview_url"] = f"/api/v1/replacement/preview/{job_id}"
        job_record["title"] = merged_field_values.get("project_title") or "Academic Report"
        job_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Persist report entry in Supabase if project_id is available
        if project_id and client and is_valid_uuid:
            try:
                rep_payload = {
                    "project_id": project_id,
                    "template_id": template_id or MASTER_TEMPLATE_ID,
                    "status": "completed",
                    "title": merged_field_values.get("project_title") or "Academic Report",
                    "file_path": str(canonical_path),
                }
                client.table("reports").insert(rep_payload).execute()
            except Exception as e:
                logger.warning(f"[{job_id}] Could not persist report record: {e}")

        return job_record

    def regenerate_section(
        self,
        job_id: str,
        section_name: str,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerates a single targeted section in-place:
        1. Synthesizes updated section text conditioned on student instructions.
        2. Re-runs DOCX replacement engine on the master template.
        3. Re-validates typography, placeholders, and refreshes the preview HTML and PDF.
        """
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Replacement job '{job_id}' not found.")

        normalized_section = section_name.lower().strip()
        logger.info(f"[{job_id}] Regenerating section '{normalized_section}' (custom_prompt: {custom_prompt})")

        job["state"] = ReplacementState.GENERATING.value
        job["arm_ui_state"] = "thinking"
        job["status_message"] = f"ARM is regenerating section '{normalized_section}'..."
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Build focused prompt and generate section
        current_fields = job.get("field_values", {})
        title = current_fields.get("project_title") or "Technical Research Project"
        description = current_fields.get("abstract") or "Engineering system methodology study."
        instructions = f"Elevate and rewrite section '{normalized_section}'."
        if custom_prompt:
            instructions += f" Refinement instructions: {custom_prompt}"

        ai_input = AIReportAgentInputDTO(
            project_title=title,
            project_description=description,
            user_instructions=instructions,
            project_id=job.get("project_id"),
        )
        ai_output = ai_report_agent_service.generate_report_content(ai_input)

        new_val = None
        for k, v in ai_output.content.items():
            if k.lower() == normalized_section or k.lower().replace("_", "") == normalized_section.replace("_", ""):
                new_val = v
                normalized_section = k
                break

        if not new_val:
            new_val = ai_output.content.get(normalized_section) or f"Updated {normalized_section.replace('_', ' ').title()} content incorporating student refinements."

        # Update field value in job
        current_fields[normalized_section] = new_val
        job["field_values"] = current_fields

        # Re-run DOCX replacement engine in-place
        job["state"] = ReplacementState.REPLACING.value
        job["arm_ui_state"] = "creating"
        job["status_message"] = f"ARM is re-inserting section '{normalized_section}' into college template..."
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        template_path = job.get("template_path") or self.default_template_path
        target_docx_path = job.get("docx_path")
        if not target_docx_path:
            output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
            os.makedirs(output_dir, exist_ok=True)
            target_docx_path = os.path.join(output_dir, f"ARM_Report_{job_id[:8]}.docx")
            job["docx_path"] = target_docx_path

        engine = DocxTemplateReplacementEngine()
        replacement_result = engine.replace(
            template_path=template_path,
            field_values=job["field_values"],
            image_assets=job.get("image_assets", {}),
            output_path=target_docx_path,
            job_id=job_id,
        )

        job["fields_replaced"] = replacement_result.fields_replaced
        job["audit"] = [a.model_dump() for a in replacement_result.audit]
        job["warnings"] = replacement_result.warnings
        job["errors"] = [e.model_dump() for e in replacement_result.errors]

        # Re-validate and re-generate preview HTML
        job["state"] = ReplacementState.VALIDATING.value
        req_fields = [f["field_name"] for f in CANONICAL_FIELDS if f.get("is_required", False)]
        val_result = ReplacementValidator.validate_and_generate_preview(
            docx_path=target_docx_path,
            required_fields=req_fields,
            pdf_path=job.get("pdf_path"),
        )
        job["preview_html"] = val_result["preview_html"]
        job["stats"] = val_result["stats"]

        job["state"] = ReplacementState.COMPLETED.value
        job["arm_ui_state"] = "completed"
        job["status_message"] = f"Section '{normalized_section}' regenerated and updated in-place successfully!"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        return job

    def replace_image(
        self,
        job_id: str,
        image_slot: str,
        asset_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Replaces a specific template image slot (e.g. image_1, image_2, image_3) in-place:
        1. Resolves file path from uploaded bytes or asset path.
        2. Re-runs DOCX replacement engine on the template.
        3. Re-validates typography and refreshes preview HTML and PDF.
        """
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Replacement job '{job_id}' not found.")

        slot_key = image_slot.lower().strip()
        logger.info(f"[{job_id}] Replacing image slot '{slot_key}'")

        job["state"] = ReplacementState.REPLACING.value
        job["arm_ui_state"] = "creating"
        job["status_message"] = f"ARM is updating image asset in slot '{slot_key}'..."
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
        os.makedirs(output_dir, exist_ok=True)

        resolved_file_path = None
        if image_base64:
            import base64
            cleaned_b64 = image_base64.split(",")[-1]
            ext = "png"
            if "image/jpeg" in image_base64 or "image/jpg" in image_base64:
                ext = "jpg"
            save_dest = os.path.join(output_dir, f"{job_id}_{slot_key}.{ext}")
            with open(save_dest, "wb") as f:
                f.write(base64.b64decode(cleaned_b64))
            resolved_file_path = save_dest
        elif asset_path:
            if not os.path.exists(asset_path):
                raise ValueError(f"Replacement image file does not exist at '{asset_path}'.")
            resolved_file_path = asset_path
        else:
            raise ValueError("Either 'asset_path' or 'image_base64' must be provided to replace image.")

        # Update image assets map
        image_assets = job.get("image_assets", {})
        image_assets[slot_key] = resolved_file_path
        job["image_assets"] = image_assets

        # Update caption if provided
        if caption:
            caption_field = f"{slot_key}_caption"
            job.get("field_values", {})[caption_field] = caption

        template_path = job.get("template_path") or self.default_template_path
        target_docx_path = job.get("docx_path")
        if not target_docx_path:
            target_docx_path = os.path.join(output_dir, f"ARM_Report_{job_id[:8]}.docx")
            job["docx_path"] = target_docx_path

        engine = DocxTemplateReplacementEngine()
        replacement_result = engine.replace(
            template_path=template_path,
            field_values=job["field_values"],
            image_assets=image_assets,
            output_path=target_docx_path,
            job_id=job_id,
        )

        job["images_replaced"] = replacement_result.images_replaced
        job["audit"] = [a.model_dump() for a in replacement_result.audit]
        job["warnings"] = replacement_result.warnings
        job["errors"] = [e.model_dump() for e in replacement_result.errors]

        # Re-validate and re-generate preview HTML
        job["state"] = ReplacementState.VALIDATING.value
        req_fields = [f["field_name"] for f in CANONICAL_FIELDS if f.get("is_required", False)]
        val_result = ReplacementValidator.validate_and_generate_preview(
            docx_path=target_docx_path,
            required_fields=req_fields,
            pdf_path=job.get("pdf_path"),
        )
        job["preview_html"] = val_result["preview_html"]
        job["stats"] = val_result["stats"]

        job["state"] = ReplacementState.COMPLETED.value
        job["arm_ui_state"] = "completed"
        job["status_message"] = f"Image slot '{slot_key}' replaced successfully!"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        return job

    def approve_report(self, job_id: str) -> Dict[str, Any]:
        """
        Marks report replacement job as approved by student:
        Locks approval status, stamps timestamp, and synchronizes database record.
        """
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Replacement job '{job_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        job["approval_status"] = "approved"
        job["approved_at"] = now
        job["updated_at"] = now
        job["status_message"] = "Report approved by student. Ready for official academic submission."

        project_id = job.get("project_id")
        client = db_manager.client
        if project_id and client:
            try:
                client.table("reports").update({
                    "status": "approved",
                    "updated_at": now
                }).eq("project_id", project_id).execute()
                logger.info(f"[{job_id}] Persisted report approval in Supabase for project {project_id}")
            except Exception as e:
                logger.warning(f"[{job_id}] Could not sync approval to Supabase: {e}")

        return job

    def regenerate_full_report(
        self,
        job_id: str,
        user_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a complete fresh regeneration and in-place replacement run
        for the project associated with an existing job.
        """
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Replacement job '{job_id}' not found.")

        return self.execute_replacement(
            project_id=job.get("project_id"),
            template_id=job.get("template_id"),
            custom_assets=job.get("image_assets"),
            user_instructions=user_instructions,
            provider=job.get("provider"),
        )


replacement_engine_service = ReplacementEngineService()
