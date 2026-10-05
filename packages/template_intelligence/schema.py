"""
ARM — Template Intelligence Normalized Schema
Defines structured specifications for extracted college report templates.
Supports DOCX and PDF structural ground-truth extraction, formatting rules,
hierarchical sections, typography, page geometry, numbering, and semantic roles.
"""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PageMargins(BaseModel):
    top_mm: float = Field(default=25.4, description="Top margin in millimeters")
    bottom_mm: float = Field(default=25.4, description="Bottom margin in millimeters")
    left_mm: float = Field(default=31.75, description="Left margin in millimeters (often 1.25 in)")
    right_mm: float = Field(default=25.4, description="Right margin in millimeters")
    gutter_mm: float = Field(default=0.0, description="Binding gutter margin")


class DocumentGeometry(BaseModel):
    page_size: str = Field(default="A4", description="A4, Letter, etc.")
    width_mm: float = Field(default=210.0)
    height_mm: float = Field(default=297.0)
    orientation: str = Field(default="portrait", description="portrait or landscape")
    margins: PageMargins = Field(default_factory=PageMargins)
    columns_count: int = Field(default=1)
    different_first_page_header: bool = Field(default=True)


class DocumentMetadata(BaseModel):
    file_type: str = Field(default="docx", description="'docx' or 'pdf'")
    file_name: str = Field(default="template")
    page_count: int = Field(default=1)
    orientation: str = Field(default="portrait")
    page_size: Dict[str, Any] = Field(default_factory=lambda: {"name": "A4", "width_mm": 210.0, "height_mm": 297.0})
    margins: PageMargins = Field(default_factory=PageMargins)
    language: str = Field(default="en")


class HeadingStyle(BaseModel):
    level: int = Field(description="Heading level 1, 2, 3...")
    font_name: str = Field(default="Times New Roman")
    size_pt: float = Field(default=14.0)
    bold: bool = Field(default=True)
    italic: bool = Field(default=False)
    all_caps: bool = Field(default=False)
    alignment: str = Field(default="left", description="left, center, right, justify")
    space_before_pt: float = Field(default=12.0)
    space_after_pt: float = Field(default=6.0)
    page_break_before: bool = Field(default=False)
    numbering_pattern: Optional[str] = Field(default=None, description="e.g. '1.', '1.1', 'CHAPTER {N}'")
    confidence: str = Field(default="exact", description="'exact', 'inferred', 'unavailable'")


# Alias HeadingRule to HeadingStyle for backward compatibility
HeadingRule = HeadingStyle


class TypographyRules(BaseModel):
    default_font: str = Field(default="Times New Roman")
    default_size_pt: float = Field(default=12.0)
    line_spacing: float = Field(default=1.5, description="1.0, 1.15, 1.5, 2.0")
    paragraph_after_pt: float = Field(default=6.0)
    paragraph_before_pt: float = Field(default=0.0)
    alignment: str = Field(default="justify")
    headings: Dict[str, HeadingStyle] = Field(default_factory=dict)
    confidence: str = Field(default="exact")


class ParagraphRules(BaseModel):
    body_font: str = Field(default="Times New Roman")
    body_size_pt: float = Field(default=12.0)
    line_spacing: float = Field(default=1.5)
    alignment: str = Field(default="justify")
    paragraph_after_pt: float = Field(default=6.0)
    paragraph_before_pt: float = Field(default=0.0)
    first_line_indent_pt: float = Field(default=0.0)
    confidence: str = Field(default="exact")


class DetectedSection(BaseModel):
    id: str = Field(default_factory=lambda: f"sec_{uuid.uuid4().hex[:8]}")
    order: int = Field(default=1)
    section_type: str = Field(
        default="chapter",
        description="title_page, certificate, declaration, acknowledgement, abstract, toc, chapter, conclusion, references, appendix, etc."
    )
    detected_title: str
    semantic_role: str = Field(default="CUSTOM_SECTION", description="Candidate semantic role with confidence")
    confidence: float = Field(default=0.8, description="0.0 to 1.0 confidence in semantic classification")
    level: int = Field(default=1)
    mandatory: bool = True
    page_number_format: Optional[str] = Field(default="arabic", description="roman, arabic, none")
    start_page_offset: Optional[int] = None
    page_number: Optional[int] = None
    element_counts: Dict[str, int] = Field(default_factory=lambda: {"paragraphs": 0, "tables": 0, "images": 0})


class HeaderFooterRule(BaseModel):
    header_text_pattern: Optional[str] = Field(default=None)
    header_alignment: str = "right"
    has_header_logo: bool = False
    footer_text_pattern: Optional[str] = Field(default=None)
    footer_page_number_alignment: str = "center"
    page_number_style: str = "arabic"  # arabic, roman
    has_page_numbers: bool = True


class TableItem(BaseModel):
    index: int
    rows: int
    columns: int
    has_header: bool = True
    alignment: str = "center"


class TableAnalysis(BaseModel):
    detected_count: int = Field(default=0)
    items: List[TableItem] = Field(default_factory=list)


class ImageItem(BaseModel):
    index: int
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    alignment: str = "center"
    caption: Optional[str] = None


class ImageAnalysis(BaseModel):
    detected_count: int = Field(default=0)
    items: List[ImageItem] = Field(default_factory=list)


class CaptionAnalysis(BaseModel):
    figure_caption_pattern: Optional[str] = Field(default=None)
    table_caption_pattern: Optional[str] = Field(default=None)
    detected_count: int = Field(default=0)


class NumberingAnalysis(BaseModel):
    detected_patterns: List[str] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    status: str = Field(default="valid", description="'valid', 'warning', 'unsupported'")
    warnings: List[str] = Field(default_factory=list)
    unsupported_features: List[str] = Field(default_factory=list)


class TemplateSchema(BaseModel):
    schema_version: str = Field(default="1.0.0", description="Semantic version of normalized template schema")
    parser_version: str = Field(default="1.0.0", description="Version of template parser engine")
    template_id: str
    template_name: str
    document: Optional[DocumentMetadata] = None
    geometry: DocumentGeometry = Field(default_factory=DocumentGeometry)
    typography: TypographyRules = Field(default_factory=TypographyRules)
    sections: List[DetectedSection] = Field(default_factory=list)
    heading_rules: Dict[str, HeadingStyle] = Field(default_factory=dict)
    paragraph_rules: ParagraphRules = Field(default_factory=ParagraphRules)
    tables: TableAnalysis = Field(default_factory=TableAnalysis)
    images: ImageAnalysis = Field(default_factory=ImageAnalysis)
    captions: CaptionAnalysis = Field(default_factory=CaptionAnalysis)
    numbering: NumberingAnalysis = Field(default_factory=NumberingAnalysis)
    header_footer: HeaderFooterRule = Field(default_factory=HeaderFooterRule)
    validation: ValidationSummary = Field(default_factory=ValidationSummary)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
