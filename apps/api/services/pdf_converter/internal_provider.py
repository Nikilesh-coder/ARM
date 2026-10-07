"""
ARM — Internal PDF to DOCX Converter Provider
Default fallback engine using local pdf2docx library.
Includes automated presentation slide layout-fitting to prevent
vertical overflow and extra blank pages on presentation templates.
"""

import os
import time
from typing import Optional, Dict, Any
import docx
from docx.shared import Inches, Pt
import pymupdf
from pdf2docx import Converter

from apps.api.core.logging import get_logger
from apps.api.services.pdf_converter.base import (
    BasePdfConverterProvider,
    ConversionTiming,
    ConversionResult,
)

logger = get_logger("service.pdf_converter.internal")


class InternalPdfConverterProvider(BasePdfConverterProvider):
    """Local, embedded PDF to DOCX converter using pdf2docx."""

    def __init__(self, fit_presentation: bool = True):
        self.fit_presentation = fit_presentation

    @property
    def name(self) -> str:
        return "internal"

    def is_available(self) -> bool:
        """Internal pdf2docx converter is always available locally."""
        return True

    @staticmethod
    def is_presentation_pdf(pdf_path: str) -> bool:
        """Detects if PDF is a presentation/slide deck (landscape, 4:3 or 16:9)."""
        try:
            doc = pymupdf.open(pdf_path)
            if len(doc) == 0:
                doc.close()
                return False
            p0 = doc[0]
            w_pt, h_pt = p0.rect.width, p0.rect.height
            doc.close()
            return (w_pt > h_pt) and ((w_pt / max(1.0, h_pt)) >= 1.25)
        except Exception:
            return False

    def fit_presentation_layout(self, docx_path: str) -> bool:
        """
        Normalizes slide margins and paragraph vertical spacing so that
        elements fit strictly within the slide bounds without creating extra pages.
        """
        try:
            doc = docx.Document(docx_path)
            for sec in doc.sections:
                sec.top_margin = Inches(0.0)
                sec.bottom_margin = Inches(0.0)
                sec.left_margin = Inches(0.0)
                sec.right_margin = Inches(0.0)

            for p in doc.paragraphs:
                if p.paragraph_format.space_before and p.paragraph_format.space_before > Pt(2):
                    p.paragraph_format.space_before = int(p.paragraph_format.space_before * 0.82)
                p.paragraph_format.space_after = Pt(0)
                if p.paragraph_format.line_spacing and p.paragraph_format.line_spacing > 1.2:
                    p.paragraph_format.line_spacing = 1.15

            doc.save(docx_path)
            logger.info(f"[INTERNAL CONVERTER] Successfully normalized presentation slide layout for '{docx_path}'")
            return True
        except Exception as e:
            logger.warning(f"[INTERNAL CONVERTER] Presentation layout normalization failed: {e}")
            return False

    def convert(
        self,
        pdf_path: str,
        output_docx_path: str,
    ) -> ConversionResult:
        """Executes in-process PDF to DOCX conversion via pdf2docx."""
        if not os.path.exists(pdf_path):
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error=f"Source PDF file not found: {pdf_path}",
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)
        logger.info(f"[INTERNAL CONVERTER] Starting conversion: '{pdf_path}' -> '{output_docx_path}'")

        timing = ConversionTiming()
        t_start = time.perf_counter()

        try:
            cv = Converter(pdf_path)
            cv.convert(output_docx_path, start=0, end=None)
            cv.close()

            # If presentation detected and enabled, fit slide layout
            if self.fit_presentation and self.is_presentation_pdf(pdf_path):
                self.fit_presentation_layout(output_docx_path)

            t_end = time.perf_counter()
            duration = t_end - t_start
            timing.conversion_sec = round(duration, 3)
            timing.total_sec = round(duration, 3)
            timing.log_timing_summary(self.name)

            if not os.path.exists(output_docx_path) or os.path.getsize(output_docx_path) == 0:
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error="Internal converter created empty or nonexistent file.",
                )

            with open(output_docx_path, "rb") as f:
                docx_bytes = f.read()

            return ConversionResult(
                success=True,
                docx_path=output_docx_path,
                docx_bytes=docx_bytes,
                provider=self.name,
                timing=timing,
            )

        except Exception as e:
            logger.error(f"[INTERNAL CONVERTER] Failed converting '{pdf_path}': {e}")
            t_end = time.perf_counter()
            timing.total_sec = round(t_end - t_start, 3)
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                timing=timing,
                error=str(e),
            )
