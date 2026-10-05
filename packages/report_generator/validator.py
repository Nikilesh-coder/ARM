"""
ARM Stage 7 - Deterministic Section Content Validator
Enforces structural correspondence with Approved Plan, fact grounding with Stage 5 Project facts,
evidence inventory alignment, prompt injection defense, and content block integrity.
"""

import re
from typing import List, Dict, Any, Optional, Set
from packages.report_planner.schema import SectionPlanItem
from packages.report_generator.schema import (
    SectionGenerationOutput,
    ContentBlock,
    MissingInformationItem,
    GroundingStatus,
    VisualRequirement
)


ALLOWED_BLOCK_TYPES = {"heading", "paragraph", "bullet_list", "numbered_list", "table", "quote", "note"}

# Suspicious phrases indicating LLM prompt leakage or meta commentary
AI_META_PATTERNS = [
    r"\bas an ai\b",
    r"\bi am an ai\b",
    r"\blanguage model\b",
    r"\bgemini\b",
    r"\bsystem instruction\b",
    r"\bsystem prompt\b",
    r"\bignore previous instructions\b",
    r"\bhere is the generated section\b",
    r"\bcertainly! here\b",
    r"\bcertainly, here\b",
    r"\bas requested\b",
]

# Numerical metric patterns that often indicate hallucination when absent from ground truth
HALLUCINATED_METRIC_PATTERN = re.compile(
    r"\b(?:\d{2,3}(?:\.\d+)?%|\b\d{1,3}(?:,\d{3})+\b|\b\d+\.\d{2,}\b|\b(?:accuracy|precision|recall|f1-score|latency)\s+(?:of|is|reached|achieved)\s+\d+)",
    re.IGNORECASE
)


class SectionContentValidator:
    """Validates generated section output against approved report plan and project facts."""

    @classmethod
    def validate_section(
        cls,
        output: SectionGenerationOutput,
        plan_section: SectionPlanItem,
        project_data: Dict[str, Any],
        evidence_items: List[Dict[str, Any]]
    ) -> SectionGenerationOutput:
        """
        Validates a single section's output.
        Mutates/enriches grounding_status, missing_information, warnings, and word_count.
        """
        warnings: List[str] = list(output.warnings or [])
        grounding_notes: List[str] = list(output.grounding_notes or [])
        missing_items: List[MissingInformationItem] = list(output.missing_information or [])

        # 1. Section Identity & Order Verification
        if output.section_id != plan_section.section_id:
            warnings.append(
                f"Section ID mismatch: generated '{output.section_id}' expected '{plan_section.section_id}'. Realigned."
            )
            output.section_id = plan_section.section_id

        output.section_title = plan_section.title
        output.section_order = plan_section.order

        # 2. Block Type & Content Integrity Check
        sanitized_blocks: List[ContentBlock] = []
        total_words = 0

        for block in output.content_blocks:
            if block.block_type not in ALLOWED_BLOCK_TYPES:
                warnings.append(f"Unsupported block type '{block.block_type}' normalized to 'paragraph'.")
                block.block_type = "paragraph"

            # Compute words
            block_text = block.text or ""
            if block.items:
                block_text += " " + " ".join(block.items)
            words = len(block_text.split())
            total_words += words

            # Check for AI meta-commentary or prompt leakage
            for pattern in AI_META_PATTERNS:
                if re.search(pattern, block_text, re.IGNORECASE):
                    warnings.append(f"Detected and sanitized AI meta-commentary matching pattern '{pattern}'.")
                    block_text = re.sub(pattern, "", block_text, flags=re.IGNORECASE).strip()
                    block.text = block_text

            sanitized_blocks.append(block)

        output.content_blocks = sanitized_blocks
        output.word_count = total_words

        # 3. Detect Empty Required Content
        if plan_section.required and not output.content_blocks:
            missing_items.append(
                MissingInformationItem(
                    field="content_blocks",
                    reason=f"Section '{plan_section.title}' is mandatory per template but produced no content blocks.",
                    severity="critical"
                )
            )

        # 4. Evidence References Alignment
        # Collect valid evidence identifiers from inventory
        valid_evidence_ids: Set[str] = set()
        for ev in evidence_items:
            if ev.get("id"):
                valid_evidence_ids.add(str(ev["id"]))
            if ev.get("filename"):
                valid_evidence_ids.add(str(ev["filename"]).lower())
            if ev.get("original_filename"):
                valid_evidence_ids.add(str(ev["original_filename"]).lower())

        for block in output.content_blocks:
            validated_source_ids = []
            for cited_id in block.source_evidence_ids:
                cited_str = str(cited_id).strip()
                if cited_str in valid_evidence_ids or cited_str.lower() in valid_evidence_ids:
                    validated_source_ids.append(cited_str)
                else:
                    warnings.append(
                        f"Unverified evidence citation '{cited_str}' removed from section '{plan_section.title}'."
                    )
            block.source_evidence_ids = validated_source_ids

        # 5. Project Fact Grounding & Metric Hallucination Detection
        # Gather all text present in verified project facts
        project_text_corpus = " ".join([
            str(v) for k, v in project_data.items()
            if isinstance(v, (str, int, float)) and k not in ("id", "user_id", "owner_id")
        ]).lower()

        # Check evidence filenames/types as well
        evidence_text_corpus = " ".join([
            f"{e.get('filename', '')} {e.get('file_type', '')} {e.get('description', '')}"
            for e in evidence_items
        ]).lower()

        combined_corpus = project_text_corpus + " " + evidence_text_corpus

        has_potential_hallucination = False
        for block in output.content_blocks:
            text_to_check = block.text or ""
            matches = HALLUCINATED_METRIC_PATTERN.findall(text_to_check)
            for m in matches:
                # If the metric is not present in the combined ground truth corpus, flag it
                if m.lower() not in combined_corpus:
                    warnings.append(
                        f"Unverified numerical claim '{m}' flagged in section '{plan_section.title}'. Requires student verification."
                    )
                    has_potential_hallucination = True

        # 6. Preserve Plan Missing Information
        if plan_section.missing_information:
            existing_fields = {item.field for item in missing_items}
            for mi in plan_section.missing_information:
                if mi not in existing_fields:
                    missing_items.append(
                        MissingInformationItem(
                            field=mi,
                            reason=f"Required fact '{mi}' was not provided in project information or evidence locker.",
                            severity="warning"
                        )
                    )

        # 7. Preserve Research & Visual Markers
        if plan_section.research_required:
            output.research_marker_preserved = True
            grounding_notes.append("External academic research required (citation search deferred to later stage).")

        # 8. Determine Final Grounding Status
        output.missing_information = missing_items
        output.warnings = warnings
        output.grounding_notes = grounding_notes

        if not output.content_blocks and plan_section.required:
            output.grounding_status = "validation_failed"
        elif any(mi.severity == "critical" for mi in missing_items):
            output.grounding_status = "missing_information"
        elif has_potential_hallucination or any(mi.severity == "warning" for mi in missing_items):
            output.grounding_status = "requires_review" if has_potential_hallucination else "partially_grounded"
        else:
            output.grounding_status = "grounded"

        return output
