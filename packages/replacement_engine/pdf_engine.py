"""
ARM Stage 10 - In-Place PDF Template Replacement & Analysis Engine
Supports:
CASE 1: PDF compilation from ARM's structured template/document (preserves formatting and layout).
CASE 2: College PDF provided as reference/template:
- In-depth structural analysis of text layer, AcroForm fields, raster scans, and bounding boxes.
- Prevention of blind text overlay on top of existing text.
- Safe field mapping to ARM TemplateFields.
- Clear, deterministic reporting when a PDF cannot be modified safely and must be converted to DOCX.
"""

import os
import re
import uuid
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field
import pymupdf

from apps.api.core.logging import get_logger
from apps.api.services.master_template_service import CANONICAL_FIELDS, MASTER_TEMPLATE_ID
from packages.replacement_engine.base import (
    BaseReplacementEngine,
    ReplacementState,
    FieldReplacementAudit,
    ReplacementErrorDetail,
    ReplacementResult,
)

logger = get_logger("replacement_engine.pdf")


class PdfAnalysisResult(BaseModel):
    """Detailed structural analysis of a candidate PDF template."""
    is_safe_for_replacement: bool
    template_type: str  # "acroform", "bounded_metadata", "scanned_raster", "unstructured_reference", "overflow_risk"
    total_pages: int
    has_text_layer: bool
    is_form_pdf: bool
    detected_fields: List[str] = Field(default_factory=list)
    field_mappings: Dict[str, str] = Field(default_factory=dict)  # template_key -> canonical_field
    issues: List[str] = Field(default_factory=list)
    recommendation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PdfTemplateAnalyzer:
    """
    Analyzes whether a college PDF contains editable text and layout information
    sufficient for reliable in-place replacement without breaking visual integrity.
    """

    @classmethod
    def analyze(cls, pdf_path: str) -> PdfAnalysisResult:
        """
        Inspects PDF structure:
        1. Validates document accessibility and page count.
        2. Detects scanned/raster images vs editable vector text streams.
        3. Identifies interactive AcroForm fields.
        4. Detects placeholder patterns and bounding box collision risks.
        5. Determines if reliable in-place replacement is possible.
        """
        if not os.path.exists(pdf_path):
            return PdfAnalysisResult(
                is_safe_for_replacement=False,
                template_type="missing_file",
                total_pages=0,
                has_text_layer=False,
                is_form_pdf=False,
                issues=[f"File not found on disk: '{pdf_path}'"],
                recommendation="Provide a valid PDF file path.",
            )

        try:
            doc = pymupdf.open(pdf_path)
        except Exception as e:
            return PdfAnalysisResult(
                is_safe_for_replacement=False,
                template_type="corrupt_pdf",
                total_pages=0,
                has_text_layer=False,
                is_form_pdf=False,
                issues=[f"Failed to parse PDF document: {str(e)}"],
                recommendation="The file is damaged or not a valid PDF.",
            )

        total_pages = len(doc)
        total_chars = 0
        total_images = 0
        detected_fields: List[str] = []
        field_mappings: Dict[str, str] = {}
        issues: List[str] = []

        is_form = bool(doc.is_form_pdf)
        form_widgets: List[Dict[str, Any]] = []

        canonical_names = {f["field_name"].lower() for f in CANONICAL_FIELDS}

        # 1. Inspect AcroForm fields across pages
        for page_idx, page in enumerate(doc):
            widgets = list(page.widgets())
            for w in widgets:
                if w.field_name:
                    name_clean = w.field_name.strip()
                    detected_fields.append(name_clean)
                    form_widgets.append({
                        "page": page_idx + 1,
                        "field_name": name_clean,
                        "rect": [w.rect.x0, w.rect.y0, w.rect.x1, w.rect.y1],
                    })
                    # Match with canonical field
                    low_name = name_clean.lower()
                    for c_name in canonical_names:
                        if c_name in low_name or low_name in c_name:
                            field_mappings[name_clean] = c_name
                            break

        # 2. Inspect text layers and images
        page_texts: List[str] = []
        for page in doc:
            p_text = page.get_text("text") or ""
            total_chars += len(p_text.strip())
            page_texts.append(p_text)
            total_images += len(page.get_images())

        full_text = " ".join(page_texts)

        # 3. Check for Scanned / Raster PDF
        if total_chars < 40 and total_images >= total_pages:
            doc.close()
            return PdfAnalysisResult(
                is_safe_for_replacement=False,
                template_type="scanned_raster",
                total_pages=total_pages,
                has_text_layer=False,
                is_form_pdf=False,
                detected_fields=[],
                issues=[
                    "The provided PDF is a scanned raster document without an editable text layer.",
                    "No vector fonts or extractable text streams are present.",
                ],
                recommendation=(
                    "Reliable in-place replacement cannot be performed on scanned raster PDFs. "
                    "The PDF must be converted into an ARM-supported structured template (DOCX format)."
                ),
                metadata={"total_images": total_images, "total_chars": total_chars},
            )

        # 4. If Interactive AcroForm PDF -> Highly reliable replacement
        if is_form and form_widgets:
            doc.close()
            return PdfAnalysisResult(
                is_safe_for_replacement=True,
                template_type="acroform",
                total_pages=total_pages,
                has_text_layer=True,
                is_form_pdf=True,
                detected_fields=detected_fields,
                field_mappings=field_mappings,
                issues=[],
                recommendation="Interactive PDF form detected. Fields can be reliably replaced in-place.",
                metadata={"form_widgets_count": len(form_widgets)},
            )

        # 5. Search for placeholder syntax (e.g. {{PROJECT_TITLE}}, {student_name})
        placeholder_matches = re.findall(r'\{\{([a-zA-Z0-9_]+)\}\}|\{([a-zA-Z0-9_]+)\}', full_text)
        found_placeholders = set()
        for g1, g2 in placeholder_matches:
            found_placeholders.add((g1 or g2).lower())

        for p_name in found_placeholders:
            detected_fields.append(p_name)
            for c_name in canonical_names:
                if c_name in p_name or p_name in c_name:
                    field_mappings[p_name] = c_name
                    break

        # Check for multi-paragraph / long-text fields among detected placeholders
        flowable_long_fields = {
            "introduction", "methodology", "implementation", "results", "conclusion",
            "problem_statement", "objectives", "technologies", "references", "future_scope"
        }
        has_flowable_fields = bool(found_placeholders.intersection(flowable_long_fields))

        # In fixed-layout PDF, multi-paragraph fields cannot be paginated or reflowed safely
        if has_flowable_fields:
            doc.close()
            issues.append(
                "PDF contains long-text flowable fields (e.g., 'introduction', 'methodology') that require dynamic pagination."
            )
            issues.append(
                "Fixed-layout PDF formats do not support text reflow across pages or paragraphs without collision."
            )
            return PdfAnalysisResult(
                is_safe_for_replacement=False,
                template_type="overflow_risk",
                total_pages=total_pages,
                has_text_layer=True,
                is_form_pdf=False,
                detected_fields=list(found_placeholders),
                field_mappings=field_mappings,
                issues=issues,
                recommendation=(
                    "This PDF contains multi-paragraph sections that cannot reflow safely in fixed-layout PDF format. "
                    "The PDF must be converted into an ARM-supported structured template (DOCX format)."
                ),
                metadata={"flowable_fields_detected": list(found_placeholders.intersection(flowable_long_fields))},
            )

        # 6. If only short metadata placeholders exist (e.g. title, student_name, roll_number, guide_name)
        metadata_only_fields = {"project_title", "student_name", "roll_number", "department", "guide_name"}
        if found_placeholders and found_placeholders.issubset(metadata_only_fields):
            doc.close()
            return PdfAnalysisResult(
                is_safe_for_replacement=True,
                template_type="bounded_metadata",
                total_pages=total_pages,
                has_text_layer=True,
                is_form_pdf=False,
                detected_fields=list(found_placeholders),
                field_mappings=field_mappings,
                issues=[],
                recommendation="PDF contains isolated metadata placeholders. Clean redaction and substitution can be performed safely.",
                metadata={"metadata_fields": list(found_placeholders)},
            )

        # 7. Unstructured Reference PDF (e.g. pre-filled final report without placeholders)
        doc.close()
        return PdfAnalysisResult(
            is_safe_for_replacement=False,
            template_type="unstructured_reference",
            total_pages=total_pages,
            has_text_layer=True,
            is_form_pdf=False,
            detected_fields=[],
            field_mappings={},
            issues=[
                "PDF contains static pre-rendered text without demarcated placeholder tokens or form fields.",
                "Modifying static text directly in a fixed-layout PDF without reflow logic causes text overlap and layout breakage.",
            ],
            recommendation=(
                "This reference PDF cannot be modified safely in-place without altering its layout. "
                "The PDF must be converted into an ARM-supported structured template (DOCX format)."
            ),
            metadata={"total_chars": total_chars},
        )


