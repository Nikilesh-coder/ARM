"""
ARM Stage 9 - Deterministic Document Generation Engine
Compiles structured academic report content into an institution-styled DOCX document
based strictly on the locked TemplateSchema and optional master template file.
"""

import os
import re
import copy
from typing import List, Optional, Dict, Any, Union
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from apps.api.core.logging import get_logger
from packages.template_intelligence.schema import TemplateSchema, HeadingStyle

logger = get_logger("document.engine")


def add_page_number_field(run):
    """Inserts a dynamic Word PAGE field code into a text run."""
    try:
        fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls("w"))
        instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls("w"))
        fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls("w"))
        fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls("w"))
        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)
        run._r.append(fldChar3)
    except Exception as e:
        logger.warning(f"Could not append page number XML field: {e}")


def set_cell_shading(cell, color_hex: str = "F2F2F2"):
    """Sets background shading color for a table cell."""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(r'<w:shd %s w:fill="%s"/>' % (nsdecls("w"), color_hex))
        tcPr.append(shd)
    except Exception as e:
        logger.warning(f"Could not set cell shading: {e}")


def set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150):
    """Sets internal padding / margins for a table cell in dxa (1/20 of a pt)."""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(
            r'<w:tcMar %s>'
            r'<w:top w:w="%d" w:type="dxa"/>'
            r'<w:bottom w:w="%d" w:type="dxa"/>'
            r'<w:left w:w="%d" w:type="dxa"/>'
            r'<w:right w:w="%d" w:type="dxa"/>'
            r'</w:tcMar>' % (nsdecls("w"), top, bottom, left, right)
        )
        tcPr.append(tcMar)
    except Exception as e:
        logger.warning(f"Could not set cell margins: {e}")


