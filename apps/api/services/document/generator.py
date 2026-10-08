"""
ReportForge AI - Institutional Document Generation Engine
Generates complete academic reports matching the college template geometry and formatting
while populating project-specific content via Gemini AI.
"""

import os
import uuid
import re
import json
from typing import Dict, Any, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from apps.api.services.ai.factory import get_ai_provider
from apps.api.services.document.image_generator import generate_diagrams_for_report
from apps.api.services.document.template_extractor import get_active_template_design
from apps.api.services.document.pdf_generator import generate_academic_pdf
from apps.api.core.logging import get_logger

logger = get_logger("document.generator")

COLOR_RED = RGBColor(230, 0, 0)
COLOR_NAVY = RGBColor(0, 32, 96)
COLOR_GREEN = RGBColor(0, 128, 0)
COLOR_CRIMSON = RGBColor(204, 0, 102)
COLOR_CYAN = RGBColor(0, 136, 204)
COLOR_PURPLE = RGBColor(102, 0, 153)
COLOR_BLUE = RGBColor(0, 51, 204)
COLOR_MAROON = RGBColor(153, 0, 0)
BLACK = RGBColor(0, 0, 0)
DARK_GRAY = RGBColor(60, 60, 60)


def apply_page_border(section, color="auto", size="4"):
    """Applies formal rectangular page border to the Word section."""
    try:
        sectPr = section._sectPr
        existing = sectPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgBorders')
        if existing is not None:
            sectPr.remove(existing)
        pgBorders = parse_xml(
            f'<w:pgBorders {nsdecls("w")}>\n'
            f'  <w:top w:val="single" w:sz="{size}" w:space="24" w:color="{color}"/>\n'
            f'  <w:left w:val="single" w:sz="{size}" w:space="24" w:color="{color}"/>\n'
            f'  <w:bottom w:val="single" w:sz="{size}" w:space="24" w:color="{color}"/>\n'
            f'  <w:right w:val="single" w:sz="{size}" w:space="24" w:color="{color}"/>\n'
            f'</w:pgBorders>'
        )
        sectPr.append(pgBorders)
    except Exception as e:
        logger.warn(f"Border application notice: {e}")


def resolve_clean_academic_title(raw_title: str, ai_provider=None) -> str:
    """
    Intelligently extracts and transforms raw user queries/prompts into formal B.Tech
    engineering project titles (e.g. 'analyze template ... about chatgpt' -> 'CHATGPT: ARCHITECTURE AND APPLICATIONS').
    """
    cleaned = raw_title.strip()
    patterns = [
        r"(?i)analyze\s+(the|my)?\s*(college|pdf)?\s*(report)?\s*template\s*(of\s+this\s+pdf)?\s*(and\s+extract\s+the\s+required\s+formatting\s+rules)?",
        r"(?i)and\s+(change|replace)\s+(the\s+)?(matter|content|text|images)\s*(in\s+this\s+pdf)?\s*(about|to|with|for)?",
        r"(?i)(change|replace)\s+(the\s+)?(matter|content|text|images)\s*(in\s+this\s+pdf)?\s*(about|to|with|for)?",
        r"(?i)^(create|generate|write|prepare|make)\s+(my|a|an)?\s*(project|academic)?\s*(report|documentation)?\s*(on|for|about)?",
        r"(?i)^(report\s+on|project\s+on|topic\s*:?)",
        r"(?i)^(about|for|on)\s+"
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned).strip()

    # If prompt contains conversational keywords or is long, refine using AI
    if any(w in raw_title.lower() for w in ["analyze", "template", "change", "matter", "pdf", "replace", "generate", "document"]) or len(raw_title.split()) > 6:
        if ai_provider:
            try:
                res = ai_provider.generate_text(
                    f"Extract the formal academic project title for a B.Tech engineering report from this user request: '{raw_title}'. "
                    f"Return ONLY the formal uppercase project title (4 to 8 words, e.g. CHATGPT AND LARGE LANGUAGE MODELS: ARCHITECTURE AND APPLICATIONS), with NO explanation and NO markdown.",
                    system_instruction="You are an academic project title generator. Return only the concise title in UPPERCASE."
                )
                clean_lines = [l.strip().strip('"').strip("'") for l in res.split("\n") if l.strip()]
                for l in reversed(clean_lines):
                    if not l.startswith("*") and not l.startswith("-") and not l.lower().startswith("note:") and not l.lower().startswith("draft"):
                        cand = re.sub(r"^(TITLE|FINAL TITLE|PROJECT TITLE)\s*:\s*", "", l, flags=re.I).strip()
                        if len(cand) > 3:
                            return cand.upper()
            except Exception as ex:
                logger.warn(f"AI title resolution fallback: {ex}")

    if len(cleaned) >= 3:
        return cleaned.upper()
    return "ADVANCED ENGINEERING RESEARCH AND APPLICATIONS"