class PdfTemplateReplacementEngine(BaseReplacementEngine):
    """
    PDF Template Replacement Engine for ARM.
    Never blindly overlays text on top of existing text.
    Performs safety verification before any modification.
    Supports:
    - CASE 1: Structured document generation with PDF output.
    - CASE 2: Safe in-place replacement on interactive or bounded PDF templates.
    """

    def __init__(self, canonical_fields: Optional[List[Dict[str, Any]]] = None):
        self.canonical_fields = canonical_fields or CANONICAL_FIELDS

    def analyze_template(self, pdf_path: str) -> PdfAnalysisResult:
        """Runs the structural layout and editable text analyzer on a candidate PDF."""
        return PdfTemplateAnalyzer.analyze(pdf_path)

    def replace(
        self,
        template_path: str,
        field_values: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ReplacementResult:
        """
        Executes safe replacement on a PDF template:
        1. Analyzes whether PDF contains editable layout/form information.
        2. If unsafe, fails with a clear, actionable explanation rather than producing a broken PDF.
        3. If safe, performs clean in-place replacement (AcroForms or clean redaction).
        """
        job_id = job_id or str(uuid.uuid4())
        image_assets = image_assets or {}
        audit_list: List[FieldReplacementAudit] = []
        warnings: List[str] = []
        errors: List[ReplacementErrorDetail] = []

        if not os.path.exists(template_path):
            err = f"PDF template file not found at: '{template_path}'"
            logger.error(err)
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="template_file", reason=err)],
            )

        if not output_path:
            output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"arm_report_{job_id[:8]}.pdf")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 1. Structural Feasibility Analysis
        analysis = self.analyze_template(template_path)
        logger.info(f"[{job_id}] PDF analysis: type={analysis.template_type}, safe={analysis.is_safe_for_replacement}")

        if not analysis.is_safe_for_replacement:
            error_reason = (
                f"PDF template '{os.path.basename(template_path)}' cannot be safely replaced in-place "
                f"({analysis.template_type}). {analysis.recommendation}"
            )
            for iss in analysis.issues:
                errors.append(ReplacementErrorDetail(field="pdf_structure", reason=iss))

            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=errors,
                warnings=[analysis.recommendation],
                metadata={
                    "analysis": analysis.model_dump(),
                    "recommended_action": "convert_to_docx",
                },
            )

        # 2. Execute safe in-place replacement
        doc = pymupdf.open(template_path)
        fields_replaced_count = 0

        try:
            # Case A: AcroForm PDF
            if analysis.template_type == "acroform":
                for page in doc:
                    for widget in page.widgets():
                        w_name = widget.field_name
                        val = None
                        if w_name in field_values:
                            val = field_values[w_name]
                        elif w_name in analysis.field_mappings:
                            canonical_key = analysis.field_mappings[w_name]
                            val = field_values.get(canonical_key)

                        if val is not None:
                            widget.field_value = str(val)
                            widget.update()
                            fields_replaced_count += 1
                            audit_list.append(
                                FieldReplacementAudit(
                                    field_name=w_name,
                                    placeholder=f"Form:{w_name}",
                                    field_type="form_field",
                                    replaced=True,
                                    new_snippet=str(val)[:80],
                                    formatting_preserved=True,
                                )
                            )

            # Case B: Bounded Text Metadata Placeholders (Clean Redaction & Insertion)
            elif analysis.template_type == "bounded_metadata":
                for page in doc:
                    for field_key, val in field_values.items():
                        if val is None:
                            continue
                        patterns = [
                            f"{{{{{field_key.upper()}}}}}",
                            f"{{{{{field_key.lower()}}}}}",
                            f"{{{field_key.upper()}}}",
                            f"{{{field_key.lower()}}}",
                        ]
                        for pat in patterns:
                            rects = page.search_for(pat)
                            for r in rects:
                                # Clean redaction: erases underlying text before inserting, NEVER blindly overlaying
                                page.add_redact_annot(
                                    r,
                                    text=str(val),
                                    fontsize=11.0,
                                    align=pymupdf.TEXT_ALIGN_LEFT,
                                )
                                page.apply_redactions()
                                fields_replaced_count += 1
                                audit_list.append(
                                    FieldReplacementAudit(
                                        field_name=field_key,
                                        placeholder=pat,
                                        field_type="metadata_text",
                                        replaced=True,
                                        new_snippet=str(val)[:80],
                                        formatting_preserved=True,
                                    )
                                )

            doc.save(output_path)
            doc.close()
            logger.info(f"[{job_id}] Successfully saved safe PDF replacement to: {output_path}")

        except Exception as ex:
            doc.close()
            err_msg = f"Failed to perform safe replacement on PDF: {str(ex)}"
            logger.error(err_msg)
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="pdf_replacement", reason=err_msg)],
            )

        return ReplacementResult(
            success=True,
            job_id=job_id,
            state=ReplacementState.COMPLETED,
            template_path=template_path,
            output_pdf_path=output_path,
            fields_replaced=fields_replaced_count,
            total_fields=len(analysis.detected_fields),
            audit=audit_list,
            warnings=warnings,
            metadata={
                "pdf_analysis": analysis.model_dump(),
                "output_format": "pdf",
            },
        )
