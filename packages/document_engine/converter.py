"""
ARM Stage 10 - Server-Side DOCX to PDF Conversion Engine
Provides an extensible conversion abstraction supporting:
1. LibreOffice / headless conversion (when installed in system environment)
2. Pure Python ReportLab + python-docx layout conversion (standalone, zero-dependency server engine)
3. Timeout protection, isolated process execution, and error handling
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import pymupdf


class ConverterUnavailableError(RuntimeError):
    """Raised when no PDF converter is available on the server."""
    pass


class ConversionTimeoutError(TimeoutError):
    """Raised when PDF conversion exceeds the timeout limit."""
    pass


class ConversionFailedError(RuntimeError):
    """Raised when PDF conversion fails or outputs invalid data."""
    pass


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page count and running headers/footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.doc_title = getattr(self, "doc_title", "Academic Report")
        self.header_text = getattr(self, "header_text", "")
        self.footer_text = getattr(self, "footer_text", "")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        page_w, page_h = self._pagesize

        # Running header (pages > 1)
        if self._pageNumber > 1:
            h_text = self.header_text or self.doc_title
            self.drawString(54, page_h - 36, h_text[:70])
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, page_h - 42, page_w - 54, page_h - 42)

        # Running footer
        f_left = self.footer_text or "ARM Academic Report Assistant"
        self.drawString(54, 30, f_left)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_w - 54, 30, page_str)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 40, page_w - 54, 40)

        self.restoreState()


class BasePdfConverter(ABC):
    """Abstract base class for DOCX to PDF converters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the converter identification name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the converter is available in the current environment."""
        pass

    @abstractmethod
    def convert(self, docx_path: str, pdf_path: str, timeout: int = 60) -> bool:
        """
        Converts DOCX to PDF.
        Returns True on success, raises an exception on failure.
        """
        pass


class LibreOfficeConverter(BasePdfConverter):
    """Converts DOCX to PDF using LibreOffice headless command line."""

    @property
    def name(self) -> str:
        return "libreoffice_headless"

    def _find_binary(self) -> Optional[str]:
        # Check standard PATH
        binary = shutil.which("soffice") or shutil.which("libreoffice")
        if binary:
            return binary

        # Check standard Windows paths
        win_candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ]
        for candidate in win_candidates:
            if os.path.exists(candidate):
                return candidate

        # Check standard Linux paths
        linux_candidates = ["/usr/bin/soffice", "/usr/bin/libreoffice", "/usr/local/bin/soffice"]
        for candidate in linux_candidates:
            if os.path.exists(candidate):
                return candidate

        return None

    def is_available(self) -> bool:
        return self._find_binary() is not None

    def convert(self, docx_path: str, pdf_path: str, timeout: int = 60) -> bool:
        binary = self._find_binary()
        if not binary:
            raise ConverterUnavailableError("LibreOffice binary not found in environment.")

        out_dir = os.path.dirname(os.path.abspath(pdf_path))
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            binary,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            docx_path
        ]

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False
            )
            if res.returncode != 0:
                raise ConversionFailedError(
                    f"LibreOffice conversion failed with code {res.returncode}: {res.stderr.decode('utf-8', errors='ignore')}"
                )

            # Expected default output name
            base_name = os.path.splitext(os.path.basename(docx_path))[0]
            generated_pdf = os.path.join(out_dir, f"{base_name}.pdf")

            if os.path.exists(generated_pdf) and generated_pdf != pdf_path:
                shutil.move(generated_pdf, pdf_path)

            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise ConversionFailedError("LibreOffice completed but no valid PDF was produced.")

            return True

        except subprocess.TimeoutExpired as e:
            raise ConversionTimeoutError(f"LibreOffice conversion timed out after {timeout} seconds.") from e
        except Exception as e:
            if isinstance(e, (ConversionTimeoutError, ConversionFailedError)):
                raise
            raise ConversionFailedError(f"LibreOffice process execution error: {str(e)}") from e


class PurePythonDocxPdfConverter(BasePdfConverter):
    """
    High-fidelity pure Python DOCX -> PDF converter.
    Parses OpenXML document elements (sections, margins, headings, paragraphs,
    inline runs, tables, bullet lists, numbered lists, blockquotes, references, images)
    and constructs a compliant PDF using ReportLab with exact template layout rules.
    Runs reliably server-side in all environments without external binary dependencies.
    """

    @property
    def name(self) -> str:
        return "pure_python_reportlab"

    def is_available(self) -> bool:
        return True

    def convert(self, docx_path: str, pdf_path: str, timeout: int = 60) -> bool:
        start_time = time.time()

        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"Source DOCX file not found: {docx_path}")

        try:
            doc = docx.Document(docx_path)
        except Exception as e:
            raise ConversionFailedError(f"Failed to open source DOCX: {e}") from e

        # Target directory
        out_dir = os.path.dirname(os.path.abspath(pdf_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # Inspect section geometry
        first_section = doc.sections[0] if doc.sections else None
        if first_section:
            # Page dimensions
            page_w = first_section.page_width.pt if first_section.page_width else 612
            page_h = first_section.page_height.pt if first_section.page_height else 792
            top_m = first_section.top_margin.pt if first_section.top_margin else 54
            bottom_m = first_section.bottom_margin.pt if first_section.bottom_margin else 54
            left_m = first_section.left_margin.pt if first_section.left_margin else 54
            right_m = first_section.right_margin.pt if first_section.right_margin else 54
        else:
            page_w, page_h = 612, 792
            top_m, bottom_m, left_m, right_m = 54, 54, 54, 54

        # Read header / footer text if present
        header_text = ""
        footer_text = ""
        if first_section and first_section.header:
            header_text = "\n".join([p.text.strip() for p in first_section.header.paragraphs if p.text.strip()])
        if first_section and first_section.footer:
            footer_text = "\n".join([p.text.strip() for p in first_section.footer.paragraphs if p.text.strip()])

        doc_template = SimpleDocTemplate(
            pdf_path,
            pagesize=(page_w, page_h),
            leftMargin=left_m,
            rightMargin=right_m,
            topMargin=max(top_m, 48),
            bottomMargin=max(bottom_m, 48)
        )

        styles = getSampleStyleSheet()

        # Custom typography styles aligned with TemplateSchema
        style_title = ParagraphStyle(
            'DOCX_Title',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        style_subtitle = ParagraphStyle(
            'DOCX_Subtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#2563EB"),
            alignment=TA_CENTER,
            spaceAfter=16
        )
        style_h1 = ParagraphStyle(
            'DOCX_H1',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        style_h2 = ParagraphStyle(
            'DOCX_H2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )
        style_h3 = ParagraphStyle(
            'DOCX_H3',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True
        )
        style_body = ParagraphStyle(
            'DOCX_Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        style_bullet = ParagraphStyle(
            'DOCX_Bullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#1E293B"),
            leftIndent=18,
            firstLineIndent=-10,
            spaceAfter=3
        )
        style_quote = ParagraphStyle(
            'DOCX_Quote',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
            leftIndent=24,
            rightIndent=24,
            spaceBefore=6,
            spaceAfter=6
        )
        style_ref = ParagraphStyle(
            'DOCX_Ref',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1E293B"),
            leftIndent=20,
            firstLineIndent=-20,
            spaceAfter=4
        )
        style_table_cell = ParagraphStyle(
            'DOCX_TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        )
        style_table_header = ParagraphStyle(
            'DOCX_TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#0F172A")
        )

        story = []
        doc_title_extracted = ""

        # Check timeout helper
        def check_timeout():
            if time.time() - start_time > timeout:
                raise ConversionTimeoutError(f"Conversion exceeded timeout of {timeout} seconds.")

        # Extract embedded images from document parts for image rendering
        embedded_images = {}
        try:
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    part_bytes = rel.target_part.blob
                    embedded_images[rel.rId] = part_bytes
        except Exception:
            pass

        # Helper to convert runs to ReportLab inline formatting
        def runs_to_xml(p) -> str:
            fragments = []
            for r in p.runs:
                txt = r.text
                if not txt:
                    continue
                # Escape XML entities
                txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if r.bold and r.italic:
                    txt = f"<b><i>{txt}</i></b>"
                elif r.bold:
                    txt = f"<b>{txt}</b>"
                elif r.italic:
                    txt = f"<i>{txt}</i>"
                if r.underline:
                    txt = f"<u>{txt}</u>"
                fragments.append(txt)
            return "".join(fragments) or p.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Iterate through paragraphs and tables in OpenXML body order
        for block in doc.element.body:
            check_timeout()
            tag = block.tag.split("}")[-1]

            if tag == "p":
                # Paragraph
                p = docx.text.paragraph.Paragraph(block, doc)
                text = p.text.strip()
                if not text:
                    # Check for page break
                    if "w:br" in block.xml and 'type="page"' in block.xml:
                        story.append(PageBreak())
                    continue

                style_name = (p.style.name or "").lower()
                xml_content = runs_to_xml(p)

                if "title" in style_name and not doc_title_extracted:
                    doc_title_extracted = text
                    story.append(Paragraph(xml_content, style_title))
                elif "subtitle" in style_name:
                    story.append(Paragraph(xml_content, style_subtitle))
                elif "heading 1" in style_name:
                    story.append(Paragraph(xml_content, style_h1))
                elif "heading 2" in style_name:
                    story.append(Paragraph(xml_content, style_h2))
                elif "heading 3" in style_name:
                    story.append(Paragraph(xml_content, style_h3))
                elif "bullet" in style_name or text.startswith("•") or text.startswith("- "):
                    # Ensure clean bullet rendering
                    clean_txt = xml_content.lstrip("•- \t")
                    story.append(Paragraph(f"• &nbsp;{clean_txt}", style_bullet))
                elif "number" in style_name:
                    story.append(Paragraph(xml_content, style_bullet))
                elif "quote" in style_name or "blockquote" in style_name:
                    story.append(Paragraph(xml_content, style_quote))
                elif "ref" in style_name:
                    story.append(Paragraph(xml_content, style_ref))
                else:
                    # Normal / Body Text
                    story.append(Paragraph(xml_content, style_body))

            elif tag == "tbl":
                # Table
                t = docx.table.Table(block, doc)
                table_data = []
                row_count = len(t.rows)
                col_count = len(t.columns) if row_count > 0 else 0

                if row_count == 0 or col_count == 0:
                    continue

                for r_idx, row in enumerate(t.rows):
                    row_cells = []
                    for cell in row.cells:
                        c_text = cell.text.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        if r_idx == 0:
                            row_cells.append(Paragraph(c_text, style_table_header))
                        else:
                            row_cells.append(Paragraph(c_text, style_table_cell))
                    table_data.append(row_cells)

                # Usable width for table
                usable_w = page_w - left_m - right_m
                col_w = usable_w / max(col_count, 1)

                t_flowable = Table(table_data, colWidths=[col_w] * col_count)
                t_flowable.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(Spacer(1, 4))
                story.append(t_flowable)
                story.append(Spacer(1, 6))

        temp_img_dir = None
        # Check for embedded images and append representative flowables
        if embedded_images:
            temp_img_dir = tempfile.mkdtemp(prefix="arm_img_")
            for img_id, img_bytes in embedded_images.items():
                img_path = os.path.join(temp_img_dir, f"{img_id}.png")
                with open(img_path, "wb") as f_img:
                    f_img.write(img_bytes)
                # Usable bounds
                max_w = min(page_w - left_m - right_m, 400)
                try:
                    rl_img = RLImage(img_path, width=max_w, height=max_w * 0.55)
                    story.append(Spacer(1, 4))
                    story.append(rl_img)
                    story.append(Spacer(1, 4))
                except Exception:
                    pass

        if not story:
            story.append(Paragraph("Empty Academic Report", style_title))

        # Build PDF using NumberedCanvas
        def make_canvas(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            c.doc_title = doc_title_extracted or "Academic Report"
            c.header_text = header_text
            c.footer_text = footer_text
            return c

        check_timeout()
        try:
            doc_template.build(story, canvasmaker=make_canvas)
        except Exception as e:
            raise ConversionFailedError(f"ReportLab PDF compilation failed: {e}") from e
        finally:
            if temp_img_dir and os.path.exists(temp_img_dir):
                shutil.rmtree(temp_img_dir, ignore_errors=True)

        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise ConversionFailedError("ReportLab generated a zero-byte or missing PDF.")

        return True


class PdfConverterService:
    """
    Manager service coordinating PDF converter strategies:
    - Selects LibreOffice if available, or falls back to PurePythonDocxPdfConverter.
    - Provides explicit test hooks for mocking unavailability, timeouts, and failures.
    """

    def __init__(self):
        self._libreoffice = LibreOfficeConverter()
        self._python_converter = PurePythonDocxPdfConverter()
        self._simulate_unavailable: bool = False
        self._simulate_timeout: bool = False
        self._simulate_corrupt_output: bool = False

    def set_simulate_unavailable(self, val: bool):
        """Test hook to simulate no converter available in environment."""
        self._simulate_unavailable = val

    def set_simulate_timeout(self, val: bool):
        """Test hook to simulate converter timeout."""
        self._simulate_timeout = val

    def set_simulate_corrupt_output(self, val: bool):
        """Test hook to simulate broken or zero-byte converter output."""
        self._simulate_corrupt_output = val

    def is_available(self) -> bool:
        if self._simulate_unavailable:
            return False
        return self._libreoffice.is_available() or self._python_converter.is_available()

    def convert(self, docx_path: str, pdf_path: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Executes conversion with fallback, timeout protection, and health checks.
        """
        if self._simulate_unavailable:
            raise ConverterUnavailableError("No PDF converter available on this server.")

        if self._simulate_timeout:
            raise ConversionTimeoutError(f"Conversion process timed out after {timeout} seconds.")

        start_time = time.time()
        converter_used = ""

        # Priority 1: LibreOffice if available on host
        if self._libreoffice.is_available():
            try:
                self._libreoffice.convert(docx_path, pdf_path, timeout=timeout)
                converter_used = self._libreoffice.name
            except Exception:
                # Fall back to pure Python
                pass

        # Priority 2: Pure Python ReportLab converter
        if not converter_used:
            self._python_converter.convert(docx_path, pdf_path, timeout=timeout)
            converter_used = self._python_converter.name

        if self._simulate_corrupt_output:
            # Overwrite with 0 bytes or corrupt payload for test
            with open(pdf_path, "wb") as f:
                f.write(b"NOT_A_VALID_PDF_CORRUPT")

        duration = round(time.time() - start_time, 3)

        return {
            "converter": converter_used,
            "duration_seconds": duration,
            "pdf_path": pdf_path,
            "file_size_bytes": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        }


pdf_converter_service = PdfConverterService()
