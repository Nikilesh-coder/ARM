"""
Template Intelligence Package
Deterministic DOCX and PDF document parsers and normalized schema generator.
"""

from .schema import (
    TemplateSchema,
    DocumentMetadata,
    DocumentGeometry,
    PageMargins,
    TypographyRules,
    HeadingStyle,
    HeadingRule,
    ParagraphRules,
    DetectedSection,
    HeaderFooterRule,
    TableAnalysis,
    TableItem,
    ImageAnalysis,
    ImageItem,
    CaptionAnalysis,
    NumberingAnalysis,
    ValidationSummary,
)
from .parser import (
    TemplateParser,
    BaseTemplateParser,
    DocxTemplateParser,
    PdfTemplateParser,
    get_template_parser,
)

from .validator import TemplateReviewValidator, CANONICAL_SEMANTIC_ROLES

__all__ = [
    "TemplateSchema",
    "DocumentMetadata",
    "DocumentGeometry",
    "PageMargins",
    "TypographyRules",
    "HeadingStyle",
    "HeadingRule",
    "ParagraphRules",
    "DetectedSection",
    "HeaderFooterRule",
    "TableAnalysis",
    "TableItem",
    "ImageAnalysis",
    "ImageItem",
    "CaptionAnalysis",
    "NumberingAnalysis",
    "ValidationSummary",
    "TemplateParser",
    "BaseTemplateParser",
    "DocxTemplateParser",
    "PdfTemplateParser",
    "get_template_parser",
    "TemplateReviewValidator",
    "CANONICAL_SEMANTIC_ROLES",
]
