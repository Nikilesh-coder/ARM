"""
ARM - Master College Template Service
Manages the fixed college template specification, reusable fields,
and automated content/image replacement mapping.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager

logger = get_logger("master_template.service")

MASTER_TEMPLATE_ID = "00000000-0000-0000-0000-000000000001"

CANONICAL_FIELDS = [
    {
        "field_name": "project_title",
        "field_label": "Project Title",
        "field_type": "text",
        "page_or_section": "Cover Page",
        "is_required": True,
        "placeholder_identifier": "{{PROJECT_TITLE}}",
        "content_limits": {"min_length": 5, "max_length": 150},
        "ordering": 1,
    },
    {
        "field_name": "student_name",
        "field_label": "Student Scholar Name",
        "field_type": "text",
        "page_or_section": "Cover Page",
        "is_required": True,
        "placeholder_identifier": "{{STUDENT_NAME}}",
        "content_limits": {"min_length": 2, "max_length": 80},
        "ordering": 2,
    },
    {
        "field_name": "roll_number",
        "field_label": "University Roll / Registration Number",
        "field_type": "text",
        "page_or_section": "Cover Page",
        "is_required": True,
        "placeholder_identifier": "{{ROLL_NUMBER}}",
        "content_limits": {"min_length": 4, "max_length": 30},
        "ordering": 3,
    },
    {
        "field_name": "department",
        "field_label": "Academic Department",
        "field_type": "text",
        "page_or_section": "Cover Page",
        "is_required": True,
        "placeholder_identifier": "{{DEPARTMENT}}",
        "content_limits": {"min_length": 4, "max_length": 100},
        "ordering": 4,
    },
    {
        "field_name": "guide_name",
        "field_label": "Faculty Supervisor / Guide Name",
        "field_type": "text",
        "page_or_section": "Cover Page / Certificate",
        "is_required": True,
        "placeholder_identifier": "{{GUIDE_NAME}}",
        "content_limits": {"min_length": 3, "max_length": 100},
        "ordering": 5,
    },
    {
        "field_name": "introduction",
        "field_label": "Chapter 1: Introduction",
        "field_type": "long_text",
        "page_or_section": "Chapter 1: Introduction",
        "is_required": True,
        "placeholder_identifier": "{{INTRODUCTION}}",
        "content_limits": {"min_words": 300, "max_words": 800},
        "ordering": 6,
    },
    {
        "field_name": "objectives",
        "field_label": "Project Objectives",
        "field_type": "list",
        "page_or_section": "Objectives",
        "is_required": True,
        "placeholder_identifier": "{{OBJECTIVES}}",
        "content_limits": {"min_items": 3, "max_items": 6},
        "ordering": 7,
    },
    {
        "field_name": "problem_statement",
        "field_label": "Problem Statement & Motivation",
        "field_type": "long_text",
        "page_or_section": "Problem Statement",
        "is_required": True,
        "placeholder_identifier": "{{PROBLEM_STATEMENT}}",
        "content_limits": {"min_words": 200, "max_words": 500},
        "ordering": 8,
    },
    {
        "field_name": "methodology",
        "field_label": "Chapter 2: System Methodology & Architecture",
        "field_type": "long_text",
        "page_or_section": "Chapter 2: System Methodology",
        "is_required": True,
        "placeholder_identifier": "{{METHODOLOGY}}",
        "content_limits": {"min_words": 400, "max_words": 1000},
        "ordering": 9,
    },
    {
        "field_name": "technologies",
        "field_label": "Tech Stack & Frameworks",
        "field_type": "list",
        "page_or_section": "Technologies",
        "is_required": True,
        "placeholder_identifier": "{{TECHNOLOGIES}}",
        "content_limits": {"min_items": 3, "max_items": 10},
        "ordering": 10,
    },
    {
        "field_name": "implementation",
        "field_label": "Chapter 3: Implementation & Execution",
        "field_type": "long_text",
        "page_or_section": "Chapter 3: Implementation",
        "is_required": True,
        "placeholder_identifier": "{{IMPLEMENTATION}}",
        "content_limits": {"min_words": 500, "max_words": 1200},
        "ordering": 11,
    },
    {
        "field_name": "results",
        "field_label": "Chapter 4: Experimental Results & Analysis",
        "field_type": "long_text",
        "page_or_section": "Chapter 4: Results & Analysis",
        "is_required": True,
        "placeholder_identifier": "{{RESULTS}}",
        "content_limits": {"min_words": 300, "max_words": 800},
        "ordering": 12,
    },
    {
        "field_name": "advantages",
        "field_label": "System Advantages",
        "field_type": "list",
        "page_or_section": "Advantages",
        "is_required": False,
        "placeholder_identifier": "{{ADVANTAGES}}",
        "content_limits": {"min_items": 3, "max_items": 6},
        "ordering": 13,
    },
    {
        "field_name": "limitations",
        "field_label": "System Constraints & Limitations",
        "field_type": "list",
        "page_or_section": "Limitations",
        "is_required": False,
        "placeholder_identifier": "{{LIMITATIONS}}",
        "content_limits": {"min_items": 2, "max_items": 5},
        "ordering": 14,
    },
    {
        "field_name": "future_scope",
        "field_label": "Future Scope & Enhancements",
        "field_type": "long_text",
        "page_or_section": "Future Scope",
        "is_required": False,
        "placeholder_identifier": "{{FUTURE_SCOPE}}",
        "content_limits": {"min_words": 150, "max_words": 400},
        "ordering": 15,
    },
    {
        "field_name": "conclusion",
        "field_label": "Chapter 5: Conclusion",
        "field_type": "long_text",
        "page_or_section": "Chapter 5: Conclusion",
        "is_required": True,
        "placeholder_identifier": "{{CONCLUSION}}",
        "content_limits": {"min_words": 200, "max_words": 500},
        "ordering": 16,
    },
    {
        "field_name": "references",
        "field_label": "Academic References & Bibliography",
        "field_type": "list",
        "page_or_section": "References",
        "is_required": True,
        "placeholder_identifier": "{{REFERENCES}}",
        "content_limits": {"min_items": 5, "max_items": 20},
        "ordering": 17,
    },
    {
        "field_name": "image_1",
        "field_label": "Figure 1: System Architecture Diagram",
        "field_type": "image",
        "page_or_section": "Chapter 2: System Methodology",
        "is_required": True,
        "placeholder_identifier": "{{IMAGE_1}}",
        "content_limits": {},
        "image_dimensions": {"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300},
        "ordering": 18,
    },
    {
        "field_name": "image_2",
        "field_label": "Figure 2: Implementation Setup / Evidence Photo",
        "field_type": "image",
        "page_or_section": "Chapter 3: Implementation",
        "is_required": False,
        "placeholder_identifier": "{{IMAGE_2}}",
        "content_limits": {},
        "image_dimensions": {"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300},
        "ordering": 19,
    },
    {
        "field_name": "image_3",
        "field_label": "Figure 3: Empirical Performance Graph / Chart",
        "field_type": "image",
        "page_or_section": "Chapter 4: Results & Analysis",
        "is_required": False,
        "placeholder_identifier": "{{IMAGE_3}}",
        "content_limits": {},
        "image_dimensions": {"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300},
        "ordering": 20,
    },
]


class MasterTemplateService:
    """Manages the Master College Template and deterministic replacement dataset creation."""

    def get_master_template(self) -> Dict[str, Any]:
        """Fetches the official master template and its fields."""
        client = db_manager.client
        template = None
        if client:
            try:
                res = client.table("templates").select("*").eq("id", MASTER_TEMPLATE_ID).execute()
                if res.data and len(res.data) > 0:
                    template = res.data[0]
            except Exception as e:
                logger.error(f"Error fetching master template: {e}")

        if not template:
            template = {
                "id": MASTER_TEMPLATE_ID,
                "name": "Standard College Academic Report Master Template",
                "is_master": True,
                "is_locked": True,
                "status": "locked",
                "master_version": "1.0.0",
                "description": "Authoritative Fixed College Report Template. Typography, margins, headers, and footers are locked. Content and images are automated via 20 configurable fields.",
                "institution": "College of Engineering & Technology",
                "department": "Department of Computer Science & Engineering",
            }

        fields = self.get_template_fields(MASTER_TEMPLATE_ID)
        return {
            "id": template["id"],
            "name": template["name"],
            "is_master": True,
            "is_locked": True,
            "status": "locked",
            "master_version": template.get("master_version", "1.0.0"),
            "description": template.get("description"),
            "institution": template.get("institution"),
            "department": template.get("department"),
            "fields_count": len(fields),
            "fields": fields,
        }

    def get_template_fields(self, template_id: str) -> List[Dict[str, Any]]:
        """Retrieves ordered fields for the given template."""
        client = db_manager.client
        if client:
            try:
                res = client.table("template_fields").select("*").eq("template_id", template_id).order("ordering", desc=False).execute()
                if res.data and len(res.data) > 0:
                    return res.data
            except Exception as e:
                logger.error(f"Error fetching template fields from DB: {e}")

        # Fallback to CANONICAL_FIELDS
        return [
            {
                "id": f"fld_{i+1}",
                "template_id": template_id,
                **fld,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            for i, fld in enumerate(CANONICAL_FIELDS)
        ]

    def build_replacement_dataset(
        self,
        project_data: Dict[str, Any],
        evidence_assets: Optional[List[Dict[str, Any]]] = None,
        custom_field_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Constructs the complete field replacement dataset:
        Takes student's project facts + evidence and maps them to the 20 template placeholders.
        Preserves 100% of the college layout while replacing matter and images.
        """
        evidence_assets = evidence_assets or []
        custom_field_values = custom_field_values or {}

        title = project_data.get("title") or "Technical Research Report"
        student = project_data.get("student_name") or "Engineering Scholar"
        roll_no = project_data.get("roll_no") or project_data.get("roll_number") or "2026BCSE001"
        dept = project_data.get("department") or "Department of Computer Science & Engineering"
        guide = project_data.get("guide_name") or "Faculty Guide, Ph.D"
        desc = project_data.get("description") or project_data.get("abstract_summary") or ""
        problem = project_data.get("problem_statement") or desc

        dataset: Dict[str, Any] = {
            # Metadata
            "project_title": custom_field_values.get("project_title", title),
            "student_name": custom_field_values.get("student_name", student),
            "roll_number": custom_field_values.get("roll_number", roll_no),
            "department": custom_field_values.get("department", dept),
            "guide_name": custom_field_values.get("guide_name", guide),

            # Core Sections Matter
            "introduction": custom_field_values.get(
                "introduction",
                project_data.get("introduction") or f"This report investigates {title}. Recent advances demonstrate critical importance across engineering domains. The core challenge addressed is {problem[:200]}."
            ),
            "objectives": custom_field_values.get(
                "objectives",
                project_data.get("objectives") or [
                    f"Design and construct an efficient architecture for {title}.",
                    "Analyze empirical performance and latency metrics in field tests.",
                    "Verify academic compliance and safety tolerances against institutional benchmarks."
                ]
            ),
            "problem_statement": custom_field_values.get("problem_statement", project_data.get("problem_statement") or problem),
            "methodology": custom_field_values.get(
                "methodology",
                project_data.get("methodology") or f"The methodology for {title} adopts a modular pipeline comprising data ingestion, processing logic, and verification routines."
            ),
            "technologies": custom_field_values.get(
                "technologies",
                project_data.get("technologies") or project_data.get("tech_stack") or ["Python", "FastAPI", "React", "PostgreSQL"]
            ),
            "implementation": custom_field_values.get(
                "implementation",
                project_data.get("implementation") or f"System implementation for {title} executes hardware and software modules with deterministic state management."
            ),
            "results": custom_field_values.get(
                "results",
                project_data.get("results") or f"Experimental results validate that {title} achieves standard operational parameters with high precision and reliability."
            ),
            "advantages": custom_field_values.get(
                "advantages",
                project_data.get("advantages") or [
                    "Significantly reduced manual intervention.",
                    "Deterministic accuracy and repeatable measurements.",
                    "Scalable architecture suitable for institutional deployment."
                ]
            ),
            "limitations": custom_field_values.get(
                "limitations",
                project_data.get("limitations") or [
                    "Requires network connectivity for real-time telemetry.",
                    "Dependent on calibrated sensor input ranges."
                ]
            ),
            "future_scope": custom_field_values.get(
                "future_scope",
                project_data.get("future_scope") or f"Future extensions will incorporate automated fault recovery and edge AI model quantization for {title}."
            ),
            "conclusion": custom_field_values.get(
                "conclusion",
                project_data.get("conclusion") or f"In conclusion, the project successfully implements {title}, meeting all specified institutional objectives and guidelines."
            ),
            "references": custom_field_values.get(
                "references",
                project_data.get("references") or [
                    "IEEE Standard for Document Format and Syntactic Notation, IEEE Std 829-2022.",
                    "Smith, J. et al., 'Deterministic Document Pipelines in Academic Computing', Journal of Systems, 2024.",
                    "University Academic Council, 'Guidelines for Engineering Project Reports', 2026."
                ]
            ),

            # Images
            "image_1": custom_field_values.get("image_1") or (
                (evidence_assets[0].get("storage_path") or evidence_assets[0].get("url") or evidence_assets[0])
                if len(evidence_assets) > 0 and isinstance(evidence_assets[0], dict)
                else (evidence_assets[0] if len(evidence_assets) > 0 else None)
            ),
            "image_2": custom_field_values.get("image_2") or (
                (evidence_assets[1].get("storage_path") or evidence_assets[1].get("url") or evidence_assets[1])
                if len(evidence_assets) > 1 and isinstance(evidence_assets[1], dict)
                else (evidence_assets[1] if len(evidence_assets) > 1 else None)
            ),
            "image_3": custom_field_values.get("image_3") or (
                (evidence_assets[2].get("storage_path") or evidence_assets[2].get("url") or evidence_assets[2])
                if len(evidence_assets) > 2 and isinstance(evidence_assets[2], dict)
                else (evidence_assets[2] if len(evidence_assets) > 2 else None)
            ),
        }

        return dataset


master_template_service = MasterTemplateService()
