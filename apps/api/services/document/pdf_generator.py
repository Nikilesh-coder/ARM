"""
ReportForge AI - PDF Report Generator
Replicates the exact visual design, colors, emblem logo, and layout of the uploaded
institutional report PDF while replacing all text and figures for the searched topic.
"""

import os
import re
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from apps.api.core.logging import get_logger

logger = get_logger("pdf.generator")


class NumberedCanvas(canvas.Canvas):
    """Adds bottom-centered page numbers matching the uploaded template."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Times-Roman", 11)
        self.setFillColor(colors.black)
        # Centered at bottom (0.55 inch from bottom)
        page_str = str(self._pageNumber)
        self.drawCentredString(letter[0] / 2.0, 0.55 * inch, page_str)
        self.restoreState()


def generate_academic_pdf(
    output_pdf_path: str,
    title: str,
    project_type: str,
    student_name: str,
    roll_no: str,
    guide_name: str,
    hod_name: str,
    department: str,
    institution: str,
    affiliation: str,
    academic_year: str,
    abstract_text: str,
    chapters: List[Dict[str, Any]],
    images: Dict[str, str],
    design: Optional[Dict[str, Any]] = None
) -> str:
    """
    Renders an academic PDF document using ReportLab matching the exact visual design,
    emblem logo, colors, and layout of the uploaded PDF template.
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    # 1. Colors extracted from the template
    color_red = colors.HexColor("#E60000")       # Primary title & heading color
    color_navy = colors.HexColor("#002060")      # Degree color
    color_green = colors.HexColor("#008000")     # Preposition 'IN'
    color_crimson = colors.HexColor("#CC0066")   # Department color
    color_cyan = colors.HexColor("#0088CC")      # 'by' & autonomous tag
    color_purple = colors.HexColor("#660099")    # Credentials color
    color_blue = colors.HexColor("#0033CC")      # College name color
    color_maroon = colors.HexColor("#990000")    # Affiliation color

    # Locate extracted college logo
    logo_file = design.get("logo_path") if design else None
    if not logo_file or not os.path.exists(logo_file):
        if os.path.exists(".storage/templates/extracted_logo.png"):
            logo_file = ".storage/templates/extracted_logo.png"

    # Margins: 1.0" standard margins
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.9 * inch
    )

    styles = getSampleStyleSheet()

    # Cover Page Typography Styles
    style_cover_title = ParagraphStyle(
        "CoverTitle",
        fontName="Times-Bold",
        fontSize=15,
        leading=19,
        alignment=TA_CENTER,
        textColor=color_red,
        spaceAfter=10
    )
    style_cover_sub = ParagraphStyle(
        "CoverSub",
        fontName="Times-Roman",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=12
    )
    style_degree = ParagraphStyle(
        "CoverDegree",
        fontName="Times-Bold",
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=color_navy,
        spaceAfter=6
    )
    style_in = ParagraphStyle(
        "CoverIn",
        fontName="Times-Bold",
        fontSize=11,
        leading=15,
        alignment=TA_CENTER,
        textColor=color_green,
        spaceAfter=6
    )
    style_dept_crimson = ParagraphStyle(
        "CoverDeptCrimson",
        fontName="Times-Bold",
        fontSize=11,
        leading=15,
        alignment=TA_CENTER,
        textColor=color_crimson,
        spaceAfter=8
    )
    style_by = ParagraphStyle(
        "CoverBy",
        fontName="Times-Bold",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=color_cyan,
        spaceAfter=8
    )
    style_college_blue = ParagraphStyle(
        "CoverCollegeBlue",
        fontName="Times-Bold",
        fontSize=13,
        leading=17,
        alignment=TA_CENTER,
        textColor=color_blue,
        spaceAfter=3
    )
    style_autonomous = ParagraphStyle(
        "CoverAutonomous",
        fontName="Times-Bold",
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=color_cyan,
        spaceAfter=4
    )
    style_affiliation_maroon = ParagraphStyle(
        "CoverAffMaroon",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=color_maroon,
        spaceAfter=4
    )

    # Academic Document Styles (Chapters, Abstract, etc.)
    style_h1_red = ParagraphStyle(
        "ChapterH1Red",
        fontName="Times-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=color_red,
        spaceBefore=12,
        spaceAfter=12,
        keepWithNext=True
    )
    style_h2_red = ParagraphStyle(
        "SectionH2Red",
        fontName="Times-Bold",
        fontSize=11.5,
        leading=15,
        alignment=TA_LEFT,
        textColor=color_red,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        "AcademicBodyText",
        fontName="Times-Roman",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        textColor=colors.black,
        spaceAfter=8
    )
    style_caption = ParagraphStyle(
        "FigureCaption",
        fontName="Times-Italic",
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceBefore=4,
        spaceAfter=12
    )

    story = []

    # -------------------------------------------------------------------------
    # PAGE 1: COVER PAGE
    # -------------------------------------------------------------------------
    story.append(Paragraph(title.upper(), style_cover_title))
    story.append(Paragraph(
        f"A {project_type} report submitted in partial fulfilment for the award of the degree of",
        style_cover_sub
    ))
    story.append(Paragraph("BACHELOR OF TECHNOLOGY", style_degree))
    story.append(Paragraph("IN", style_in))
    story.append(Paragraph(department.upper(), style_dept_crimson))
    story.append(Paragraph("by", style_by))

    # Student Credentials Table
    stu_table_data = [
        ["NAME", "ROLL NO"],
        [student_name, roll_no]
    ]
    t_stu = Table(stu_table_data, colWidths=[2.6 * inch, 2.6 * inch])
    t_stu.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), color_purple),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_stu)
    story.append(Spacer(1, 10))

    # Centered Circular College Logo
    if logo_file and os.path.exists(logo_file):
        story.append(RLImage(logo_file, width=2.3 * inch, height=2.3 * inch))
        story.append(Spacer(1, 12))
    else:
        story.append(Spacer(1, 35))

    story.append(Paragraph(department.upper(), style_dept_crimson))
    story.append(Paragraph(institution.upper(), style_college_blue))
    story.append(Paragraph("(AUTONOMOUS)", style_autonomous))
    story.append(Paragraph(
        f"({affiliation})<br/>"
        f"Accredited by NBA, New Delhi &amp; NAAC with 'A' grade, Karakambadi Road, TIRUPATI – 517507<br/>"
        f"{academic_year}<br/>"
        f"(AUTONOMOUS)",
        style_affiliation_maroon
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 2: CERTIFICATE
    # -------------------------------------------------------------------------
    story.append(Paragraph(
        f"({affiliation})<br/>"
        f"Accredited by NBA, New Delhi &amp; NAAC with 'A' Grade, Karakambadi Road, TIRUPATI – 517507.<br/><br/>"
        f"<b>{department.upper()}</b>",
        style_affiliation_maroon
    ))
    story.append(Spacer(1, 8))

    if logo_file and os.path.exists(logo_file):
        story.append(RLImage(logo_file, width=2.0 * inch, height=2.0 * inch))
        story.append(Spacer(1, 8))

    story.append(Paragraph("CERTIFICATE", style_h1_red))
    story.append(Spacer(1, 6))

    cert_text = (
        f'This is to certify that the {project_type} Report entitled, '
        f'<font color="#E60000"><b>"{title.upper()}"</b></font> is a Bonafide record of the work '
        f'presented and submitted by <font color="#660099"><b>{student_name}</b>; {roll_no}</font> '
        f'for the partial fulfillment of the requirements for the award of B.Tech degree in '
        f'<font color="#0033CC"><b>{department.upper()}</b></font>.'
    )
    story.append(Paragraph(cert_text, style_body))
    story.append(Spacer(1, 45))

    dept_short = department.split()[-1] if department else "EEE"
    sig_left = Paragraph(
        f"<b>{guide_name}</b><br/>Guide",
        ParagraphStyle("SigLeft", fontName="Times-Roman", fontSize=10.5, leading=14, alignment=TA_LEFT)
    )
    sig_right = Paragraph(
        f"<b>{hod_name}</b><br/>Head of the Department of {dept_short}",
        ParagraphStyle("SigRight", fontName="Times-Roman", fontSize=10.5, leading=14, alignment=TA_RIGHT)
    )
    t_sig = Table([[sig_left, sig_right]], colWidths=[3.2 * inch, 3.2 * inch])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_sig)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 3: ACKNOWLEDGEMENT
    # -------------------------------------------------------------------------
    story.append(Paragraph("ACKNOWLEDGEMENT", ParagraphStyle(
        "AckTitle", parent=styles['Normal'], fontName='Times-Bold', fontSize=14, alignment=TA_CENTER, spaceAfter=14
    )))

    ack_paras = [
        f"I am thankful to my guide <b>{guide_name}</b>, Associate Professor, Department of {dept_short} for her valuable guidance, encouragement, and supportive attitude which helped in the successful completion of this report.",
        f"I would like to express my sincere gratitude to <b>{hod_name}</b>, Professor &amp; Head, Department of {dept_short}, for his kind guidance and encouragement during the course of study and in the successful completion of the seminar report.",
        "I would like to express my heartfelt thanks to <b>Dr. K. Chandrasekhar Reddy</b>, Principal, for successful completion of this report, which could not have been done without the support and encouragement of the faculty.",
        "I sincerely thank the Management for providing all the necessary facilities during the course of this study.",
        "I would like to express my deep gratitude to all those who helped directly or indirectly to transform an idea into a successful seminar report."
    ]
    for ap in ack_paras:
        story.append(Paragraph(ap, style_body))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 35))
    story.append(Paragraph(f"<b>{student_name}</b><br/>(Roll No: {roll_no})", ParagraphStyle(
        "AckSign", parent=styles['Normal'], fontName='Times-Roman', fontSize=10.5, alignment=TA_RIGHT
    )))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 4: ABSTRACT
    # -------------------------------------------------------------------------
    story.append(Paragraph("ABSTRACT", style_h1_red))
    story.append(Spacer(1, 8))
    clean_abstract = re.sub(r"\*\*|\*", "", abstract_text).strip()
    story.append(Paragraph(clean_abstract, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 5: CONTENTS
    # -------------------------------------------------------------------------
    story.append(Paragraph("CONTENTS", style_h1_red))
    story.append(Spacer(1, 8))
    toc_data = [
        ["CHAPTER NO.", "TITLE", "PAGE NO."],
        ["", "ABSTRACT", "4"],
        ["1", "INTRODUCTION", "7"],
        ["2", "LITERATURE SURVEY", "11"],
        ["3", "SYSTEM ARCHITECTURE & METHODOLOGY", "14"],
        ["4", "EXPERIMENTAL RESULTS & EVALUATION", "18"],
        ["5", "CONCLUSION & FUTURE SCOPE", "20"],
        ["6", "REFERENCES", "24"]
    ]
    t_toc = Table(toc_data, colWidths=[1.3 * inch, 4.2 * inch, 0.9 * inch])
    t_toc.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), color_red),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, 0), 1, color_red),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 6: LIST OF FIGURES
    # -------------------------------------------------------------------------
    story.append(Paragraph("LIST OF FIGURES", style_h1_red))
    story.append(Spacer(1, 8))
    lof_data = [
        ["FIG. NO.", "FIGURE NAME", "PAGE NO."],
        ["1.2", f"Core Operational Analysis for {title[:30]}", "8"],
        ["3.1", f"Complete System Architecture for {title[:30]}", "15"],
        ["4.1", f"Performance Benchmark Evaluation for {title[:30]}", "19"]
    ]
    t_lof = Table(lof_data, colWidths=[1.3 * inch, 4.2 * inch, 0.9 * inch])
    t_lof.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), color_red),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, 0), 1, color_red),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
    ]))
    story.append(t_lof)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # CHAPTERS 1 TO 6
    # -------------------------------------------------------------------------
    for ch in chapters:
        ch_num = ch["num"]
        ch_title = ch["title"]
        story.append(Paragraph(f"CHAPTER {ch_num}", style_h1_red))
        story.append(Paragraph(ch_title, style_h1_red))
        story.append(Spacer(1, 8))

        for sec in ch["sections"]:
            sec_heading = sec[0]
            sec_body = sec[1]

            if sec_heading:
                story.append(Paragraph(sec_heading, style_h2_red))

            # Clean markdown formatting and write paragraphs
            clean_body = re.sub(r"\*\*|\*", "", sec_body).strip()
            paras = clean_body.split("\n\n")
            for p in paras:
                if p.strip():
                    story.append(Paragraph(p.strip().replace("\n", " "), style_body))

            story.append(Spacer(1, 4))

        # Insert Topic Diagrams
        if ch_num == 1 and images.get("img_slot_1") and os.path.exists(images["img_slot_1"]):
            story.append(Spacer(1, 8))
            story.append(RLImage(images["img_slot_1"], width=5.5 * inch, height=3.0 * inch))
            story.append(Paragraph(f"Fig 1.2: Core Challenges & Operational Analysis for {title}", style_caption))
            story.append(Spacer(1, 8))

        elif ch_num == 3 and images.get("img_slot_2") and os.path.exists(images["img_slot_2"]):
            story.append(Spacer(1, 8))
            story.append(RLImage(images["img_slot_2"], width=5.5 * inch, height=3.0 * inch))
            story.append(Paragraph(f"Fig 3.1: Complete End-to-End System Architecture for {title}", style_caption))
            story.append(Spacer(1, 8))

        elif ch_num == 4 and images.get("img_slot_3") and os.path.exists(images["img_slot_3"]):
            story.append(Spacer(1, 8))
            story.append(RLImage(images["img_slot_3"], width=5.5 * inch, height=3.0 * inch))
            story.append(Paragraph(f"Fig 4.1: Empirical Benchmarking and Validation Results for {title}", style_caption))
            story.append(Spacer(1, 8))

        story.append(PageBreak())

    # Build document with custom NumberedCanvas for clean bottom page numbers
    doc.build(story, canvasmaker=NumberedCanvas)
    logger.info(f"Academic replica PDF compiled successfully at {output_pdf_path} ({os.path.getsize(output_pdf_path)} bytes)")
    return output_pdf_path
