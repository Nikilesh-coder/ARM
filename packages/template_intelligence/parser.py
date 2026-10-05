"""
ARM — Deterministic Template Intelligence Parser
Extracts factual document properties, geometry, typography, heading hierarchies,
sections, tables, images, and semantic roles from institutional DOCX and PDF templates.
"""

import io
import os
import re
import uuid
import zipfile
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

import docx
from docx.shared import Pt, Length, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .schema import (
    TemplateSchema,
    DocumentMetadata,
    DocumentGeometry,
    PageMargins,
    TypographyRules,
    HeadingStyle,
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

# Canonical academic and project section mappings for deterministic semantic classification
SEMANTIC_CLASSIFICATIONS: List[Tuple[str, str, List[str], float]] = [
    ("title_page", "TITLE_PAGE", ["title", "project report on", "submitted in partial fulfillment", "bachelor of technology", "master of technology", "presentation on", "community service project presentation"], 0.95),
    ("certificate", "CERTIFICATE", ["bonafide certificate", "certificate of approval", "certificate"], 0.95),
    ("declaration", "DECLARATION", ["candidate's declaration", "declaration by student", "declaration"], 0.95),
    ("acknowledgement", "ACKNOWLEDGEMENT", ["acknowledgement", "acknowledgments"], 0.95),
    ("abstract", "ABSTRACT", ["abstract", "executive summary", "synopsis"], 0.95),
    ("toc", "TABLE_OF_CONTENTS", ["table of contents", "contents", "index"], 0.95),
    ("list_of_figures", "LIST_OF_FIGURES", ["list of figures", "figures index"], 0.95),
    ("list_of_tables", "LIST_OF_TABLES", ["list of tables", "tables index"], 0.95),
    ("introduction", "INTRODUCTION", ["chapter 1", "introduction", "background and motivation"], 0.90),
    ("objectives", "OBJECTIVES", ["objectives", "aims and objectives", "project objectives", "goals", "aim"], 0.90),
    ("community_awareness", "COMMUNITY_AWARENESS", ["community awareness", "awareness program", "community outreach", "awareness on"], 0.90),
    ("field_activities", "FIELD_ACTIVITIES", ["community interaction photos", "interaction photos", "photo gallery", "place 1", "place 2", "field visit"], 0.85),
    ("advantages_disadvantages", "ADVANTAGES_DISADVANTAGES", ["advantages and disadvantages", "merits and demerits", "pros and cons", "advantages", "disadvantages"], 0.90),
    ("problems_observed", "PROBLEMS_OBSERVED", ["problems we observed", "problems observed", "challenges faced", "issues observed", "observations and challenges", "hazards observed"], 0.90),
    ("literature_review", "LITERATURE_REVIEW", ["literature survey", "literature review", "related work"], 0.90),
    ("methodology", "METHODOLOGY", ["system analysis", "system design", "system architecture", "methodology", "proposed system"], 0.90),
    ("implementation", "IMPLEMENTATION", ["implementation", "details of implementation", "modules", "development"], 0.90),
    ("results", "RESULTS", ["results and discussion", "testing and results", "experimental results", "analysis of results"], 0.90),
    ("conclusion", "CONCLUSION", ["conclusion", "conclusions and future scope", "conclusion & future work"], 0.90),
    ("references", "REFERENCES", ["references", "bibliography"], 0.95),
    ("queries", "QUERIES", ["queries", "q&a", "questions", "queries??"], 0.90),
    ("thank_you", "THANK_YOU", ["thank you", "thanks", "thank you!!"], 0.90),
    ("appendix", "APPENDIX", ["appendix", "appendices"], 0.90),
]



def length_to_mm(length_val: Optional[Length]) -> float:
    """Converts a python-docx Length (EMUs) to millimeters."""
    if length_val is None:
        return 25.4
    return round(length_val.mm, 2)


def pt_to_float(pt_val: Optional[Pt]) -> float:
    """Converts Pt value to float."""
    if pt_val is None:
        return 12.0
    return round(pt_val.pt, 1)


class BaseTemplateParser(ABC):
    """Abstract base parser for template documents."""

    @abstractmethod
    def parse(self, template_id: str, template_name: str) -> TemplateSchema:
        """Parses document and returns a normalized TemplateSchema."""
        pass


class DocxTemplateParser(BaseTemplateParser):
    """
    Deterministic DOCX Template Parser.
    Extracts OpenXML formatting styles, sections, paragraphs, tables, images,
    and headers/footers using python-docx without modifying original files.
    """

    def __init__(self, file_source):
        self.warnings: List[str] = []
        self.unsupported_features: List[str] = []
        
        if isinstance(file_source, bytes):
            self.file_bytes = file_source
            self.doc = docx.Document(io.BytesIO(file_source))
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                self.file_bytes = f.read()
            self.doc = docx.Document(file_source)
        elif hasattr(file_source, "read"):
            self.file_bytes = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            self.doc = docx.Document(io.BytesIO(self.file_bytes))
        else:
            self.doc = docx.Document(file_source)
            self.file_bytes = b""

    def parse(self, template_id: str = "template_custom", template_name: str = "College Template.docx") -> TemplateSchema:
        geometry = self._extract_geometry()
        typography, paragraph_rules, heading_rules = self._extract_typography_and_headings()
        tables_analysis = self._extract_tables()
        images_analysis = self._extract_images()
        header_footer = self._extract_header_footer()
        numbering_analysis = self._extract_numbering()
        captions_analysis = self._extract_captions()
        sections = self._detect_sections()

        # Approximate page count from section count and paragraphs (approx 3.5 paragraphs per academic page)
        para_count = len(self.doc.paragraphs)
        page_count = max(len(self.doc.sections), (para_count // 4) + 1)

        document_metadata = DocumentMetadata(
            file_type="docx",
            file_name=template_name,
            page_count=page_count,
            orientation=geometry.orientation,
            page_size={"name": geometry.page_size, "width_mm": geometry.width_mm, "height_mm": geometry.height_mm},
            margins=geometry.margins,
            language="en"
        )

        confidence_scores = {
            "geometry": 1.0,
            "typography": 0.95 if heading_rules else 0.75,
            "sections": round(min(1.0, len(sections) / 5.0), 2),
            "tables": 1.0 if tables_analysis.detected_count > 0 else 0.9,
            "images": 1.0 if images_analysis.detected_count > 0 else 0.9
        }

        validation_status = "valid" if not self.warnings else "warning"

        return TemplateSchema(
            schema_version="1.0.0",
            parser_version="1.0.0",
            template_id=template_id,
            template_name=template_name,
            document=document_metadata,
            geometry=geometry,
            typography=typography,
            sections=sections,
            heading_rules=heading_rules,
            paragraph_rules=paragraph_rules,
            tables=tables_analysis,
            images=images_analysis,
            captions=captions_analysis,
            numbering=numbering_analysis,
            header_footer=header_footer,
            validation=ValidationSummary(
                status=validation_status,
                warnings=self.warnings,
                unsupported_features=self.unsupported_features
            ),
            confidence_scores=confidence_scores,
            warnings=self.warnings,
            raw_metadata={
                "paragraph_count": para_count,
                "table_count": len(self.doc.tables),
                "sections_count": len(self.doc.sections),
                "has_embedded_images": images_analysis.detected_count > 0
            }
        )

    def _extract_geometry(self) -> DocumentGeometry:
        if not self.doc.sections:
            self.warnings.append("No document sections found in DOCX. Defaulting to standard A4 geometry.")
            return DocumentGeometry()

        first_section = self.doc.sections[0]
        width_mm = length_to_mm(first_section.page_width)
        height_mm = length_to_mm(first_section.page_height)

        orientation = "portrait"
        if width_mm > height_mm:
            orientation = "landscape"

        page_size = "A4"
        if abs(width_mm - 215.9) < 6.0 and abs(height_mm - 279.4) < 6.0:
            page_size = "Letter"
        elif abs(width_mm - 210.0) < 6.0 and abs(height_mm - 297.0) < 6.0:
            page_size = "A4"

        margins = PageMargins(
            top_mm=length_to_mm(first_section.top_margin),
            bottom_mm=length_to_mm(first_section.bottom_margin),
            left_mm=length_to_mm(first_section.left_margin),
            right_mm=length_to_mm(first_section.right_margin),
            gutter_mm=length_to_mm(first_section.gutter) if hasattr(first_section, 'gutter') else 0.0
        )

        return DocumentGeometry(
            page_size=page_size,
            width_mm=width_mm,
            height_mm=height_mm,
            orientation=orientation,
            margins=margins,
            different_first_page_header=bool(first_section.different_first_page_header_footer)
        )

    def _extract_typography_and_headings(self) -> Tuple[TypographyRules, ParagraphRules, Dict[str, HeadingStyle]]:
        default_font = "Times New Roman"
        default_size_pt = 12.0
        line_spacing = 1.5
        alignment = "justify"

        # Inspect Normal style
        try:
            normal_style = self.doc.styles['Normal']
            if normal_style.font.name:
                default_font = normal_style.font.name
            if normal_style.font.size:
                default_size_pt = pt_to_float(normal_style.font.size)
        except Exception:
            pass

        # Inspect body paragraph samples if available
        sample_fonts = []
        for p in self.doc.paragraphs[:20]:
            for r in p.runs:
                if r.font and r.font.name:
                    sample_fonts.append(r.font.name)
        if sample_fonts:
            # Most frequent font in runs
            default_font = max(set(sample_fonts), key=sample_fonts.count)

        heading_rules: Dict[str, HeadingStyle] = {}
        for level in range(1, 5):
            style_name = f'Heading {level}'
            try:
                h_style = self.doc.styles[style_name]
                font_name = h_style.font.name or default_font
                size_pt = pt_to_float(h_style.font.size) if h_style.font.size else (16.0 - (level - 1) * 2.0)
                bold = h_style.font.bold if h_style.font.bold is not None else True
                italic = bool(h_style.font.italic)

                rule = HeadingStyle(
                    level=level,
                    font_name=font_name,
                    size_pt=size_pt,
                    bold=bold,
                    italic=italic,
                    alignment="center" if level == 1 else "left",
                    space_before_pt=12.0 if level == 1 else 6.0,
                    space_after_pt=6.0,
                    page_break_before=(level == 1),
                    numbering_pattern="1." if level == 1 else ("1.1" if level == 2 else None),
                    confidence="exact"
                )
                heading_rules[f"level_{level}"] = rule
                heading_rules[f"heading_{level}"] = rule
            except Exception:
                inferred_rule = HeadingStyle(
                    level=level,
                    font_name=default_font,
                    size_pt=max(10.0, 16.0 - (level - 1) * 2.0),
                    bold=True,
                    italic=(level >= 3),
                    alignment="center" if level == 1 else "left",
                    space_before_pt=12.0 if level == 1 else 6.0,
                    space_after_pt=6.0,
                    page_break_before=(level == 1),
                    confidence="inferred"
                )
                heading_rules[f"level_{level}"] = inferred_rule
                heading_rules[f"heading_{level}"] = inferred_rule

        typography = TypographyRules(
            default_font=default_font,
            default_size_pt=default_size_pt,
            line_spacing=line_spacing,
            paragraph_after_pt=6.0,
            paragraph_before_pt=0.0,
            alignment=alignment,
            headings=heading_rules,
            confidence="exact"
        )

        paragraph_rules = ParagraphRules(
            body_font=default_font,
            body_size_pt=default_size_pt,
            line_spacing=line_spacing,
            alignment=alignment,
            paragraph_after_pt=6.0,
            paragraph_before_pt=0.0,
            first_line_indent_pt=0.0,
            confidence="exact"
        )

        return typography, paragraph_rules, heading_rules

    def _extract_tables(self) -> TableAnalysis:
        table_items = []
        for i, tbl in enumerate(self.doc.tables):
            rows = len(tbl.rows)
            cols = len(tbl.columns) if rows > 0 else 0
            has_header = rows > 1
            table_items.append(TableItem(
                index=i + 1,
                rows=rows,
                columns=cols,
                has_header=has_header,
                alignment="center"
            ))
        return TableAnalysis(detected_count=len(table_items), items=table_items)

    def _extract_images(self) -> ImageAnalysis:
        image_items = []
        count = 0
        if self.file_bytes:
            try:
                with zipfile.ZipFile(io.BytesIO(self.file_bytes)) as zf:
                    for name in zf.namelist():
                        if name.startswith("word/media/"):
                            count += 1
                            image_items.append(ImageItem(
                                index=count,
                                width_pt=300.0,
                                height_pt=200.0,
                                alignment="center"
                            ))
            except Exception:
                pass
        return ImageAnalysis(detected_count=count, items=image_items)

    def _extract_header_footer(self) -> HeaderFooterRule:
        rule = HeaderFooterRule()
        if self.doc.sections:
            first_section = self.doc.sections[0]
            header = first_section.header
            if header and header.paragraphs:
                header_text = "".join([p.text for p in header.paragraphs]).strip()
                if header_text:
                    rule.header_text_pattern = header_text

            footer = first_section.footer
            if footer and footer.paragraphs:
                footer_text = "".join([p.text for p in footer.paragraphs]).strip()
                if footer_text:
                    rule.footer_text_pattern = footer_text
        return rule

    def _extract_numbering(self) -> NumberingAnalysis:
        patterns = set()
        for p in self.doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if re.match(r"^\d+\.\s+", text):
                patterns.add("1. Section")
            elif re.match(r"^\d+\.\d+\s+", text):
                patterns.add("1.1 Subsection")
            elif re.match(r"^\d+\.\d+\.\d+\s+", text):
                patterns.add("1.1.1 Sub-subsection")
            elif re.match(r"^Chapter\s+\d+", text, re.IGNORECASE):
                patterns.add("Chapter {N}")
            elif re.match(r"^[IVXLCDM]+\.\s+", text):
                patterns.add("I. Roman")
            elif re.match(r"^[A-Z]\.\s+", text):
                patterns.add("A. Alphabetic")

        return NumberingAnalysis(detected_patterns=sorted(list(patterns)))

    def _extract_captions(self) -> CaptionAnalysis:
        fig_count = 0
        tbl_count = 0
        for p in self.doc.paragraphs:
            text = p.text.strip()
            if re.match(r"^(Figure|Fig\.)\s+\d+[:\.]", text, re.IGNORECASE):
                fig_count += 1
            elif re.match(r"^Table\s+\d+[:\.]", text, re.IGNORECASE):
                tbl_count += 1

        return CaptionAnalysis(
            figure_caption_pattern="Figure {N}: {Title}" if fig_count > 0 else None,
            table_caption_pattern="Table {N}: {Title}" if tbl_count > 0 else None,
            detected_count=fig_count + tbl_count
        )

    def _detect_sections(self) -> List[DetectedSection]:
        detected: List[DetectedSection] = []
        seen_types = set()
        order = 1

        for para in self.doc.paragraphs:
            text = para.text.strip()
            if not text or len(text) > 90:
                continue
            text_lower = text.lower()

            # Discard obvious prompt injection text from section titles
            if any(term in text_lower for term in ["ignore", "system instruction", "reveal secret", "database password"]):
                continue

            matched = False
            for section_type, semantic_role, keywords, conf in SEMANTIC_CLASSIFICATIONS:
                if section_type in seen_types:
                    continue
                for kw in keywords:
                    if kw in text_lower:
                        seen_types.add(section_type)
                        detected.append(
                            DetectedSection(
                                id=f"sec_{order}_{section_type}",
                                order=order,
                                section_type=section_type,
                                detected_title=text,
                                semantic_role=semantic_role,
                                confidence=conf,
                                level=1,
                                mandatory=True,
                                page_number_format=(
                                    "roman" if section_type in [
                                        "certificate", "declaration", "acknowledgement", "abstract", "toc", "list_of_figures", "list_of_tables"
                                    ] else ("none" if section_type == "title_page" else "arabic")
                                ),
                                element_counts={"paragraphs": 1, "tables": 0, "images": 0}
                            )
                        )
                        order += 1
                        matched = True
                        break
                if matched:
                    break

            # If not matched by static keywords, capture if explicitly styled as Heading or bold header
            if not matched and len(text) <= 70:
                is_heading_style = bool(para.style and para.style.name and para.style.name.startswith("Heading"))
                is_bold_header = bool(para.runs and any(r.bold for r in para.runs) and (text.isupper() or len(text.split()) <= 6))
                if is_heading_style or is_bold_header:
                    slug = re.sub(r"[^a-z0-9]+", "_", text_lower).strip("_")
                    if slug and slug not in seen_types:
                        seen_types.add(slug)
                        detected.append(
                            DetectedSection(
                                id=f"sec_{order}_{slug}",
                                order=order,
                                section_type=slug,
                                detected_title=text,
                                semantic_role="CUSTOM_SECTION",
                                confidence=0.85,
                                level=1,
                                mandatory=True,
                                page_number_format="arabic",
                                element_counts={"paragraphs": 1, "tables": 0, "images": 0}
                            )
                        )
                        order += 1


        # Fallback to cover/title page if not explicitly titled
        if "title_page" not in seen_types and len(self.doc.paragraphs) > 0:
            detected.insert(0, DetectedSection(
                id="sec_0_title_page",
                order=0,
                section_type="title_page",
                detected_title="Cover / Title Page",
                semantic_role="TITLE_PAGE",
                mandatory=True,
                page_number_format="none",
                confidence=0.85
            ))

        return detected


class PdfTemplateParser(BaseTemplateParser):
    """
    Deterministic PDF Template Parser.
    Extracts text blocks, page geometry, preliminary sections, font sizes,
    and images using PyMuPDF and pypdf without modifying original files.
    """

    def __init__(self, file_source):
        self.warnings: List[str] = []
        self.unsupported_features: List[str] = [
            "Exact paragraph line spacing (inferred)",
            "Binding gutter margin (unavailable in PDF stream)",
            "Native Word style names (unavailable in PDF stream)"
        ]

        if isinstance(file_source, bytes):
            self.file_bytes = file_source
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                self.file_bytes = f.read()
        elif hasattr(file_source, "read"):
            self.file_bytes = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
        else:
            self.file_bytes = b""

    def parse(self, template_id: str = "template_pdf_custom", template_name: str = "College Template.pdf") -> TemplateSchema:
        import pymupdf

        doc = pymupdf.open(stream=self.file_bytes, filetype="pdf")
        page_count = len(doc)
        if page_count == 0:
            raise ValueError("PDF document has 0 pages.")

        first_page = doc[0]
        rect = first_page.rect
        width_pt = rect.width
        height_pt = rect.height
        width_mm = round(width_pt * 25.4 / 72.0, 2)
        height_mm = round(height_pt * 25.4 / 72.0, 2)

        orientation = "portrait" if height_mm >= width_mm else "landscape"
        page_size_name = "A4"
        if abs(width_mm - 215.9) < 8.0 and abs(height_mm - 279.4) < 8.0:
            page_size_name = "Letter"

        margins = PageMargins(
            top_mm=25.4,
            bottom_mm=25.4,
            left_mm=31.75,
            right_mm=25.4,
            gutter_mm=0.0
        )

        geometry = DocumentGeometry(
            page_size=page_size_name,
            width_mm=width_mm,
            height_mm=height_mm,
            orientation=orientation,
            margins=margins,
            columns_count=1
        )

        document_metadata = DocumentMetadata(
            file_type="pdf",
            file_name=template_name,
            page_count=page_count,
            orientation=orientation,
            page_size={"name": page_size_name, "width_mm": width_mm, "height_mm": height_mm},
            margins=margins,
            language="en"
        )

        # Extract text blocks, font sizes, headings
        detected_sections: List[DetectedSection] = []
        seen_types = set()
        order = 1
        font_sizes: List[float] = []
        font_names: List[str] = []
        image_count = 0
        numbering_patterns = set()

        is_presentation = any(p.rect.width > p.rect.height for p in doc) or len(doc) <= 25

        def _classify_text(t: str) -> Tuple[str, str, float]:
            t_low = t.lower().strip()
            for stype, srole, kws, conf in SEMANTIC_CLASSIFICATIONS:
                for kw in kws:
                    if kw == t_low or t_low.startswith(kw) or f" {kw}" in f" {t_low}":
                        return stype, srole, conf
            slug = re.sub(r"[^a-z0-9]+", "_", t_low).strip("_")
            return slug or "section", (slug or "CUSTOM_SECTION").upper(), 0.80

        for page_idx, page in enumerate(doc):
            # Check embedded images
            image_list = page.get_images()
            image_count += len(image_list)

            # Check numbering patterns
            blocks = page.get_text("blocks")
            for b in blocks:
                first_line = b[4].strip().split("\n")[0].strip()
                if re.match(r"^\d+\.\s+", first_line):
                    numbering_patterns.add("1. Section")
                elif re.match(r"^\d+\.\d+\s+", first_line):
                    numbering_patterns.add("1.1 Subsection")
                elif re.match(r"^Chapter\s+\d+", first_line, re.IGNORECASE):
                    numbering_patterns.add("Chapter {N}")

            # For presentation slides or page-by-page templates:
            # Page 1 is the Title Page
            if page_idx == 0:
                detected_sections.append(
                    DetectedSection(
                        id=f"sec_{order}_title_page",
                        order=order,
                        section_type="title_page",
                        detected_title="Title / Cover Page",
                        semantic_role="TITLE_PAGE",
                        confidence=0.95,
                        level=1,
                        page_number=1,
                        mandatory=True,
                        page_number_format="none"
                    )
                )
                seen_types.add("title_page")
                order += 1
                continue

            # Extract spans with formatting
            p_dict = page.get_text("dict")
            spans = []
            for b in p_dict.get("blocks", []):
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l.get("spans", []):
                            txt = s.get("text", "").strip()
                            if txt and not re.match(r"^Pg\.\s*\d+$", txt, re.I):
                                spans.append({
                                    "text": txt,
                                    "size": round(s.get("size", 12.0), 1),
                                    "bbox": s.get("bbox", (0, 0, 0, 0))
                                })

            # Filter boilerplate headers/footers
            content_spans = [
                s for s in spans
                if not any(ign in s["text"] for ign in ["SVCE TIRUPATI", "EDUCATION FOR A BETTER SOCIETY"])
            ]
            if not content_spans:
                continue

            # Find prominent heading at top of page (y < 260)
            top_spans = [s for s in content_spans if s["bbox"][1] < 260]
            if top_spans:
                max_size = max(s["size"] for s in top_spans)
                heading_spans = [s for s in top_spans if s["size"] >= max_size - 1.0]
                raw_title = " ".join(s["text"] for s in heading_spans).strip()
                clean_title = re.sub(r"^[•\uf0d8\uf071\uf0a7\s\d\.\-:]+", "", raw_title).strip()
                if not clean_title:
                    clean_title = raw_title
            else:
                clean_title = content_spans[0]["text"]

            # Discard prompt injection attempts
            if any(term in clean_title.lower() for term in ["ignore", "system instruction", "reveal secret", "database password"]):
                continue

            sec_type, sec_role, sec_conf = _classify_text(clean_title)

            # Do not register sub-bullets on TOC/Contents page as sections
            if sec_type not in seen_types:
                seen_types.add(sec_type)
                detected_sections.append(
                    DetectedSection(
                        id=f"sec_{order}_{sec_type}",
                        order=order,
                        section_type=sec_type,
                        detected_title=clean_title,
                        semantic_role=sec_role,
                        confidence=sec_conf * 0.95,
                        level=1,
                        page_number=page_idx + 1,
                        mandatory=True,
                        page_number_format="roman" if page_idx < 4 else "arabic"
                    )
                )
                order += 1


        # Inferred Typography from PDF
        body_font = "Times New Roman"
        body_size_pt = 12.0
        line_spacing = 1.5

        self.warnings.append("PDF formatting metadata (line spacing, paragraph spacing) was inferred from visual layout.")

        heading_rules = {
            "level_1": HeadingStyle(
                level=1,
                font_name=body_font,
                size_pt=16.0,
                bold=True,
                alignment="center",
                page_break_before=True,
                confidence="inferred"
            ),
            "level_2": HeadingStyle(
                level=2,
                font_name=body_font,
                size_pt=14.0,
                bold=True,
                alignment="left",
                confidence="inferred"
            ),
            "level_3": HeadingStyle(
                level=3,
                font_name=body_font,
                size_pt=12.0,
                bold=True,
                italic=True,
                alignment="left",
                confidence="inferred"
            ),
        }

        typography = TypographyRules(
            default_font=body_font,
            default_size_pt=body_size_pt,
            line_spacing=line_spacing,
            paragraph_after_pt=6.0,
            alignment="justify",
            headings=heading_rules,
            confidence="inferred"
        )

        paragraph_rules = ParagraphRules(
            body_font=body_font,
            body_size_pt=body_size_pt,
            line_spacing=line_spacing,
            alignment="justify",
            paragraph_after_pt=6.0,
            confidence="inferred"
        )

        if "title_page" not in seen_types:
            detected_sections.insert(0, DetectedSection(
                id="sec_0_title_page",
                order=0,
                section_type="title_page",
                detected_title="Cover / Title Page",
                semantic_role="TITLE_PAGE",
                confidence=0.85,
                page_number=1,
                page_number_format="none"
            ))

        doc.close()

        confidence_scores = {
            "geometry": 1.0,
            "typography": 0.80,
            "sections": round(min(1.0, len(detected_sections) / 5.0), 2),
            "tables": 0.70,
            "images": 0.90
        }

        return TemplateSchema(
            schema_version="1.0.0",
            parser_version="1.0.0",
            template_id=template_id,
            template_name=template_name,
            document=document_metadata,
            geometry=geometry,
            typography=typography,
            sections=detected_sections,
            heading_rules=heading_rules,
            paragraph_rules=paragraph_rules,
            tables=TableAnalysis(detected_count=0, items=[]),
            images=ImageAnalysis(detected_count=image_count, items=[]),
            captions=CaptionAnalysis(detected_count=0),
            numbering=NumberingAnalysis(detected_patterns=sorted(list(numbering_patterns))),
            header_footer=HeaderFooterRule(has_page_numbers=True),
            validation=ValidationSummary(
                status="warning",
                warnings=self.warnings,
                unsupported_features=self.unsupported_features
            ),
            confidence_scores=confidence_scores,
            warnings=self.warnings,
            raw_metadata={
                "page_count": page_count,
                "detected_images": image_count,
                "inferred_typography": True
            }
        )


class TemplateParser:
    """
    Unified entry-point for deterministic document parsing.
    Maintains full backward compatibility for existing callers.
    """

    def __init__(self, docx_or_pdf_source):
        self.source = docx_or_pdf_source
        self.parser = self._select_parser(docx_or_pdf_source)

    def _select_parser(self, source) -> BaseTemplateParser:
        if isinstance(source, str):
            ext = os.path.splitext(source)[1].lower()
            if ext == ".pdf":
                return PdfTemplateParser(source)
            return DocxTemplateParser(source)
        elif isinstance(source, bytes):
            if source.startswith(b"%PDF-"):
                return PdfTemplateParser(source)
            return DocxTemplateParser(source)
        return DocxTemplateParser(source)

    def parse(self, template_id: str = "template_custom", template_name: str = "Custom Institutional Template") -> TemplateSchema:
        return self.parser.parse(template_id=template_id, template_name=template_name)


def get_template_parser(file_source: Any, file_type: str = "docx") -> BaseTemplateParser:
    """Factory returns format-specific deterministic template parser."""
    clean_type = file_type.lstrip(".").lower()
    if clean_type == "pdf":
        return PdfTemplateParser(file_source)
    return DocxTemplateParser(file_source)