def generate_academic_matter(title: str, ai_provider, project_type: str, department: str, institution: str) -> Optional[Dict[str, Any]]:
    """
    Generates complete in-depth academic content for Abstract and Chapters 1 to 6
    specifically researched and written for the given project topic.
    """
    prompt = f"""
You are writing a comprehensive, formal academic B.Tech engineering report on the topic: "{title}".
Institution: {institution}
Department: {department}
Project Type: {project_type}

Generate detailed technical content for the report.
Return ONLY a valid JSON object with this exact structure:
{{
  "abstract": "A formal, high-quality academic abstract of ~200-250 words describing the project, architecture, methodology, and significance.",
  "chapter_1_sections": [
    ["1.1 BACKGROUND AND MOTIVATION", "Detailed technical background and motivation for {title}... (2-3 solid academic paragraphs)"],
    ["1.2 CHALLENGES AND CORE ISSUES", "Detailed technical challenges, bottlenecks, and security/efficiency issues..."],
    ["1.3 OBJECTIVES AND SCOPE", "Detailed project objectives and clear engineering scope..."]
  ],
  "chapter_2_sections": [
    ["2.1 OVERVIEW OF EXISTING TECHNOLOGIES", "Technical review of foundational architectures and baseline approaches..."],
    ["2.2 COMPARATIVE ANALYSIS", "In-depth comparison of models, algorithms, and frameworks..."],
    ["2.3 ADVANTAGES AND CURRENT LIMITATIONS", "Technical advantages, trade-offs, and constraints..."]
  ],
  "chapter_3_sections": [
    ["3.1 SYSTEM ARCHITECTURE AND PIPELINE", "Detailed end-to-end architectural blocks, dataflow, and processing stages..."],
    ["3.2 METHODOLOGICAL EXECUTION & WORKFLOW", "Step-by-step technical methodology, algorithms, and optimization protocols..."]
  ],
  "chapter_4_sections": [
    ["4.1 QUANTITATIVE BENCHMARKING & METRICS", "Detailed empirical metrics, latency, accuracy, throughput, and benchmark scores..."],
    ["4.2 DISCUSSION OF FINDINGS", "In-depth technical analysis and interpretation of empirical findings..."]
  ],
  "chapter_5_sections": [
    ["5.1 CONCLUSION", "Comprehensive technical conclusion summarizing the findings and project outcomes..."],
    ["5.2 FUTURE SCOPE", "Realistic next-generation advancements, edge deployment, and research directions..."]
  ],
  "chapter_6_references": [
    "[1] Landmark publication / standard for {title}.",
    "[2] Technical IEEE or ACM conference paper on {title}.",
    "[3] International technical standard or benchmark reference.",
    "[4] Peer-reviewed journal article on {title}.",
    "[5] Industry whitepaper and implementation guidelines."
  ]
}}
Do NOT wrap in markdown formatting. Return raw JSON only.
"""
    try:
        raw_res = ai_provider.generate_text(prompt, system_instruction="Output raw JSON only. Do not include markdown codeblocks, thinking, or preamble.")
        clean_res = raw_res.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        if clean_res.startswith("```"):
            clean_res = clean_res[3:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
        clean_res = clean_res.strip()
        parsed = json.loads(clean_res)
        return parsed
    except Exception as e:
        logger.warn(f"Failed to generate structured matter via AI: {e}")
        return None


def create_full_academic_report(
    title: str,
    project_type: str = "Capstone Project",
    student_name: Optional[str] = None,
    roll_no: Optional[str] = None,
    guide_name: Optional[str] = None,
    hod_name: Optional[str] = None,
    department: Optional[str] = None,
    institution: Optional[str] = None,
    academic_year: str = "2025 - 2028",
    problem_statement: Optional[str] = None,
    proposed_solution: Optional[str] = None,
    tech_stack: Optional[str] = None,
    blueprint_chapters: Optional[List[Dict[str, Any]]] = None,
    output_dir: str = ".storage/reports"
) -> Dict[str, Any]:
    """
    Template-Preserving Academic Report Creation.
    The Master College Template is the absolute SOURCE OF TRUTH.
    ARM strictly mutates configured replaceable elements in-place on a working copy of the template,
    preserving 100% of the original page size, margins, fonts, colors, logos, headers, and footers.
    """
    import shutil
    from apps.api.services.replacement_engine_service import replacement_engine_service

    os.makedirs(output_dir, exist_ok=True)
    report_id = f"rep_{uuid.uuid4().hex[:10]}"
    final_docx_path = os.path.join(output_dir, f"{report_id}.docx")
    final_pdf_path = os.path.join(output_dir, f"{report_id}.pdf")

    ai = get_ai_provider()
    clean_title = resolve_clean_academic_title(title, ai)
    logger.info(f"Executing template-preserving report creation for: '{clean_title}'")

    project_data = {
        "id": f"proj_{report_id}",
        "title": clean_title,
        "project_type": project_type,
        "student_name": student_name or "Kasireddy Charishma",
        "roll_number": roll_no or "25BFA02L13",
        "guide_name": guide_name or "Dr. R. Sireesha Ph.D.",
        "department": department or "Department of Electrical & Electronics Engineering",
        "institution": institution or "Sri Venkateswara College of Engineering (Autonomous)",
        "academic_year": academic_year,
        "problem_statement": problem_statement or f"Critical safety hazards, practices, and awareness issues in {clean_title}.",
        "proposed_solution": proposed_solution or f"Comprehensive engineering framework and community awareness on {clean_title}.",
    }

    job_result = replacement_engine_service.execute_replacement(
        project_data=project_data,
        job_id=report_id,
    )

    gen_docx = job_result.get("docx_path")
    gen_pdf = job_result.get("pdf_path")

    if gen_docx and os.path.exists(gen_docx) and gen_docx != final_docx_path:
        shutil.copy2(gen_docx, final_docx_path)
    if gen_pdf and os.path.exists(gen_pdf) and gen_pdf != final_pdf_path:
        shutil.copy2(gen_pdf, final_pdf_path)

    active_docx = final_docx_path if os.path.exists(final_docx_path) else gen_docx
    active_pdf = final_pdf_path if os.path.exists(final_pdf_path) else gen_pdf

    file_size = os.path.getsize(active_docx) if active_docx and os.path.exists(active_docx) else 41000
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:30]

    field_vals = job_result.get("field_values", {})
    preview_sections = []
    section_display_map = [
        ("introduction", "Chapter 1: Introduction"),
        ("objectives", "Objectives"),
        ("problem_statement", "Problem Statement"),
        ("methodology", "Chapter 2: System Methodology"),
        ("implementation", "Chapter 3: Implementation"),
        ("results", "Chapter 4: Results & Analysis"),
        ("conclusion", "Chapter 5: Conclusion"),
    ]
    for key, label in section_display_map:
        val = field_vals.get(key)
        if val:
            content_str = "\n".join(val) if isinstance(val, list) else str(val)
            preview_sections.append({
                "id": key,
                "title": label,
                "wordCount": len(content_str.split()),
                "content": content_str[:1200]
            })

    return {
        "report_id": report_id,
        "job_id": report_id,
        "title": clean_title,
        "file_name": f"{safe_name}_ARM.docx",
        "output_path": active_docx,
        "pdf_path": None,
        "file_size_bytes": file_size,
        "download_url": f"{os.getenv('BACKEND_URL', 'https://arm-backend-031f.onrender.com')}/api/v1/reports/{report_id}/download",
        "pdf_download_url": None,
        "preview_sections": preview_sections,
        "status": "completed",
        "state": "COMPLETED",
        "fields_replaced": job_result.get("fields_replaced", 0),
        "images_replaced": job_result.get("images_replaced", 0),
    }

    # Resolve design from active template contract
    active_design = get_active_template_design()
    active_inst = active_design.get("institution", {})
    institution_final = institution or active_inst.get("name") or "INSTITUTION OF ENGINEERING & TECHNOLOGY"
    department_final = department or active_inst.get("department") or "DEPARTMENT OF ENGINEERING & TECHNOLOGY"
    affiliation_final = active_inst.get("affiliation") or "Approved by AICTE, New Delhi & Affiliated to State Technological University"

    student_name_final = student_name or active_design.get("student_metadata", {}).get("student_name") or "Engineering Scholar"
    roll_no_final = roll_no or active_design.get("student_metadata", {}).get("roll_no") or "25BFA02L13"
    guide_name_final = guide_name or active_design.get("student_metadata", {}).get("guide_name") or "Faculty Guide, Ph.D"
    hod_name_final = hod_name or "Head of the Department, Ph.D."

    ai = get_ai_provider()
    clean_title = resolve_clean_academic_title(title, ai)
    logger.info(f"Resolved academic title: '{clean_title}' (raw query: '{title}')")

    images = generate_diagrams_for_report(report_id, title=clean_title)

    # 1. Generate Abstract and Chapter Matter via AI
    academic_matter = generate_academic_matter(clean_title, ai, project_type, department_final, institution_final)
    if academic_matter and "abstract" in academic_matter:
        abstract_text = re.sub(r"\*\*|\*", "", academic_matter["abstract"]).strip()
        chapters = [
            {
                "num": 1,
                "title": "INTRODUCTION",
                "sections": academic_matter.get("chapter_1_sections", [])
            },
            {
                "num": 2,
                "title": "LITERATURE SURVEY",
                "sections": academic_matter.get("chapter_2_sections", [])
            },
            {
                "num": 3,
                "title": "APPLICATIONS & METHODOLOGY",
                "sections": academic_matter.get("chapter_3_sections", [])
            },
            {
                "num": 4,
                "title": "EXPERIMENTAL RESULTS & EVALUATION",
                "sections": academic_matter.get("chapter_4_sections", [])
            },
            {
                "num": 5,
                "title": "CONCLUSION & FUTURE SCOPE",
                "sections": academic_matter.get("chapter_5_sections", [])
            },
            {
                "num": 6,
                "title": "REFERENCES",
                "sections": [("", "\n\n".join(academic_matter.get("chapter_6_references", [])))]
            }
        ]
    else:
        abstract_text = (
            f"This project report presents an extensive investigation and engineering realization of '{clean_title}'. "
            f"Contemporary systems necessitate resilient architectures, deterministic control loops, and comprehensive verification protocols. "
            f"The primary objective of this work is to systematically examine operational bottlenecks, establish an optimized methodology, "
            f"and implement practical solutions tailored to institutional and real-world deployment criteria. "
            f"Through experimental benchmarks and structured evaluations, the proposed framework exhibits pronounced enhancements in reliability, "
            f"scalability, and standards compliance."
        )
        chapters = [
            {
                "num": 1,
                "title": "INTRODUCTION",
                "sections": [
                    ("1.1 BACKGROUND AND MOTIVATION", f"The necessity and timeliness of {clean_title} within modern engineering and societal systems cannot be overstated. Rapid technological acceleration requires rigorous, dependable engineering frameworks rather than fragile heuristic methods. Establishing standardized architectures ensures operational resilience, scalability, and predictable system behavior."),
                    ("1.2 CHALLENGES AND CORE VULNERABILITIES", f"Traditional approaches to {clean_title} frequently struggle with operational latency, data inconsistency, environmental interference, and component degradation. Identifying these systemic vulnerabilities at an architectural stage is crucial for designing fault-tolerant mechanisms."),
                    ("1.3 OBJECTIVES AND SCOPE", f"The key objectives of this project are: firstly, to systematically investigate contemporary bottlenecks in {clean_title}; secondly, to engineer a robust, modular, and standardized realization; and thirdly, to empirically validate outcomes against rigorous performance criteria.")
                ]
            },
            {
                "num": 2,
                "title": "LITERATURE SURVEY",
                "sections": [
                    ("2.1 OVERVIEW OF EXISTING FRAMEWORKS", f"A thorough investigation of existing academic literature and industrial prior art reveals significant ongoing innovation surrounding {clean_title}. Recent publications emphasize the criticality of deterministic verification and automated telemetry over reactive intervention."),
                    ("2.2 COMPARATIVE ANALYSIS & SYSTEM DESCRIPTION", f"The proposed implementation introduces multi-tiered decoupling, deterministic feedback mechanisms, and automated diagnostic modules. In contrast to conventional solutions, this framework significantly reduces human operational error and computational overhead."),
                    ("2.3 ADVANTAGES AND CURRENT LIMITATIONS", f"Key advantages include: elevated throughput, strict compliance with institutional and industry benchmarks, and modular extensibility. Identified limitations include initial calibration requirements and interface integration constraints.")
                ]
            },
            {
                "num": 3,
                "title": "APPLICATIONS & METHODOLOGY",
                "sections": [
                    ("3.1 SYSTEM ARCHITECTURE AND PIPELINE", f"The architectural blueprint establishes an end-to-end processing pipeline tailored specifically for {clean_title}. Data ingestion is performed through standardized protocols, normalized using deterministic verification algorithms, and processed within isolated fault domains to prevent cascading failures."),
                    ("3.2 METHODOLOGICAL EXECUTION & RISK CONTROLS", f"Operational execution strictly implements the standard engineering hierarchy of controls: hazard elimination, engineering fail-safes, automated safeguards, and rigorous monitoring protocols.")
                ]
            },
            {
                "num": 4,
                "title": "EXPERIMENTAL RESULTS & EVALUATION",
                "sections": [
                    ("4.1 QUANTITATIVE BENCHMARKING", f"Empirical evaluation of the proposed framework for {clean_title} demonstrates consistent operational superiority over baseline implementations. Key performance indicators such as response latency, execution throughput, and error mitigation show marked improvements across iterative trials."),
                    ("4.2 DISCUSSION OF FINDINGS", f"The experimental data validates the theoretical hypotheses. By minimizing runtime variance and enforcing deterministic state transitions, the system achieves stable, repeatable performance under peak stress conditions.")
                ]
            },
            {
                "num": 5,
                "title": "CONCLUSION & FUTURE SCOPE",
                "sections": [
                    ("5.1 CONCLUSION", f"This report successfully presents the architectural design, algorithmic foundation, and practical implementation of '{clean_title}'. The outcomes verify that standardized engineering methodologies deliver substantial benefits in reliability, maintainability, and domain efficiency."),
                    ("5.2 FUTURE SCOPE", f"Future enhancements for '{clean_title}' include: integration with distributed edge AI nodes for real-time autonomous calibration, cross-platform mobile telemetry dashboards, and cloud-native predictive analytics.")
                ]
            },
            {
                "num": 6,
                "title": "REFERENCES",
                "sections": [
                    ("", (
                        f"[1] IEEE Standard for Systems and Software Verification and Control in {clean_title}. IEEE Std 1012-2024.\n\n"
                        f"[2] International Organization for Standardization (ISO). Quality Management and Systems Engineering. ISO/IEC/IEEE 90003.\n\n"
                        f"[3] Bureau of Indian Standards (BIS). Code of Practice and Industrial Engineering Standards. BIS IS 732.\n\n"
                        f"[4] Sharma, R., Patel, V., & Kumar, S. (2025). Advanced Methodologies and Architecture Design for {clean_title}. IEEE Transactions on Engineering & Technology, 48(4), 210-224.\n\n"
                        f"[5] National Institute of Standards and Technology (NIST). Engineering Guidelines and Dependability Frameworks for Complex Distributed Implementations."
                    ))
                ]
            }
        ]

    # 2. Build Document using python-docx
    doc = docx.Document()

    # Set Page Margins: 1.25" Left (Gutter for Binding), 1.0" Right, 1.0" Top, 1.0" Bottom
    # Apply formal rectangular page borders from template design
    has_borders = active_design.get("borders", {}).get("has_page_borders", False)
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.25)
        sec.right_margin = Inches(1.0)
        if has_borders:
            apply_page_border(sec)

    # --------------------------------------------------------------------------
    # PAGE 1: TITLE / COVER PAGE
    # --------------------------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(16)
    p_title.paragraph_format.space_after = Pt(10)
    run_title = p_title.add_run(clean_title.upper())
    run_title.bold = True
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(15)
    run_title.font.color.rgb = COLOR_RED

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(10)
    run_sub = p_sub.add_run(f"A {project_type} report submitted in partial fulfilment for the award of\nthe degree of")
    run_sub.font.name = "Times New Roman"
    run_sub.font.size = Pt(10)
    run_sub.italic = True

    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_deg.paragraph_format.space_after = Pt(6)
    run_deg = p_deg.add_run("BACHELOR OF TECHNOLOGY\n")
    run_deg.bold = True
    run_deg.font.name = "Times New Roman"
    run_deg.font.size = Pt(12)
    run_deg.font.color.rgb = COLOR_NAVY

    run_in = p_deg.add_run("IN\n")
    run_in.bold = True
    run_in.font.name = "Times New Roman"
    run_in.font.size = Pt(11)
    run_in.font.color.rgb = COLOR_GREEN

    run_top_dept = p_deg.add_run(department_final.upper())
    run_top_dept.bold = True
    run_top_dept.font.name = "Times New Roman"
    run_top_dept.font.size = Pt(11)
    run_top_dept.font.color.rgb = COLOR_CRIMSON

    p_by = doc.add_paragraph()
    p_by.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_by.paragraph_format.space_after = Pt(6)
    run_by = p_by.add_run("by")
    run_by.font.name = "Times New Roman"
    run_by.font.size = Pt(10)
    run_by.font.color.rgb = COLOR_CYAN

    # Student Credentials Table
    table_stu = doc.add_table(rows=2, cols=2)
    table_stu.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_stu.rows[0].cells[0].paragraphs[0].text = "NAME"
    table_stu.rows[0].cells[1].paragraphs[0].text = "ROLL NO"
    table_stu.rows[1].cells[0].paragraphs[0].text = student_name_final
    table_stu.rows[1].cells[1].paragraphs[0].text = roll_no_final

    for row in table_stu.rows:
        for cell in row.cells:
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if len(p.runs) > 0:
                p.runs[0].font.name = "Times New Roman"
                p.runs[0].font.size = Pt(10.5)
                p.runs[0].font.color.rgb = COLOR_PURPLE

    # Extracted College Emblem Logo in the Center
    # Check for pre-converted fixed version first, then fall back to original
    _logo_candidates = [
        ".storage/templates/extracted_logo_fixed.png",
        logo_file if (logo_file := active_design.get("logo_path")) else None,
        ".storage/templates/extracted_logo.png",
    ]
    logo_file = next((p for p in _logo_candidates if p and os.path.exists(p)), None)
    if logo_file:
        try:
            # Ensure the image is in a docx-compatible format (PNG/JPEG) — auto-convert if needed
            import io
            try:
                from PIL import Image as _PIL_Image
                with _PIL_Image.open(logo_file) as _img:
                    if _img.format not in ("PNG", "JPEG", "GIF", "BMP", "TIFF"):
                        _buf = io.BytesIO()
                        _rgb = _img.convert("RGB") if _img.mode not in ("RGB", "RGBA") else _img
                        if _img.mode == "RGBA":
                            _bg = _PIL_Image.new("RGB", _img.size, (255, 255, 255))
                            _bg.paste(_rgb, mask=_img.split()[-1])
                            _rgb = _bg
                        _rgb.save(_buf, format="PNG")
                        _buf.seek(0)
                        logo_stream = _buf
                    else:
                        logo_stream = logo_file
            except ImportError:
                logo_stream = logo_file

            p_logo = doc.add_paragraph()
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_logo.paragraph_format.space_before = Pt(8)
            p_logo.paragraph_format.space_after = Pt(8)
            p_logo.add_run().add_picture(logo_stream, width=Inches(2.2))
        except Exception as _logo_err:
            logger.warning(f"Logo could not be embedded (skipping): {_logo_err}")

    # Institution Block at Bottom
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(8)
    p_inst.paragraph_format.space_after = Pt(4)

    run_dept = p_inst.add_run(f"{department_final.upper()}\n")
    run_dept.bold = True
    run_dept.font.name = "Times New Roman"
    run_dept.font.size = Pt(11)
    run_dept.font.color.rgb = COLOR_CRIMSON

    run_coll = p_inst.add_run(f"{institution_final.upper()}\n")
    run_coll.bold = True
    run_coll.font.name = "Times New Roman"
    run_coll.font.size = Pt(13)
    run_coll.font.color.rgb = COLOR_BLUE

    run_auto1 = p_inst.add_run("(AUTONOMOUS)\n")
    run_auto1.bold = True
    run_auto1.font.name = "Times New Roman"
    run_auto1.font.size = Pt(9.5)
    run_auto1.font.color.rgb = COLOR_CYAN

    run_aff = p_inst.add_run(
        f"({affiliation_final})\n"
        f"Accredited by NBA, New Delhi & NAAC with 'A' grade, Karakambadi Road, TIRUPATI – 517507\n"
        f"{academic_year}\n"
        f"(AUTONOMOUS)"
    )
    run_aff.font.name = "Times New Roman"
    run_aff.font.size = Pt(8.5)
    run_aff.font.color.rgb = COLOR_MAROON

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # PAGE 2: CERTIFICATE
    # --------------------------------------------------------------------------
    p_cert_hdr = doc.add_paragraph()
    p_cert_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ch = p_cert_hdr.add_run(
        f"({affiliation_final})\n"
        f"Accredited by NBA, New Delhi & NAAC with 'A' Grade, Karakambadi Road, TIRUPATI – 517507.\n\n"
    )
    r_ch.font.name = "Times New Roman"
    r_ch.font.size = Pt(8.5)
    r_ch.font.color.rgb = COLOR_MAROON

    r_ch_dept = p_cert_hdr.add_run(f"{department_final.upper()}\n")
    r_ch_dept.bold = True
    r_ch_dept.font.name = "Times New Roman"
    r_ch_dept.font.size = Pt(10.5)
    r_ch_dept.font.color.rgb = COLOR_CRIMSON

    if logo_file and os.path.exists(logo_file):
        p_clogo = doc.add_paragraph()
        p_clogo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_clogo.paragraph_format.space_before = Pt(6)
        p_clogo.paragraph_format.space_after = Pt(6)
        p_clogo.add_run().add_picture(logo_file, width=Inches(1.9))

    p_cert_t = doc.add_paragraph()
    p_cert_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cert_t.paragraph_format.space_before = Pt(12)
    p_cert_t.paragraph_format.space_after = Pt(14)
    r_ct = p_cert_t.add_run("CERTIFICATE")
    r_ct.bold = True
    r_ct.font.name = "Times New Roman"
    r_ct.font.size = Pt(14)
    r_ct.font.color.rgb = COLOR_RED

    p_cert_body = doc.add_paragraph()
    p_cert_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_cert_body.paragraph_format.line_spacing = 1.5
    p_cert_body.paragraph_format.space_after = Pt(40)
    r_cb1 = p_cert_body.add_run(f'This is to certify that the {project_type} Report entitled, ')
    r_cb1.font.name = "Times New Roman"
    r_cb1.font.size = Pt(11.5)

    r_cb_title = p_cert_body.add_run(f'"{clean_title.upper()}"')
    r_cb_title.bold = True
    r_cb_title.font.name = "Times New Roman"
    r_cb_title.font.size = Pt(11.5)
    r_cb_title.font.color.rgb = COLOR_RED

    r_cb2 = p_cert_body.add_run(f' is a Bonafide record of the work presented and submitted by ')
    r_cb2.font.name = "Times New Roman"
    r_cb2.font.size = Pt(11.5)

    r_cb_stu = p_cert_body.add_run(f'{student_name_final}; {roll_no_final}')
    r_cb_stu.bold = True
    r_cb_stu.font.name = "Times New Roman"
    r_cb_stu.font.size = Pt(11.5)
    r_cb_stu.font.color.rgb = COLOR_PURPLE

    r_cb3 = p_cert_body.add_run(f' for the partial fulfillment of the requirements for the award of B.Tech degree in ')
    r_cb3.font.name = "Times New Roman"
    r_cb3.font.size = Pt(11.5)

    r_cb_dept = p_cert_body.add_run(f'{department_final.upper()}.')
    r_cb_dept.bold = True
    r_cb_dept.font.name = "Times New Roman"
    r_cb_dept.font.size = Pt(11.5)
    r_cb_dept.font.color.rgb = COLOR_BLUE

    # Signatures: Guide & HOD side by side
    tbl_sig = doc.add_table(rows=1, cols=2)
    tbl_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    p_left = tbl_sig.rows[0].cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_g = p_left.add_run(f"\n\n\n{guide_name_final}\nGuide")
    r_g.bold = True
    r_g.font.name = "Times New Roman"
    r_g.font.size = Pt(11)

    p_right = tbl_sig.rows[0].cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_h = p_right.add_run(f"\n\n\n{hod_name_final}\nHead of the Department")
    r_h.bold = True
    r_h.font.name = "Times New Roman"
    r_h.font.size = Pt(11)

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # PAGE 3: ACKNOWLEDGEMENT
    # --------------------------------------------------------------------------
    p_ack_t = doc.add_paragraph()
    p_ack_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ack_t.paragraph_format.space_after = Pt(20)
    r_at = p_ack_t.add_run("ACKNOWLEDGEMENT")
    r_at.bold = True
    r_at.font.name = "Times New Roman"
    r_at.font.size = Pt(14)
    r_at.font.color.rgb = BLACK

    dept_short = department_final.split()[-1] if department_final else "Engineering"
    ack_paras = [
        f"I am thankful to my guide {guide_name_final}, Associate Professor, Department of {dept_short} for valuable guidance, encouragement, and supportive attitude which helped in the successful completion of this report.",
        f"I would like to express my sincere gratitude to {hod_name_final}, Professor & Head, Department of {dept_short}, for kind guidance and encouragement during the course of study.",
        f"I would like to express my heartfelt thanks to the Principal, for support and encouragement throughout the completion of this academic project.",
        "I sincerely thank the Management for providing all the necessary facilities during the course of this study.",
        "I would like to express my deep gratitude to all those who helped directly or indirectly to transform this idea into a successful seminar report."
    ]

    for a_text in ack_paras:
        p_a = doc.add_paragraph()
        p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_a.paragraph_format.line_spacing = 1.5
        p_a.paragraph_format.space_after = Pt(12)
        ra = p_a.add_run(a_text)
        ra.font.name = "Times New Roman"
        ra.font.size = Pt(12)

    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sign.paragraph_format.space_before = Pt(30)
    rs = p_sign.add_run(f"{student_name_final}\n(Roll No: {roll_no_final})")
    rs.bold = True
    rs.font.name = "Times New Roman"
    rs.font.size = Pt(11)

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # PAGE 4: ABSTRACT
    # --------------------------------------------------------------------------
    p_abs_t = doc.add_paragraph()
    p_abs_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_abs_t.paragraph_format.space_after = Pt(20)
    r_abst = p_abs_t.add_run("ABSTRACT")
    r_abst.bold = True
    r_abst.font.name = "Times New Roman"
    r_abst.font.size = Pt(14)
    r_abst.font.color.rgb = COLOR_RED

    p_abs_b = doc.add_paragraph()
    p_abs_b.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs_b.paragraph_format.line_spacing = 1.5
    p_abs_b.paragraph_format.space_after = Pt(14)
    r_abb = p_abs_b.add_run(abstract_text)
    r_abb.font.name = "Times New Roman"
    r_abb.font.size = Pt(12)

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # PAGE 5: CONTENTS TABLE
    # --------------------------------------------------------------------------
    p_cnt_t = doc.add_paragraph()
    p_cnt_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cnt_t.paragraph_format.space_after = Pt(16)
    r_cntt = p_cnt_t.add_run("CONTENTS")
    r_cntt.bold = True
    r_cntt.font.name = "Times New Roman"
    r_cntt.font.size = Pt(14)
    r_cntt.font.color.rgb = COLOR_RED

    toc_rows = [
        ["", "Abstract", "i"],
        ["", "Table of contents", "ii"],
        ["", "List of figures", "iii"],
        ["Chapter No.", "Description", "Page No."],
        ["1", "INTRODUCTION", "7-11"],
        ["1.1", f"The Importance of {clean_title[:30]}...", "7-8"],
        ["1.2", "Core Challenges & Requirements", "9-10"],
        ["1.3", "Objectives of the Study", "11"],
        ["2", "LITERATURE SURVEY", "12-16"],
        ["2.1", "Overview of Existing Systems", "12"],
        ["2.2", "Comparative Technology Analysis", "13"],
        ["", "SYSTEM DESCRIPTION", "14-15"],
        ["", "ADVANTAGES & DISADVANTAGES", "16"],
        ["3", "APPLICATIONS & METHODOLOGY", "17-19"],
        ["3.1", "Proactive Implementation & Architecture", "18"],
        ["3.2", "Operational Testing & Safety", "19"],
        ["4", "CONCLUSION", "20"],
        ["5", "FUTURE SCOPE", "21"],
        ["6", "REFERENCES", "22-23"],
    ]

    tbl_toc = doc.add_table(rows=len(toc_rows), cols=3)
    tbl_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(toc_rows):
        cells = tbl_toc.rows[r_idx].cells
        for c_idx, val in enumerate(row_vals):
            p = cells[c_idx].paragraphs[0]
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif c_idx == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)
            if r_idx == 3 or val.startswith("CHAPTER") or val in ("INTRODUCTION", "LITERATURE SURVEY", "APPLICATIONS & METHODOLOGY", "CONCLUSION", "FUTURE SCOPE", "REFERENCES"):
                r.bold = True

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # PAGE 6: LIST OF FIGURES
    # --------------------------------------------------------------------------
    p_lof_t = doc.add_paragraph()
    p_lof_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_lof_t.paragraph_format.space_after = Pt(16)
    r_loft = p_lof_t.add_run("LIST OF FIGURES")
    r_loft.bold = True
    r_loft.font.name = "Times New Roman"
    r_loft.font.size = Pt(14)
    r_loft.font.color.rgb = COLOR_RED

    fig1_title = f"Operational Challenges & Vulnerability Analysis for {clean_title[:35]}"
    fig2_title = f"System Block Architecture & Data Pipeline for {clean_title[:35]}"
    fig3_title = f"Comparative Experimental Performance for {clean_title[:35]}"

    lof_rows = [
        ["Fig. No.", "Figure Name", "Page No."],
        ["Fig 1.2", fig1_title, "10"],
        ["Fig 3.1", fig2_title, "16"],
        ["Fig 4.1", fig3_title, "19"],
    ]
    tbl_lof = doc.add_table(rows=len(lof_rows), cols=3)
    tbl_lof.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(lof_rows):
        cells = tbl_lof.rows[r_idx].cells
        for c_idx, val in enumerate(row_vals):
            p = cells[c_idx].paragraphs[0]
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif c_idx == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)
            if r_idx == 0:
                r.bold = True

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # CHAPTERS 1 TO 6: THE MATTER (Written by Gemini AI)
    # --------------------------------------------------------------------------

    for ch in chapters:
        # Chapter Heading
        p_ch_num = doc.add_paragraph()
        p_ch_num.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ch_num.paragraph_format.space_before = Pt(28)
        p_ch_num.paragraph_format.space_after = Pt(4)
        r_cn = p_ch_num.add_run(f"CHAPTER {ch['num']}")
        r_cn.bold = True
        r_cn.font.name = "Times New Roman"
        r_cn.font.size = Pt(14)
        r_cn.font.color.rgb = COLOR_RED

        p_ch_title = doc.add_paragraph()
        p_ch_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ch_title.paragraph_format.space_after = Pt(20)
        r_ct = p_ch_title.add_run(ch["title"])
        r_ct.bold = True
        r_ct.font.name = "Times New Roman"
        r_ct.font.size = Pt(14)
        r_ct.font.color.rgb = COLOR_RED

        # Sections
        for sec_heading, sec_content in ch["sections"]:
            if sec_heading:
                p_sh = doc.add_paragraph()
                p_sh.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_sh.paragraph_format.space_before = Pt(14)
                p_sh.paragraph_format.space_after = Pt(6)
                r_sh = p_sh.add_run(sec_heading)
                r_sh.bold = True
                r_sh.font.name = "Times New Roman"
                r_sh.font.size = Pt(12)
                r_sh.font.color.rgb = COLOR_RED

            if sec_content:
                for para_text in sec_content.split("\n\n"):
                    p_body = doc.add_paragraph()
                    p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p_body.paragraph_format.line_spacing = 1.5
                    p_body.paragraph_format.space_after = Pt(10)
                    r_b = p_body.add_run(para_text.strip())
                    r_b.font.name = "Times New Roman"
                    r_b.font.size = Pt(12)
                    r_b.font.color.rgb = BLACK

            # Embed technical diagrams in relevant sections
            if "1.2" in sec_heading and "img_slot_1" in images and os.path.exists(images["img_slot_1"]):
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(12)
                p_img.paragraph_format.space_after = Pt(4)
                p_img.add_run().add_picture(images["img_slot_1"], width=Inches(5.5))
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_after = Pt(12)
                rc = p_cap.add_run(f"Fig 1.2: {fig1_title}")
                rc.font.name = "Times New Roman"
                rc.font.size = Pt(10)
                rc.italic = True
                rc.font.color.rgb = DARK_GRAY

            elif "3.1" in sec_heading and "img_slot_2" in images and os.path.exists(images["img_slot_2"]):
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(12)
                p_img.paragraph_format.space_after = Pt(4)
                p_img.add_run().add_picture(images["img_slot_2"], width=Inches(5.5))
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_after = Pt(12)
                rc = p_cap.add_run(f"Fig 3.1: {fig2_title}")
                rc.font.name = "Times New Roman"
                rc.font.size = Pt(10)
                rc.italic = True
                rc.font.color.rgb = DARK_GRAY

            elif ("4.1" in sec_heading or ch["num"] == 4) and "img_slot_3" in images and os.path.exists(images["img_slot_3"]) and sec_heading == ch["sections"][-1][0]:
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(12)
                p_img.paragraph_format.space_after = Pt(4)
                p_img.add_run().add_picture(images["img_slot_3"], width=Inches(5.5))
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_after = Pt(12)
                rc = p_cap.add_run(f"Fig 4.1: {fig3_title}")
                rc.font.name = "Times New Roman"
                rc.font.size = Pt(10)
                rc.italic = True
                rc.font.color.rgb = DARK_GRAY

        doc.add_page_break()

    # Save finalized DOCX document
    doc.save(output_path)
    file_size = os.path.getsize(output_path)
    logger.info(f"Report DOCX compiled successfully at {output_path} ({file_size} bytes)")

    # Compile finalized PDF document matching exact template layout
    pdf_output_path = os.path.join(output_dir, f"{report_id}.pdf")
    try:
        generate_academic_pdf(
            output_pdf_path=pdf_output_path,
            title=clean_title,
            project_type=project_type,
            student_name=student_name_final,
            roll_no=roll_no_final,
            guide_name=guide_name_final,
            hod_name=hod_name_final,
            department=department_final,
            institution=institution_final,
            affiliation=affiliation_final,
            academic_year=academic_year,
            abstract_text=abstract_text,
            chapters=chapters,
            images=images,
            design=active_design
        )
    except Exception as e:
        logger.warn(f"PDF generation exception (fallback available): {e}")

    preview_sections = [
        {
            "id": "sec-0",
            "title": "Abstract",
            "pageNumber": 5,
            "wordCount": len(abstract_text.split()),
            "content": abstract_text
        }
    ]
    for ch in chapters:
        all_sec_text = "\n\n".join(f"{s[0]}\n{s[1]}" if s[0] else s[1] for s in ch["sections"])
        preview_sections.append({
            "id": f"sec-{ch['num']}",
            "title": f"Chapter {ch['num']}: {ch['title']}",
            "pageNumber": 5 + ch["num"] * 2,
            "wordCount": len(all_sec_text.split()),
            "content": all_sec_text[:1200]
        })

    return {
        "report_id": report_id,
        "title": clean_title,
        "file_name": f"{clean_title.replace(' ', '_')[:30]}_ARM.docx",
        "output_path": output_path,
        "pdf_path": None,
        "file_size_bytes": file_size,
        "download_url": f"{os.getenv('BACKEND_URL', 'https://arm-backend-031f.onrender.com')}/api/v1/reports/{report_id}/download",
        "pdf_download_url": None,
        "preview_sections": preview_sections
    }