class DocumentAssembler:
    """
    Deterministic document assembler.
    Enforces formatting rules from locked TemplateSchema onto verified report content.
    """

    def __init__(self, template_schema: TemplateSchema, master_template_path: Optional[str] = None):
        self.schema = template_schema
        self.master_template_path = master_template_path
        self._is_from_master = False

        if master_template_path and os.path.exists(master_template_path):
            self.doc = docx.Document(master_template_path)
            self._is_from_master = True
        else:
            default_tpl = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../.storage/templates/master_college_template.docx")
            )
            if os.path.exists(default_tpl):
                self.doc = docx.Document(default_tpl)
                self.master_template_path = default_tpl
                self._is_from_master = True
            else:
                self.doc = docx.Document()
                self._apply_geometry()
                self._apply_header_footer()

    def _apply_geometry(self):
        """Applies margins, page size, and orientation strictly from schema geometry."""
        if not self.doc.sections:
            return
        section = self.doc.sections[0]
        geom = self.schema.geometry

        # Page Dimensions
        section.page_width = Inches(geom.width_mm / 25.4)
        section.page_height = Inches(geom.height_mm / 25.4)

        # Margins
        section.top_margin = Inches(geom.margins.top_mm / 25.4)
        section.bottom_margin = Inches(geom.margins.bottom_mm / 25.4)
        section.left_margin = Inches(geom.margins.left_mm / 25.4)
        section.right_margin = Inches(geom.margins.right_mm / 25.4)

        if hasattr(section, "different_first_page_header_footer"):
            section.different_first_page_header_footer = geom.different_first_page_header

    def _apply_header_footer(self):
        """Configures header and footer based on template schema rules."""
        if not self.doc.sections:
            return
        section = self.doc.sections[0]
        hf_rule = self.schema.header_footer

        # Header configuration
        if hf_rule.header_text_pattern:
            header = section.header
            p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            p.text = ""
            run = p.add_run(hf_rule.header_text_pattern)
            run.font.name = self.schema.typography.default_font
            run.font.size = Pt(9.0)
            run.font.color.rgb = RGBColor(120, 120, 120)
            if hf_rule.header_alignment == "center":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif hf_rule.header_alignment == "left":
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Footer configuration
        if hf_rule.has_page_numbers or hf_rule.footer_text_pattern:
            footer = section.footer
            p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            p.text = ""

            if hf_rule.footer_text_pattern:
                run_txt = p.add_run(hf_rule.footer_text_pattern + "  |  ")
                run_txt.font.name = self.schema.typography.default_font
                run_txt.font.size = Pt(9.0)
                run_txt.font.color.rgb = RGBColor(120, 120, 120)

            if hf_rule.has_page_numbers:
                run_pg = p.add_run("Page ")
                run_pg.font.name = self.schema.typography.default_font
                run_pg.font.size = Pt(9.0)
                add_page_number_field(run_pg)

            if hf_rule.footer_page_number_alignment == "left":
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            elif hf_rule.footer_page_number_alignment == "right":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def replace_placeholders(self, placeholders: Dict[str, str]):
        """
        Deterministically replaces template metadata placeholders across all
        paragraphs, table cells, headers, and footers.
        """
        def _replace_in_text(text: str) -> str:
            for key, val in placeholders.items():
                if val:
                    text = text.replace(f"{{{{{key}}}}}", str(val))
                    text = text.replace(f"{{{key}}}", str(val))
            return text

        def _replace_in_paragraph(p):
            # Fast check
            full_txt = p.text
            if "{{" in full_txt or "{" in full_txt:
                for key, val in placeholders.items():
                    if val is not None:
                        pat = re.compile(re.escape(f"{{{{{key}}}}}"), re.IGNORECASE)
                        if pat.search(full_txt):
                            full_txt = pat.sub(str(val), full_txt)
                        pat2 = re.compile(re.escape(f"{{{key}}}"), re.IGNORECASE)
                        if pat2.search(full_txt):
                            full_txt = pat2.sub(str(val), full_txt)
                # If modified, reassign text preserving run 0's styling if possible
                if full_txt != p.text:
                    if p.runs:
                        font_name = p.runs[0].font.name
                        font_size = p.runs[0].font.size
                        bold = p.runs[0].bold
                        italic = p.runs[0].italic
                        color = p.runs[0].font.color.rgb if p.runs[0].font.color else None
                        p.text = full_txt
                        if p.runs:
                            p.runs[0].font.name = font_name
                            if font_size:
                                p.runs[0].font.size = font_size
                            p.runs[0].bold = bold
                            p.runs[0].italic = italic
                            if color:
                                p.runs[0].font.color.rgb = color
                    else:
                        p.text = full_txt

        # Body paragraphs
        for p in self.doc.paragraphs:
            _replace_in_paragraph(p)

        # Tables
        for table in self.doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        _replace_in_paragraph(p)

        # Headers & Footers
        for section in self.doc.sections:
            if section.header:
                for p in section.header.paragraphs:
                    _replace_in_paragraph(p)
            if section.footer:
                for p in section.footer.paragraphs:
                    _replace_in_paragraph(p)

    def replace_template_images(self, image_map: Dict[str, Any]):
        """
        Replaces template image placeholders ({{IMAGE_1}}, {{IMAGE_2}}, {{IMAGE_3}}, etc.)
        with real embedded pictures and styled figure captions.
        """
        for p in list(self.doc.paragraphs):
            full_txt = p.text
            for key, val in image_map.items():
                if not val:
                    continue
                placeholder_tag = f"{{{{{key.upper()}}}}}"
                placeholder_tag_single = f"{{{key.upper()}}}"
                if placeholder_tag.lower() in full_txt.lower() or placeholder_tag_single.lower() in full_txt.lower():
                    img_path = val
                    caption = None
                    if isinstance(val, dict):
                        img_path = val.get("storage_path") or val.get("file_path") or val.get("url")
                        caption = val.get("caption") or val.get("title")

                    if img_path and os.path.exists(str(img_path)):
                        p.text = ""
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p.paragraph_format.space_before = Pt(8.0)
                        p.paragraph_format.space_after = Pt(4.0)
                        run = p.add_run()
                        geom = self.schema.geometry
                        printable_width_in = (geom.width_mm - geom.margins.left_mm - geom.margins.right_mm) / 25.4
                        target_width = min(printable_width_in * 0.85, 5.5) if printable_width_in > 0 else 5.5
                        run.add_picture(str(img_path), width=Inches(target_width))

                        if caption:
                            cap_para = self.doc.add_paragraph()
                            cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            cap_para.paragraph_format.space_after = Pt(8.0)
                            run_cap = cap_para.add_run(str(caption))
                            run_cap.italic = True
                            run_cap.font.name = self.schema.typography.default_font
                            run_cap.font.size = Pt(9.5)

    def add_heading(
        self,
        text: str,
        level: int = 1,
        numbering_prefix: Optional[str] = None
    ) -> Any:
        """Adds a heading formatted strictly according to the template schema."""
        p = self.doc.add_paragraph()
        style_key = f"heading_{level}"

        # Resolve heading rule from typography.headings or heading_rules
        heading_rule: Optional[HeadingStyle] = (
            self.schema.heading_rules.get(style_key)
            or self.schema.typography.headings.get(style_key)
        )

        display_text = text
        if numbering_prefix and not text.startswith(numbering_prefix):
            display_text = f"{numbering_prefix} {text}"

        if heading_rule and heading_rule.all_caps:
            display_text = display_text.upper()

        run = p.add_run(display_text)
        run.bold = heading_rule.bold if heading_rule else True
        run.italic = heading_rule.italic if heading_rule else False
        run.font.name = heading_rule.font_name if heading_rule else self.schema.typography.default_font
        run.font.size = Pt(heading_rule.size_pt if heading_rule else (16.0 if level == 1 else 13.0))

        # Paragraph alignment & spacing
        if heading_rule:
            if heading_rule.alignment == "center":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif heading_rule.alignment == "right":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif heading_rule.alignment == "justify":
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            p.paragraph_format.space_before = Pt(heading_rule.space_before_pt)
            p.paragraph_format.space_after = Pt(heading_rule.space_after_pt)

            if heading_rule.page_break_before:
                p.paragraph_format.page_break_before = True
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(12.0)
            p.paragraph_format.space_after = Pt(6.0)

        # Keep heading with next paragraph to avoid orphan headings
        p.paragraph_format.keep_with_next = True
        return p

    def add_body_paragraph(self, text: str, bold_prefix: Optional[str] = None) -> Any:
        """Adds standard body text adhering to default font, size, line spacing, and alignment."""
        p = self.doc.add_paragraph()

        font_name = self.schema.typography.default_font
        if (
            self.schema.paragraph_rules
            and self.schema.paragraph_rules.body_font
            and self.schema.paragraph_rules.body_font != "Times New Roman"
        ):
            font_name = self.schema.paragraph_rules.body_font

        font_size = self.schema.typography.default_size_pt
        if (
            self.schema.paragraph_rules
            and self.schema.paragraph_rules.body_size_pt
            and self.schema.paragraph_rules.body_size_pt != 12.0
        ):
            font_size = self.schema.paragraph_rules.body_size_pt

        if bold_prefix:
            run_pfx = p.add_run(bold_prefix)
            run_pfx.bold = True
            run_pfx.font.name = font_name
            run_pfx.font.size = Pt(font_size)

        run = p.add_run(text)
        run.font.name = font_name
        run.font.size = Pt(font_size)

        # Apply paragraph rules
        line_spacing = self.schema.paragraph_rules.line_spacing or self.schema.typography.line_spacing
        p.paragraph_format.line_spacing = line_spacing

        space_after = self.schema.paragraph_rules.paragraph_after_pt or self.schema.typography.paragraph_after_pt
        p.paragraph_format.space_after = Pt(space_after)

        alignment = self.schema.paragraph_rules.alignment or self.schema.typography.alignment
        if alignment == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif alignment == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif alignment == "right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        if self.schema.paragraph_rules.first_line_indent_pt > 0:
            p.paragraph_format.first_line_indent = Pt(self.schema.paragraph_rules.first_line_indent_pt)

        return p

    def add_bullet_list(self, items: List[str]):
        """Adds bullet list items with consistent indentation and template typography."""
        font_name = self.schema.paragraph_rules.body_font or self.schema.typography.default_font
        font_size = self.schema.paragraph_rules.body_size_pt or self.schema.typography.default_size_pt

        for item in items:
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_after = Pt(3.0)
            p.paragraph_format.line_spacing = 1.15

            run_bullet = p.add_run("•  ")
            run_bullet.bold = True
            run_bullet.font.name = font_name
            run_bullet.font.size = Pt(font_size)

            run_text = p.add_run(item)
            run_text.font.name = font_name
            run_text.font.size = Pt(font_size)

    def add_numbered_list(self, items: List[str]):
        """Adds numbered list items with sequential indexing and template typography."""
        font_name = self.schema.paragraph_rules.body_font or self.schema.typography.default_font
        font_size = self.schema.paragraph_rules.body_size_pt or self.schema.typography.default_size_pt

        for idx, item in enumerate(items, start=1):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_after = Pt(3.0)
            p.paragraph_format.line_spacing = 1.15

            run_num = p.add_run(f"{idx}.  ")
            run_num.bold = True
            run_num.font.name = font_name
            run_num.font.size = Pt(font_size)

            run_text = p.add_run(item)
            run_text.font.name = font_name
            run_text.font.size = Pt(font_size)

    def add_table(self, headers: List[str], rows: List[List[str]], caption: Optional[str] = None):
        """Adds a cleanly styled table with header row formatting, borders, and caption."""
        if not headers or len(headers) == 0:
            raise ValueError("Table must contain at least one column header.")

        # Caption
        if caption:
            cap_para = self.doc.add_paragraph()
            cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_para.paragraph_format.space_before = Pt(6.0)
            cap_para.paragraph_format.space_after = Pt(4.0)
            run = cap_para.add_run(caption)
            run.bold = True
            run.font.name = self.schema.typography.default_font
            run.font.size = Pt(10.0)

        table = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        font_name = self.schema.typography.default_font

        # Header row
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            cell_p = hdr_cells[i].paragraphs[0]
            cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cell_p.add_run(header_text)
            run.bold = True
            run.font.name = font_name
            run.font.size = Pt(10.0)
            set_cell_shading(hdr_cells[i], "EAEAEA")
            set_cell_margins(hdr_cells[i], top=120, bottom=120, left=150, right=150)

        # Data rows
        for row_idx, row_data in enumerate(rows):
            row_cells = table.rows[row_idx + 1].cells
            for col_idx, cell_value in enumerate(row_data):
                if col_idx < len(row_cells):
                    cell_p = row_cells[col_idx].paragraphs[0]
                    run = cell_p.add_run(str(cell_value))
                    run.font.name = font_name
                    run.font.size = Pt(9.5)
                    set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=120, right=120)

        # Space after table
        after_p = self.doc.add_paragraph()
        after_p.paragraph_format.space_after = Pt(6.0)

    def add_image(
        self,
        image_path: str,
        caption: Optional[str] = None,
        max_width_inches: Optional[float] = None
    ) -> bool:
        """
        Embeds an image deterministically centered, respecting printable page bounds
        and adding an institutionally styled figure caption.
        """
        if not os.path.exists(image_path):
            logger.warning(f"Image path not found: {image_path}")
            return False

        # Calculate max printable width
        geom = self.schema.geometry
        printable_width_in = (geom.width_mm - geom.margins.left_mm - geom.margins.right_mm) / 25.4
        if printable_width_in <= 0:
            printable_width_in = 6.0

        target_width = max_width_inches or min(printable_width_in * 0.85, 5.5)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8.0)
        p.paragraph_format.space_after = Pt(4.0)

        run = p.add_run()
        run.add_picture(image_path, width=Inches(target_width))

        if caption:
            cap_para = self.doc.add_paragraph()
            cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_para.paragraph_format.space_after = Pt(8.0)
            run_cap = cap_para.add_run(caption)
            run_cap.italic = True
            run_cap.font.name = self.schema.typography.default_font
            run_cap.font.size = Pt(9.5)

        return True

    def add_quote(self, text: str):
        """Adds an indented blockquote with subtle italic styling."""
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.right_indent = Inches(0.5)
        p.paragraph_format.space_before = Pt(6.0)
        p.paragraph_format.space_after = Pt(6.0)
        run = p.add_run(f'"{text}"')
        run.italic = True
        run.font.name = self.schema.typography.default_font
        run.font.size = Pt(self.schema.typography.default_size_pt)

    def add_references(self, references: List[Any]):
        """Adds references list formatted with bracketed numbering and hanging indent."""
        font_name = self.schema.typography.default_font
        font_size = Pt(self.schema.typography.default_size_pt - 0.5)

        for idx, ref in enumerate(references, start=1):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.first_line_indent = Inches(-0.3)
            p.paragraph_format.space_after = Pt(4.0)
            p.paragraph_format.line_spacing = 1.15

            run_num = p.add_run(f"[{idx}]  ")
            run_num.bold = True
            run_num.font.name = font_name
            run_num.font.size = font_size

            ref_text = ref if isinstance(ref, str) else ref.get("text", str(ref))
            run_text = p.add_run(ref_text)
            run_text.font.name = font_name
            run_text.font.size = font_size

    def assemble_report(
        self,
        generated_report: Any,
        project_info: Dict[str, Any],
        verified_claims: Optional[List[Dict[str, Any]]] = None,
        evidence_inventory: Optional[List[Dict[str, Any]]] = None
    ) -> "DocumentAssembler":
        """
        Assembles complete report content deterministically.
        Strictly follows the authoritative section ordering from the locked template schema.
        """
        # 1. Deterministic placeholder replacements
        members_text = ""
        members = project_info.get("members") or []
        if members:
            members_text = ", ".join([m.get("student_name", "") for m in members if m.get("student_name")])

        placeholders = {
            "PROJECT_TITLE": project_info.get("title") or project_info.get("project_name") or "",
            "PROJECT_NAME": project_info.get("title") or project_info.get("project_name") or "",
            "REPORT_TITLE": project_info.get("report_title") or project_info.get("title") or "",
            "STUDENT_NAME": members_text or project_info.get("student_name") or "Student Name",
            "NAME": members_text or project_info.get("student_name") or "Student Name",
            "GUIDE_NAME": project_info.get("guide_name") or "Faculty Advisor",
            "ADVISOR": project_info.get("guide_name") or "Faculty Advisor",
            "DEPARTMENT": project_info.get("department") or "Department of Computer Science",
            "INSTITUTION": project_info.get("institution") or "University College of Engineering",
            "COLLEGE": project_info.get("institution") or "University College of Engineering",
            "ACADEMIC_YEAR": project_info.get("academic_year") or "2026-2027",
            "SEMESTER": project_info.get("semester") or "Semester VIII",
            "ROLL_NUMBER": project_info.get("roll_number") or "",
            "INTRODUCTION": project_info.get("introduction") or "",
            "OBJECTIVES": project_info.get("objectives") or "",
            "PROBLEM_STATEMENT": project_info.get("problem_statement") or "",
            "METHODOLOGY": project_info.get("methodology") or "",
            "TECHNOLOGIES": project_info.get("technologies") or "",
            "IMPLEMENTATION": project_info.get("implementation") or "",
            "RESULTS": project_info.get("results") or "",
            "ADVANTAGES": project_info.get("advantages") or "",
            "LIMITATIONS": project_info.get("limitations") or "",
            "FUTURE_SCOPE": project_info.get("future_scope") or "",
            "CONCLUSION": project_info.get("conclusion") or "",
            "REFERENCES": project_info.get("references") or "",
        }

        # Include any custom field values passed directly in project_info
        custom_fields = project_info.get("custom_field_values") or project_info.get("field_values") or {}
        for k, v in custom_fields.items():
            if isinstance(v, (str, int, float)):
                placeholders[k.upper()] = str(v)
            elif isinstance(v, list):
                placeholders[k.upper()] = "\n".join(str(item) for item in v)

        self.replace_placeholders(placeholders)

        # Automatic Image Mapping & Replacement
        image_mapping: Dict[str, Any] = {}
        for img_key in ["image_1", "image_2", "image_3"]:
            if project_info.get(img_key):
                image_mapping[img_key] = project_info.get(img_key)
        if project_info.get("image_mapping"):
            image_mapping.update(project_info["image_mapping"])
        if project_info.get("field_mapping"):
            image_mapping.update(project_info["field_mapping"])
        if custom_fields:
            for k, v in custom_fields.items():
                if "image" in k.lower():
                    image_mapping[k] = v

        if image_mapping:
            self.replace_template_images(image_mapping)

        # 2. Build multi-key lookup map of generated sections
        # Generated SectionGenerationOutput uses section_id set from the plan.
        # Template schema sections use TemplateSection.id (and detected_title).
        # We index by multiple keys to be robust to minor naming differences.
        gen_sections_by_id: Dict[str, Any] = {}         # keyed by section_id (lower)
        gen_sections_by_title: Dict[str, Any] = {}      # keyed by section_title (lower, stripped)

        for sec in getattr(generated_report, "sections", []):
            sec_id = getattr(sec, "section_id", None) or (sec.get("section_id") if isinstance(sec, dict) else None)
            sec_title = getattr(sec, "section_title", None) or (sec.get("section_title") if isinstance(sec, dict) else None)
            if sec_id:
                gen_sections_by_id[str(sec_id).lower().strip()] = sec
            if sec_title:
                gen_sections_by_title[str(sec_title).lower().strip()] = sec
                # Also index without punctuation/whitespace for fuzzy match
                norm = re.sub(r"[^a-z0-9]", "", str(sec_title).lower())
                gen_sections_by_title[norm] = sec

        def _find_generated_section(tpl_sec) -> Optional[Any]:
            """Try multiple matching strategies for a template section → generated section."""
            # Strategy 1: exact section_id match
            cand = gen_sections_by_id.get(str(tpl_sec.id).lower().strip())
            if cand:
                return cand
            # Strategy 2: detected_title exact match
            cand = gen_sections_by_title.get(str(tpl_sec.detected_title).lower().strip())
            if cand:
                return cand
            # Strategy 3: semantic_role exact match (used as section_id in plan fallback)
            cand = gen_sections_by_id.get(str(tpl_sec.semantic_role).lower().strip())
            if cand:
                return cand
            # Strategy 4: normalized title containment (partial match)
            norm_tpl = re.sub(r"[^a-z0-9]", "", str(tpl_sec.detected_title).lower())
            for norm_key, v in gen_sections_by_title.items():
                if norm_tpl and norm_key and (norm_tpl in norm_key or norm_key in norm_tpl):
                    return v
            # Strategy 5: any generated section whose title contains the template title
            tpl_title_lower = str(tpl_sec.detected_title).lower().strip()
            for sec in getattr(generated_report, "sections", []):
                sec_title = getattr(sec, "section_title", None) or (sec.get("section_title") if isinstance(sec, dict) else "")
                if sec_title and tpl_title_lower in str(sec_title).lower():
                    return sec
            return None

        # If schema has defined sections, use schema section sequence as authoritative order
        ordered_sections = self.schema.sections if self.schema.sections else []

        if not ordered_sections:
            # Fallback to report's own sections if template schema had 0 sections extracted
            logger.warning("Template schema has 0 sections — using generated report section order as fallback. This may indicate template parsing failure.")
            report_sections = getattr(generated_report, "sections", [])
            for sec in report_sections:
                self._render_section(sec, evidence_inventory)
        else:
            # Render according to authoritative locked template order
            chapter_counter = 0
            matched_count = 0
            for tpl_sec in ordered_sections:
                sec_type = (tpl_sec.section_type or "").lower()
                sec_title = (tpl_sec.detected_title or "").lower()

                # Handle Title Page deterministically
                if sec_type == "title_page" or "cover" in sec_title or (tpl_sec.order == 1 and "title" in sec_title):
                    if not self._is_from_master:
                        self._render_title_page(project_info)
                    matched_count += 1
                    continue

                # Handle Table of Contents deterministically
                if sec_type == "toc" or "contents" in sec_title:
                    content_sections = [s for s in ordered_sections if (s.section_type or "").lower() not in ("title_page", "toc") and "cover" not in (s.detected_title or "").lower()]
                    self._render_toc(content_sections)
                    matched_count += 1
                    continue

                matched_content = _find_generated_section(tpl_sec)

                if matched_content:
                    matched_count += 1

                is_chapter = tpl_sec.section_type == "chapter" or "chapter" in tpl_sec.detected_title.lower()
                if is_chapter:
                    chapter_counter += 1

                prefix = f"Chapter {chapter_counter}:" if is_chapter and not re.search(r"(?i)chapter\s+\d+", tpl_sec.detected_title) else None

                # For slide presentations or distinct sections, start each on a new page if previous paragraph had text
                if not self._is_from_master and self.doc.paragraphs:
                    last_p = self.doc.paragraphs[-1]
                    if last_p.text.strip():
                        self.doc.add_page_break()

                if matched_content:
                    self._render_section(
                        matched_content,
                        evidence_inventory,
                        heading_override=tpl_sec.detected_title,
                        numbering_prefix=prefix,
                        level=tpl_sec.level or 1
                    )
                else:
                    self.add_heading(tpl_sec.detected_title, level=tpl_sec.level or 1, numbering_prefix=prefix)


            total_tpl = len(ordered_sections)
            if matched_count < total_tpl:
                logger.warning(
                    f"Section matching coverage: {matched_count}/{total_tpl} template sections were matched "
                    f"to generated content. {total_tpl - matched_count} sections rendered as empty placeholders."
                )

        return self

    def _render_title_page(self, project_info: Dict[str, Any]):
        """Renders the formal title / presentation cover page deterministically."""
        institution = project_info.get("institution") or "SRI VENKATESWARA COLLEGE OF ENGINEERING"
        department = project_info.get("department") or "Department of Electrical & Electronics Engineering"
        proj_type = project_info.get("project_type") or "Community Service Project"
        title = project_info.get("title") or "Academic Project"
        guide_name = project_info.get("guide_name") or "Dr. R. Sireesha Ph.D."
        academic_year = project_info.get("academic_year") or "2024-2028"

        # Institution Header
        p_inst = self.doc.add_paragraph()
        p_inst.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_inst = p_inst.add_run(f"{institution.split('(')[0].strip().upper()}\n")
        r_inst.bold = True
        r_inst.font.name = self.schema.typography.default_font
        r_inst.font.size = Pt(13)
        r_inst.font.color.rgb = RGBColor(27, 54, 93)

        r_sub = p_inst.add_run("EDUCATION FOR A BETTER SOCIETY\n")
        r_sub.font.name = self.schema.typography.default_font
        r_sub.font.size = Pt(8.5)
        r_sub.font.color.rgb = RGBColor(120, 120, 120)

        # Presentation Subtitle
        p_pres = self.doc.add_paragraph()
        p_pres.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pres.paragraph_format.space_before = Pt(18)
        p_pres.paragraph_format.space_after = Pt(12)
        r_pres = p_pres.add_run(f"{proj_type}\nPresentation on\n")
        r_pres.font.name = self.schema.typography.default_font
        r_pres.font.size = Pt(12.5)
        r_pres.font.color.rgb = RGBColor(180, 40, 40)

        # Project Title
        r_title = p_pres.add_run(f'“{title.upper()}”')
        r_title.bold = True
        r_title.font.name = self.schema.typography.default_font
        r_title.font.size = Pt(15)
        r_title.font.color.rgb = RGBColor(180, 20, 20)

        # Presented By
        p_by = self.doc.add_paragraph()
        p_by.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_by.paragraph_format.space_before = Pt(14)
        p_by.paragraph_format.space_after = Pt(6)
        r_by = p_by.add_run("Presented by\n")
        r_by.font.name = self.schema.typography.default_font
        r_by.font.size = Pt(11)
        r_by.italic = True
        r_by.font.color.rgb = RGBColor(180, 100, 20)

        # Members list / table
        members = project_info.get("members") or []
        if members:
            tbl = self.doc.add_table(rows=len(members), cols=2)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            for idx, m in enumerate(members):
                s_name = m.get("student_name") or m.get("name") or "Student"
                r_no = m.get("roll_number") or m.get("roll_no") or ""
                c0 = tbl.rows[idx].cells[0].paragraphs[0]
                c0.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r0 = c0.add_run(s_name.upper())
                r0.bold = True
                r0.font.name = self.schema.typography.default_font
                r0.font.size = Pt(9.5)

                c1 = tbl.rows[idx].cells[1].paragraphs[0]
                c1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                r1 = c1.add_run(r_no)
                r1.bold = True
                r1.font.name = self.schema.typography.default_font
                r1.font.size = Pt(9.5)
        else:
            s_name = project_info.get("student_name") or "Engineering Scholar"
            r_no = project_info.get("roll_number") or project_info.get("roll_no") or ""
            p_stu = self.doc.add_paragraph()
            p_stu.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_stu = p_stu.add_run(f"{s_name.upper()}   {r_no}")
            r_stu.bold = True
            r_stu.font.name = self.schema.typography.default_font
            r_stu.font.size = Pt(10)

        # Guidance
        p_guid = self.doc.add_paragraph()
        p_guid.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_guid.paragraph_format.space_before = Pt(16)
        p_guid.paragraph_format.space_after = Pt(4)
        r_g1 = p_guid.add_run("Under the Guidance of\n")
        r_g1.font.name = self.schema.typography.default_font
        r_g1.font.size = Pt(10.5)
        r_g1.italic = True
        r_g1.font.color.rgb = RGBColor(180, 40, 40)

        r_g2 = p_guid.add_run(f"{guide_name}\n")
        r_g2.bold = True
        r_g2.font.name = self.schema.typography.default_font
        r_g2.font.size = Pt(11)

        # Department & Institution
        p_foot = self.doc.add_paragraph()
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_foot.paragraph_format.space_before = Pt(12)
        r_d = p_foot.add_run(f"{department}\n")
        r_d.font.name = self.schema.typography.default_font
        r_d.font.size = Pt(10.5)
        r_d.font.color.rgb = RGBColor(27, 54, 93)

        r_c = p_foot.add_run(f"{institution.upper()}\n(Autonomous)\n")
        r_c.bold = True
        r_c.font.name = self.schema.typography.default_font
        r_c.font.size = Pt(12)
        r_c.font.color.rgb = RGBColor(27, 54, 93)

        if academic_year:
            r_y = p_foot.add_run(f"{academic_year}")
            r_y.bold = True
            r_y.font.name = self.schema.typography.default_font
            r_y.font.size = Pt(9.5)
            r_y.font.color.rgb = RGBColor(180, 40, 40)

        self.doc.add_page_break()

    def _render_toc(self, content_sections: List[Any]):
        """Renders the Table of Contents slide/page matching the template structure."""
        p_toc = self.doc.add_paragraph()
        p_toc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_toc.paragraph_format.space_before = Pt(12)
        p_toc.paragraph_format.space_after = Pt(16)
        run_t = p_toc.add_run("CONTENTS")
        run_t.bold = True
        run_t.font.name = self.schema.typography.default_font
        run_t.font.size = Pt(16)
        run_t.font.color.rgb = RGBColor(180, 20, 20)

        for sec in content_sections:
            title = getattr(sec, "detected_title", "")
            clean_title = re.sub(r"^[•\uf0d8\uf071\uf0a7\s\d\.\-:]+", "", title).strip()
            if not clean_title or clean_title.lower() in ("cover / title page", "title / cover page", "contents", "table of contents"):
                continue
            p_item = self.doc.add_paragraph()
            p_item.paragraph_format.left_indent = Inches(0.8)
            p_item.paragraph_format.space_after = Pt(6)
            r_bullet = p_item.add_run("•  ")
            r_bullet.bold = True
            r_bullet.font.size = Pt(13)
            r_bullet.font.color.rgb = RGBColor(180, 20, 20)

            r_txt = p_item.add_run(clean_title)
            r_txt.font.name = self.schema.typography.default_font
            r_txt.font.size = Pt(12.5)
            r_txt.bold = True

        self.doc.add_page_break()



    def _render_section(
        self,
        sec: Any,
        evidence_inventory: Optional[List[Dict[str, Any]]] = None,
        heading_override: Optional[str] = None,
        numbering_prefix: Optional[str] = None,
        level: int = 1
    ):
        """Renders an individual report section and its constituent content blocks."""
        title = heading_override or getattr(sec, "section_title", None) or (sec.get("section_title") if isinstance(sec, dict) else "Section")
        self.add_heading(title, level=level, numbering_prefix=numbering_prefix)

        content_blocks = getattr(sec, "content_blocks", []) or (sec.get("content_blocks", []) if isinstance(sec, dict) else [])

        for block in content_blocks:
            b_type = getattr(block, "block_type", None) or (block.get("block_type") if isinstance(block, dict) else "paragraph")
            b_text = getattr(block, "text", "") or (block.get("text", "") if isinstance(block, dict) else "")

            if b_type == "heading":
                b_level = getattr(block, "level", 2) or (block.get("level", 2) if isinstance(block, dict) else 2)
                self.add_heading(b_text, level=min(b_level, 4))

            elif b_type == "paragraph":
                clean_text = re.sub(r'\blead to\b', 'result in', b_text, flags=re.I)
                clean_text = re.sub(r'\bleads to\b', 'results in', clean_text, flags=re.I)
                self.add_body_paragraph(clean_text)

            elif b_type in ("bullet_list", "list"):
                items = getattr(block, "items", []) or (block.get("items", []) if isinstance(block, dict) else [])
                clean_items = [
                    re.sub(r'\bleads to\b', 'results in', re.sub(r'\blead to\b', 'result in', item, flags=re.I), flags=re.I)
                    for item in items
                ]
                if clean_items:
                    self.add_bullet_list(clean_items)
                elif b_text:
                    clean_b = re.sub(r'\bleads to\b', 'results in', re.sub(r'\blead to\b', 'result in', b_text, flags=re.I), flags=re.I)
                    self.add_bullet_list([clean_b])


            elif b_type == "numbered_list":
                items = getattr(block, "items", []) or (block.get("items", []) if isinstance(block, dict) else [])
                if items:
                    self.add_numbered_list(items)
                elif b_text:
                    self.add_numbered_list([b_text])

            elif b_type == "table":
                headers = getattr(block, "headers", []) or (block.get("headers", []) if isinstance(block, dict) else [])
                rows = getattr(block, "rows", []) or (block.get("rows", []) if isinstance(block, dict) else [])
                caption = b_text if b_text else None
                if headers:
                    self.add_table(headers, rows, caption=caption)

            elif b_type == "quote":
                self.add_quote(b_text)

            elif b_type == "note":
                self.add_body_paragraph(b_text, bold_prefix="Note: ")

            elif b_type == "image":
                # Check evidence inventory for matching image
                img_path = getattr(block, "image_path", None) or (block.get("image_path") if isinstance(block, dict) else None)
                if not img_path and evidence_inventory:
                    source_ids = getattr(block, "source_evidence_ids", []) or (block.get("source_evidence_ids", []) if isinstance(block, dict) else [])
                    for ev in evidence_inventory:
                        if ev.get("id") in source_ids and ev.get("mime_type", "").startswith("image/"):
                            img_path = ev.get("local_path") or ev.get("storage_path")
                            break
                if img_path and os.path.exists(img_path):
                    self.add_image(img_path, caption=b_text)
                else:
                    # Clean visual requirement note if image file not on disk
                    self.add_body_paragraph(f"[Visual Asset: {b_text or 'Figure'}]", bold_prefix="Figure Slot: ")

    def save(self, output_path: str) -> str:
        """Saves the compiled document to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.doc.save(output_path)
        return output_path
