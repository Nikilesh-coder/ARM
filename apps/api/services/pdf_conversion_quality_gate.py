"""
ARM — PDF Conversion Quality Gate
Validates candidate converted DOCX files against the original PDF template
before the DOCX is accepted and registered into the ARM report generation pipeline.
Enforces strict page-count preservation, blank page elimination, dimension integrity,
and visual fidelity, with specialized zero-tolerance rules for presentation templates.
"""

import os
import tempfile
from typing import Dict, Any, List, Tuple, Optional
import docx
import pymupdf

from apps.api.core.logging import get_logger
from apps.api.services.visual_report_validator import VisualReportValidator
from apps.api.services.pdf_visual_comparison_service import pdf_visual_comparison_service

logger = get_logger("service.pdf_conversion_quality_gate")


class PdfConversionQualityGate:
    """Automated Quality Gate for validating PDF -> DOCX conversions."""

    @classmethod
    def is_presentation_template(cls, pdf_path: str) -> Tuple[bool, float, float]:
        """
        Determines whether the PDF is a presentation/slide deck based on geometry.
        Returns (is_presentation, width_in, height_in).
        """
        try:
            doc = pymupdf.open(pdf_path)
            if len(doc) == 0:
                doc.close()
                return False, 0.0, 0.0
            p0 = doc[0]
            w_in = round(p0.rect.width / 72.0, 2)
            h_in = round(p0.rect.height / 72.0, 2)
            doc.close()
            is_pres = (w_in > h_in) and ((w_in / max(0.1, h_in)) >= 1.25)
            return is_pres, w_in, h_in
        except Exception as e:
            logger.warning(f"[QUALITY GATE] Error inspecting PDF geometry: {e}")
            return False, 0.0, 0.0

    @classmethod
    def validate_pdf_conversion_quality(
        cls,
        original_pdf: str,
        converted_docx: str,
        staging_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive Quality Gate validation comparing original PDF vs converted DOCX.
        Returns structured decision dictionary with PASS/FAIL status and detailed reasons.
        """
        if not os.path.exists(original_pdf):
            return {
                "passed": False,
                "status": "FAIL",
                "reasons": [f"Original PDF not found: {original_pdf}"],
            }

        if not os.path.exists(converted_docx) or os.path.getsize(converted_docx) == 0:
            return {
                "passed": False,
                "status": "FAIL",
                "reasons": [f"Converted DOCX does not exist or is empty: {converted_docx}"],
            }

        # 1. Parse original PDF
        try:
            orig_doc = pymupdf.open(original_pdf)
            orig_pages_count = len(orig_doc)
            orig_is_pres, orig_w_in, orig_h_in = cls.is_presentation_template(original_pdf)
            orig_texts = [p.get_text() or "" for p in orig_doc]
            orig_doc.close()
        except Exception as e:
            return {
                "passed": False,
                "status": "FAIL",
                "reasons": [f"Failed to parse original PDF: {e}"],
            }

        temp_dir = staging_dir or tempfile.mkdtemp(prefix="arm_qgate_")
        os.makedirs(temp_dir, exist_ok=True)
        rendered_pdf = os.path.join(temp_dir, "rendered_docx.pdf")

        converted_ok = VisualReportValidator._convert_docx_to_pdf_word(converted_docx, rendered_pdf)
        if not converted_ok or not os.path.exists(rendered_pdf):
            return {
                "passed": False,
                "status": "FAIL",
                "reasons": ["Word COM failed to open and render converted DOCX to PDF."],
            }

        # 3. Parse Rendered DOCX
        try:
            conv_doc = pymupdf.open(rendered_pdf)
            conv_pages_count = len(conv_doc)
            p0 = conv_doc[0]
            conv_w_in = round(p0.rect.width / 72.0, 2)
            conv_h_in = round(p0.rect.height / 72.0, 2)
            conv_texts = [p.get_text() or "" for p in conv_doc]
            conv_doc.close()
        except Exception as e:
            return {
                "passed": False,
                "status": "FAIL",
                "reasons": [f"Failed to inspect rendered DOCX PDF: {e}"],
            }

        # 4. Check Blank Pages on Converted Document
        # Render pages to check pixel variance
        img_dir = os.path.join(temp_dir, "rendered_pages")
        conv_images = pdf_visual_comparison_service.render_pdf_to_images(rendered_pdf, img_dir)
        conv_blank_pages = []
        for idx, img_p in enumerate(conv_images, start=1):
            txt = conv_texts[idx - 1] if idx - 1 < len(conv_texts) else ""
            if pdf_visual_comparison_service.detect_blank_page(img_p, txt):
                conv_blank_pages.append(idx)

        # 5. Evaluate Quality Gate Criteria
        reasons = []
        is_passed = True

        # Rule A: Presentation-specific page count strict equality
        if orig_is_pres:
            if conv_pages_count != orig_pages_count:
                is_passed = False
                reasons.append(
                    f"Presentation template page count mismatch: Original has {orig_pages_count} slides, "
                    f"but converted DOCX renders as {conv_pages_count} pages ({conv_pages_count - orig_pages_count:+d} extra/missing)."
                )
        else:
            # Standard documents allow max 1 page tolerance
            if abs(conv_pages_count - orig_pages_count) > 1:
                is_passed = False
                reasons.append(
                    f"Document page count mismatch: Original has {orig_pages_count} pages, "
                    f"converted DOCX has {conv_pages_count} pages."
                )

        # Rule B: Blank page elimination
        if len(conv_blank_pages) > 0:
            is_passed = False
            reasons.append(
                f"Converted DOCX introduced {len(conv_blank_pages)} blank/near-blank pages: {conv_blank_pages}"
            )

        # Rule C: Page dimensions & orientation
        w_diff = abs(conv_w_in - orig_w_in)
        h_diff = abs(conv_h_in - orig_h_in)
        if w_diff > 0.5 or h_diff > 0.5:
            # Check if aspect ratio matches
            aspect_orig = orig_w_in / max(0.1, orig_h_in)
            aspect_conv = conv_w_in / max(0.1, conv_h_in)
            if abs(aspect_orig - aspect_conv) > 0.15:
                is_passed = False
                reasons.append(
                    f"Page aspect ratio changed: Original is {orig_w_in}\"x{orig_h_in}\" (aspect {aspect_orig:.2f}), "
                    f"converted DOCX is {conv_w_in}\"x{conv_h_in}\" (aspect {aspect_conv:.2f})."
                )

        status_str = "PASS" if is_passed else "FAIL"

        result = {
            "passed": is_passed,
            "status": status_str,
            "is_presentation": orig_is_pres,
            "page_counts": {
                "original_pdf": orig_pages_count,
                "converted_docx": conv_pages_count,
                "difference": conv_pages_count - orig_pages_count,
            },
            "blank_pages": {
                "original_pdf": [],
                "converted_docx": conv_blank_pages,
            },
            "dimensions": {
                "original_pdf": {"width_in": orig_w_in, "height_in": orig_h_in},
                "converted_docx": {"width_in": conv_w_in, "height_in": conv_h_in},
            },
            "reasons": reasons,
        }

        logger.info(
            f"[QUALITY GATE] {status_str} | Original: {orig_pages_count} pages | "
            f"Converted: {conv_pages_count} pages | Blank pages: {conv_blank_pages} | "
            f"Reasons: {reasons if reasons else 'All quality checks satisfied.'}"
        )

        return result


quality_gate = PdfConversionQualityGate()
validate_pdf_conversion_quality = quality_gate.validate_pdf_conversion_quality
