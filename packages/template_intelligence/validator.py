"""
ARM — Template Review & Lock Validator
Provides rigorous validation for student-reviewed template structures prior to locking.
Ensures document hierarchy, typography bounds, section uniqueness, semantic roles,
and immutable source fact preservation.
"""

from typing import Dict, Any, List, Tuple, Optional
from packages.template_intelligence.schema import TemplateSchema, DetectedSection

CANONICAL_SEMANTIC_ROLES = {
    "TITLE_PAGE",
    "CERTIFICATE",
    "DECLARATION",
    "ACKNOWLEDGEMENT",
    "ABSTRACT",
    "TOC",
    "LIST_OF_FIGURES",
    "LIST_OF_TABLES",
    "INTRODUCTION",
    "LITERATURE_REVIEW",
    "METHODOLOGY",
    "SYSTEM_DESIGN",
    "IMPLEMENTATION",
    "RESULTS",
    "DISCUSSION",
    "CONCLUSION",
    "FUTURE_WORK",
    "REFERENCES",
    "APPENDIX",
    "CUSTOM_SECTION"
}


class TemplateReviewValidator:
    """
    Validates reviewed template schemas before saving review drafts or locking as authoritative.
    Differentiates between blocking errors (which reject save/lock) and non-blocking warnings.
    """

    @classmethod
    def validate_review(
        cls,
        schema_dict: Dict[str, Any],
        source_metadata: Optional[Dict[str, Any]] = None,
        is_locking: bool = False
    ) -> Tuple[Optional[TemplateSchema], List[str], List[str]]:
        """
        Validates schema_dict.
        Returns (parsed_template_schema, blocking_errors, warnings).
        """
        blocking_errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(schema_dict, dict):
            return None, ["Review payload must be a valid JSON object."], []

        # 1. Schema version check
        schema_version = schema_dict.get("schema_version", "1.0.0")
        if not schema_version.startswith("1."):
            blocking_errors.append(f"Unsupported schema version: '{schema_version}'. Only 1.x is supported.")

        # 2. Structural Pydantic parse
        parsed_schema: Optional[TemplateSchema] = None
        try:
            parsed_schema = TemplateSchema(**schema_dict)
        except Exception as e:
            blocking_errors.append(f"Invalid schema structure: {str(e)}")
            return None, blocking_errors, warnings

        # 3. Sections validation
        sections = parsed_schema.sections
        if not sections or len(sections) == 0:
            blocking_errors.append("Template must contain at least one detected section.")
        else:
            seen_ids = set()
            highest_parent_level_seen = 0
            levels_seen = set()

            for idx, sec in enumerate(sections):
                # Check empty title
                title = (sec.detected_title or "").strip()
                if not title:
                    blocking_errors.append(f"Section at index {idx} has an empty or blank title.")

                # Check unique IDs
                if sec.id in seen_ids:
                    blocking_errors.append(f"Duplicate section ID detected: '{sec.id}'. Section IDs must be unique.")
                seen_ids.add(sec.id)

                # Check level bounds
                if sec.level < 1 or sec.level > 6:
                    blocking_errors.append(f"Section '{title}' has invalid hierarchy level {sec.level}. Must be between 1 and 6.")

                # Check order (allows 0-indexed or 1-indexed sequences)
                if sec.order < 0:
                    blocking_errors.append(f"Section '{title}' has invalid order {sec.order}. Must be a non-negative integer.")

                # Check semantic role
                role = (sec.semantic_role or "").upper()
                if role not in CANONICAL_SEMANTIC_ROLES:
                    warnings.append(f"Section '{title}' uses non-standard semantic role '{sec.semantic_role}'. Defaulting to CUSTOM_SECTION.")

                # Hierarchy sanity check:
                # If level > 1, there must be at least one preceding ancestor with level - 1
                if sec.level > 1:
                    required_parent_level = sec.level - 1
                    if required_parent_level not in levels_seen:
                        blocking_errors.append(
                            f"Malformed hierarchy: Section '{title}' (Level {sec.level}) has no preceding parent Level {required_parent_level}."
                        )
                
                levels_seen.add(sec.level)

        # 4. Geometry and Margin validation
        geom = parsed_schema.geometry
        if geom and geom.margins:
            m = geom.margins
            if m.top_mm <= 0 or m.bottom_mm <= 0 or m.left_mm <= 0 or m.right_mm <= 0:
                blocking_errors.append("Page margins must be strictly positive numbers (greater than 0 mm).")
            if m.top_mm > 150 or m.bottom_mm > 150 or m.left_mm > 150 or m.right_mm > 150:
                warnings.append("Page margins are unusually large (> 150 mm).")

        # 5. Typography validation
        typo = parsed_schema.typography
        if typo:
            if typo.default_size_pt <= 4 or typo.default_size_pt > 100:
                blocking_errors.append(f"Default font size {typo.default_size_pt} pt is outside valid academic range (5 - 100 pt).")
            if typo.line_spacing <= 0.4 or typo.line_spacing > 5.0:
                blocking_errors.append(f"Line spacing {typo.line_spacing} is outside valid range (0.5 - 5.0).")

        # 6. Source Facts Preservation
        # Ensure user did not tamper with immutable source metadata to claim the uploaded file itself changed
        if source_metadata and parsed_schema.document:
            src_doc = source_metadata.get("document") or {}
            # Verify file_name, file_type, page_count were not falsified
            if src_doc.get("file_name") and parsed_schema.document.file_name != src_doc.get("file_name"):
                parsed_schema.document.file_name = src_doc["file_name"]
            if src_doc.get("file_type") and parsed_schema.document.file_type != src_doc.get("file_type"):
                parsed_schema.document.file_type = src_doc["file_type"]
            if src_doc.get("page_count") and parsed_schema.document.page_count != src_doc.get("page_count"):
                parsed_schema.document.page_count = src_doc["page_count"]

        # Aggregate warnings from parsed schema
        if parsed_schema.warnings:
            warnings.extend([w for w in parsed_schema.warnings if w not in warnings])
        if parsed_schema.validation and parsed_schema.validation.warnings:
            warnings.extend([w for w in parsed_schema.validation.warnings if w not in warnings])

        return parsed_schema, blocking_errors, warnings
