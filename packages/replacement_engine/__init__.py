"""
ARM Stage 10 - Template Replacement Engine Package
Exports base interfaces, DOCX replacement implementation, validator, and data models.
"""

from packages.replacement_engine.base import (
    BaseReplacementEngine,
    ReplacementState,
    FieldReplacementAudit,
    ReplacementErrorDetail,
    ReplacementResult,
)
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.pdf_engine import (
    PdfTemplateReplacementEngine,
    PdfTemplateAnalyzer,
    PdfAnalysisResult,
)
from packages.replacement_engine.validator import ReplacementValidator

__all__ = [
    "BaseReplacementEngine",
    "DocxTemplateReplacementEngine",
    "PdfTemplateReplacementEngine",
    "PdfTemplateAnalyzer",
    "PdfAnalysisResult",
    "ReplacementState",
    "FieldReplacementAudit",
    "ReplacementErrorDetail",
    "ReplacementResult",
    "ReplacementValidator",
]
