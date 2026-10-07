"""
ReportForge AI / ARM — Custom College Template Ingestion & Analysis Service
Stage 15: Upload, Structural Inspection, Safe Mapping, and Preservation of Custom College Templates.
The uploaded college DOCX is the immutable master source of truth.
"""

import os
import io
import re
import uuid
import zipfile
import tempfile
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import docx
from docx.shared import Inches, Pt
from docx.oxml.ns import qn

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.core.database import db_manager
from apps.api.services.storage import get_storage_provider
from packages.replacement_engine.base import FIXED_ELEMENTS, REPLACEABLE_ELEMENTS

logger = get_logger("service.custom_template")

# In-memory store for user-uploaded custom templates (fallback & cache)
_CUSTOM_TEMPLATES_STORE: Dict[str, Any] = {}

# Canonical ARM field definitions for auto-detection and mapping
CANONICAL_ARM_FIELDS = [
    {"key": "project_title", "label": "Project Title", "type": "text", "patterns": [r"project\s*title", r"title\s*of\s*(the)?\s*project", r"seminar\s*title", r"report\s*title"]},
    {"key": "student_name", "label": "Student Name", "type": "text", "patterns": [r"student\s*name", r"name\s*of\s*(the)?\s*student", r"candidate\s*name", r"submitted\s*by"]},
    {"key": "roll_number", "label": "Roll Number / Reg No", "type": "text", "patterns": [r"roll\s*(no|number)", r"reg(ister)?\s*(no|number)", r"hall\s*ticket\s*no", r"usn", r"htno"]},
    {"key": "guide_name", "label": "Guide / Supervisor Name", "type": "text", "patterns": [r"guide\s*name", r"supervisor", r"under\s*the\s*guidance\s*of", r"faculty\s*advisor"]},
    {"key": "department", "label": "Department", "type": "text", "patterns": [r"department\s*of", r"dept\."]},
    {"key": "institution", "label": "College / University Name", "type": "text", "patterns": [r"college\s*of", r"university", r"institute\s*of"]},
    {"key": "academic_year", "label": "Academic Year", "type": "text", "patterns": [r"academic\s*year", r"202[4-9]\s*-\s*202[4-9]"]},
    {"key": "abstract", "label": "Abstract", "type": "long_text", "patterns": [r"abstract", r"executive\s*summary"]},
    {"key": "problem_statement", "label": "Problem Statement", "type": "long_text", "patterns": [r"problem\s*statement", r"statement\s*of\s*problem"]},
    {"key": "introduction", "label": "Introduction", "type": "long_text", "patterns": [r"chapter\s*1", r"introduction", r"background\s*and\s*overview"]},
    {"key": "objectives", "label": "Objectives", "type": "list", "patterns": [r"objectives?", r"aims?\s*and\s*objectives?"]},
    {"key": "methodology", "label": "Methodology", "type": "long_text", "patterns": [r"methodology", r"system\s*design", r"system\s*architecture", r"proposed\s*system"]},
    {"key": "technologies", "label": "Technologies / Tools Used", "type": "list", "patterns": [r"technologies(\s*used)?", r"tools(\s*and\s*technologies)?", r"tech\s*stack"]},
    {"key": "implementation", "label": "Implementation", "type": "long_text", "patterns": [r"implementation", r"implementation\s*details"]},
    {"key": "results", "label": "Results & Discussion", "type": "long_text", "patterns": [r"results?(\s*and\s*discussion)?", r"experimental\s*results?"]},
    {"key": "advantages", "label": "Advantages", "type": "list", "patterns": [r"advantages?", r"merits?"]},
    {"key": "disadvantages", "label": "Disadvantages", "type": "list", "patterns": [r"disadvantages?", r"drawbacks?"]},
    {"key": "problems_observed", "label": "Problems Observed", "type": "list", "patterns": [r"problems\s*(we\s*)?observed", r"challenges\s*observed"]},
    {"key": "limitations", "label": "Limitations", "type": "list", "patterns": [r"limitations?", r"demerits?"]},
    {"key": "future_scope", "label": "Future Scope", "type": "long_text", "patterns": [r"future\s*scope", r"future\s*enhancements?"]},
    {"key": "conclusion", "label": "Conclusion", "type": "long_text", "patterns": [r"conclusion", r"concluding\s*remarks"]},
    {"key": "references", "label": "References", "type": "list", "patterns": [r"references?", r"bibliography"]},
]

# Patterns for negative disqualification when detecting unlabeled project titles
TITLE_DISQUALIFY_PATTERNS = [
    # Boilerplate / agenda / TOC / presentation tags
    r"^agenda$", r"^table\s+of\s+contents$", r"^contents$", r"^index$",
    r"^overview$", r"^abstract$", r"^acknowledgment[s]?$", r"^certificate$",
    r"^declaration$", r"^bonafide\s+certificate$",
    r"^academic\s+report$", r"^project\s+report$", r"^seminar\s+report$", r"^technical\s+report$",
    r"^a\s+report\s+on$", r"^seminar\s+presentation$",
    r"^(a\s+)?(mini|major|seminar|capstone|internship|community\s+service)?\s*(project|seminar|technical)?\s*(report|presentation)\s*(on)?$",
    r"^(on|presentation\s+on|seminar\s+presentation\s+on|project\s+report\s+on)$",
    r"^(thank\s+you|queries\??|questions\??)$",
    r"^.*thank\s+you.*$", r"^.*queries.*$",
    r"^unit[-\s]*\d+$", r"^chapter[-\s]*\d+$",
    # Institutional headers
    r"\bcollege\s+(of|for)\b", r"\buniversity\b", r"\binstitute\s+(of|for)\b",
    r"\bengineering\s+college\b", r"\bpolytechnic\b", r"\bacademy\b",
    r"\bvidya\s*peeth\b", r"\baccredited\s+by\b", r"\baffiliated\s+to\b",
    r"\bapproved\s+by\b", r"\bnaac\b", r"\baicte\b", r"\bnba\b", r"\bugc\b",
    r"\bautonomous\b", r"\bcampus\b", r"\beducation\s+for\b",
    # Department lines
    r"\bdepartment\s+(of|&)\b", r"\bdept\.?\s+(of|&)\b", r"\bschool\s+of\b",
    r"\bcomputer\s+science\b", r"\binformation\s+technology\b",
    r"\belectrical\s+(&|and)\s+electronics\b", r"\belectronics\s+(&|and)\s+communication\b",
    r"\bmechanical\s+engineering\b", r"\bcivil\s+engineering\b",
    # Degree / academic fulfillment
    r"\bbachelor\s+of\b", r"\bmaster\s+of\b", r"\bdoctor\s+of\b", r"\bdiploma\s+in\b",
    r"\bb\.?\s*tech\b", r"\bm\.?\s*tech\b", r"\bb\.?\s*e\.?\b", r"\bm\.?\s*e\.?\b",
    r"\bb\.?\s*sc\b", r"\bm\.?\s*sc\b", r"\bm\.?\s*c\.?\s*a\b", r"\bb\.?\s*c\.?\s*a\b",
    r"\bph\.?d\b", r"\bin\s+partial\s+fulfillment\b", r"\bacademic\s+year\b",
    r"\bacademic\s+session\b", r"\bsemester\b",
    # Student / Guide / Roll number lines
    r"\bsubmitted\s+by\b", r"\bpresented\s+by\b", r"\bguided\s+by\b",
    r"\bunder\s+the\s+guidance\b", r"\bproject\s+guide\b", r"\binternal\s+guide\b",
    r"\bexternal\s+guide\b", r"\bsupervisor\b", r"\bcoordinator\b",
    r"\bhead\s+of\s+department\b", r"\bh\.?o\.?d\b",
    r"\broll\s+no\b", r"\breg(\.|istration)?\s+no\b", r"\bhall\s*ticket\b",
    r"\bhtno\b", r"\busn\b", r"\bpin\s+no\b",
    r"^[0-9]{2}[A-Za-z0-9]{8,10}$",
    # Section headings
    r"^introduction(\s+to.*)?$",
    r"^problem\s+statement$",
    r"^objectives?$",
    r"^methodology$",
    r"^proposed\s+system$",
    r"^literature\s+survey$",
    r"^results?(\s+and\s+discussion)?$",
    r"^conclusion.*$",
    r"^references?$",
    r"^future\s+scope$",
    r"^future\s+directions.*$",
]


class CustomTemplateService:
    """Production service for managing user-uploaded college templates."""

    @staticmethod
    def validate_docx(content: bytes, filename: str) -> None:
        """Validates DOCX format, magic bytes, and integrity."""
        if not filename:
            raise ValueError("Please provide a valid document filename.")

        ext = os.path.splitext(filename)[1].lower()
        if ext != ".docx":
            raise ValueError("Unsupported format. Custom templates must be uploaded in .docx format.")

        if len(content) == 0:
            raise ValueError("The uploaded document is empty.")

        max_bytes = 25 * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError("File is too large. College templates must be under 25MB.")

        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("Invalid document structure. Please upload a valid Microsoft Word (.docx) file.")

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist:
                    raise ValueError("Invalid DOCX archive. Required OpenXML manifest missing.")
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                if total_uncompressed > 100 * 1024 * 1024:
                    raise ValueError("Document package exceeds safety thresholds.")
        except zipfile.BadZipFile:
            raise ValueError("The uploaded .docx file is corrupted or could not be decompressed.")

    @staticmethod
    def validate_template_file(content: bytes, filename: str) -> str:
        """Validates DOCX or PDF format, magic bytes, size, and integrity. Returns extension."""
        if not filename:
            raise ValueError("Please provide a valid document filename.")

        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf" or ext != ".docx":
            raise ValueError("Only DOCX college templates are currently supported.")

        if len(content) == 0:
            raise ValueError("The uploaded document is empty.")

        max_bytes = 25 * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError("File is too large. College templates must be under 25MB.")

        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("Invalid document structure. Please upload a valid Microsoft Word (.docx) file.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist:
                    raise ValueError("Invalid DOCX archive. Required OpenXML manifest missing.")
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                if total_uncompressed > 100 * 1024 * 1024:
                    raise ValueError("Document package exceeds safety thresholds.")
        except zipfile.BadZipFile:
            raise ValueError("The uploaded .docx file is corrupted or could not be decompressed.")

        return ext

    @classmethod
    def _detect_first_page_main_title(cls, doc: docx.Document) -> Optional[Dict[str, Any]]:
        """
        Prioritizes the first page (cover slide/page) to detect the main project title.
        Uses typography (font size, bold), position, line structure, and semantic context.
        Distinguishes project title from college name, department, degree, student details,
        guide details, agenda, and section headings.
        Supports single-paragraph and multiline titles.
        """
        def _score_para(p_idx: int, p_obj: Any) -> Tuple[float, str, float]:
            txt = p_obj.text.strip()
            if not txt or len(txt) < 3:
                return -100.0, "Too short or empty", 0.0

            txt_lower = txt.lower()
            for pat in TITLE_DISQUALIFY_PATTERNS:
                if re.search(pat, txt_lower):
                    return -100.0, f"Disqualified: {pat}", 0.0

            font_sizes = []
            is_bold = False
            for r in p_obj.runs:
                if r.font.size and r.font.size.pt:
                    font_sizes.append(r.font.size.pt)
                if r.bold:
                    is_bold = True
            f_sz = max(font_sizes) if font_sizes else 14.0

            score = f_sz * 1.5
            if f_sz >= 24:
                score += 30.0
            elif f_sz >= 18:
                score += 15.0

            if is_bold:
                score += 20.0

            if p_idx == 0:
                score += 40.0
            elif p_idx == 1:
                score += 30.0
            elif p_idx == 2:
                score += 25.0
            elif p_idx == 3:
                score += 20.0
            elif p_idx <= 5:
                score += 10.0
            else:
                score -= 15.0

            if ":" in txt:
                score += 15.0
            if re.search(r'["“][^"”]+["”]', txt):
                score += 25.0
            if txt.isupper() and len(txt) > 8:
                score += 15.0

            words = len(txt.split())
            if 3 <= words <= 16:
                score += 20.0
            elif words == 2:
                score += 5.0
            elif words == 1 or words > 22:
                score -= 20.0

            return score, "OK", f_sz

        # 1. Primary Search: First 15 non-empty paragraphs (cover page range)
        candidates = []
        for i, p in enumerate(doc.paragraphs[:15]):
            t = p.text.strip()
            if not t:
                continue
            sc, _, f_sz = _score_para(i, p)
            if sc > 0:
                candidates.append((sc, i, p, t, f_sz))

        # Check for multiline titles (combining adjacent paragraphs on cover page)
        for idx in range(len(candidates)):
            sc, i, p_obj, t, f_sz = candidates[idx]
            if i + 1 < len(doc.paragraphs):
                p_next = doc.paragraphs[i + 1]
                t_next = p_next.text.strip()
                if t_next and len(t_next) >= 3:
                    sc_next, _, f_sz_next = _score_para(i + 1, p_next)
                    if sc_next > 0:
                        if t.endswith((":", "-")) or (abs(f_sz - f_sz_next) <= 4.0 and len((t + " " + t_next).split()) <= 18):
                            comb_text = f"{t} {t_next}"
                            comb_score = sc + sc_next + 15.0
                            candidates.append((comb_score, i, p_obj, comb_text, max(f_sz, f_sz_next)))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # 2. Fallback Search: Paragraphs 16 to 40 (only if no confident candidate on page 1)
        if not candidates or candidates[0][0] < 35.0:
            for i, p in enumerate(doc.paragraphs[15:40], start=15):
                t = p.text.strip()
                if not t:
                    continue
                sc, _, f_sz = _score_para(i, p)
                if sc > 0:
                    candidates.append((sc, i, p, t, f_sz))
            candidates.sort(key=lambda x: x[0], reverse=True)

        if not candidates or candidates[0][0] < 35.0:
            return None

        best_score, best_idx, best_p, best_text, best_sz = candidates[0]

        # Extract inner title if quotes present
        inner_title = best_text
        q_match = re.search(r'["“]([^"”]+)["”]', best_text)
        if q_match:
            inner_title = q_match.group(1).strip()

        logger.info(
            f"Detected first-page main title (Paragraph {best_idx + 1}, score={best_score:.1f}, "
            f"font_size={best_sz}pt): '{best_text}'"
        )

        return {
            "id": "field_project_title",
            "template_element": best_text,
            "original_text": best_text,
            "inner_title": inner_title,
            "sample_text": best_text[:80],
            "arm_field": "project_title",
            "section_heading": "Project Title",
            "action": "replace",
            "is_replaceable": True,
            "is_explicit_placeholder": False,
            "content_type": "title",
            "layout_metrics": {
                "font_size_pt": best_sz,
                "word_count": len(best_text.split()),
                "char_count": len(best_text),
            },
            "location": f"Paragraph {best_idx + 1} (Cover Page Title)",
            "confidence_score": round(best_score, 1),
        }

    @classmethod
    def analyze_template_docx(cls, file_path: str) -> Dict[str, Any]:
        """
        Inspects the uploaded DOCX template without rebuilding or redesigning it.
        Extracts exact page geometry, candidate text placeholders, images,
        and classifies elements into FIXED vs candidate REPLACEABLE.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Template file not found at: {file_path}")

        doc = docx.Document(file_path)

        # 1. Exact Page Geometry Analysis
        page_settings = {
            "width_in": 8.5,
            "height_in": 11.0,
            "orientation": "portrait",
            "top_margin_in": 1.0,
            "bottom_margin_in": 1.0,
            "left_margin_in": 1.0,
            "right_margin_in": 1.0,
            "sections_count": len(doc.sections),
        }
        if doc.sections:
            sec = doc.sections[0]
            try:
                page_settings["width_in"] = round(sec.page_width.inches, 2)
                page_settings["height_in"] = round(sec.page_height.inches, 2)
                page_settings["orientation"] = "landscape" if sec.page_width > sec.page_height else "portrait"
                page_settings["top_margin_in"] = round(sec.top_margin.inches, 2)
                page_settings["bottom_margin_in"] = round(sec.bottom_margin.inches, 2)
                page_settings["left_margin_in"] = round(sec.left_margin.inches, 2)
                page_settings["right_margin_in"] = round(sec.right_margin.inches, 2)
            except Exception as e:
                logger.warning(f"Failed to read detailed section geometry: {e}")

        # 2. Extract Paragraphs & Tables for Text Placeholder Detection
        candidate_text_fields: List[Dict[str, Any]] = []
        found_arm_keys: set = set()
        seen_placeholders: set = set()

        # Step 2a: Scan for explicit {{...}} brackets
        bracket_pattern = re.compile(r"\{\{([^}]+)\}\}")
        for p_idx, p in enumerate(doc.paragraphs):
            matches = bracket_pattern.findall(p.text)
            for raw_key in matches:
                clean_key = raw_key.strip().lower().replace(" ", "_")
                if clean_key in seen_placeholders:
                    continue
                seen_placeholders.add(clean_key)

                # Map to canonical ARM field if matched
                matched_arm_key = clean_key
                for f_def in CANONICAL_ARM_FIELDS:
                    if f_def["key"] == clean_key or any(re.search(pat, clean_key) for pat in f_def["patterns"]):
                        matched_arm_key = f_def["key"]
                        break

                candidate_text_fields.append({
                    "id": f"field_{len(candidate_text_fields) + 1}",
                    "template_element": f"{{{{{raw_key}}}}}",
                    "sample_text": p.text[:80],
                    "arm_field": matched_arm_key,
                    "action": "replace",
                    "is_explicit_placeholder": True,
                    "location": f"Paragraph {p_idx + 1}",
                })
                found_arm_keys.add(matched_arm_key)

        # Step 2-Title: FIRST-PAGE PRIORITY DETECTION FOR MAIN PROJECT TITLE
        if "project_title" not in found_arm_keys:
            detected_title = cls._detect_first_page_main_title(doc)
            if detected_title:
                candidate_text_fields.insert(0, detected_title)
                found_arm_keys.add("project_title")

        # Identify Table of Contents range to avoid treating TOC index labels as replaceable body matter
        toc_indices = set()
        is_toc = False
        for p_i, p in enumerate(doc.paragraphs[:50]):
            t_u = p.text.strip().upper()
            if "CONTENTS" in t_u or "TABLE OF CONTENTS" in t_u or "INDEX" in t_u:
                is_toc = True
                continue
            if is_toc:
                if len(p.text.strip()) > 70 or re.match(r"^Pg\.?\s*\d+", p.text.strip(), re.IGNORECASE):
                    is_toc = False
                else:
                    toc_indices.add(p_i)

        ACADEMIC_METADATA_KEYS = {
            "student_name", "roll_number", "guide_name", "department",
            "institution", "academic_year", "degree"
        }

        # Step 2b: Scan for explicit text phrases in document if {{...}} were not all present
        for p_idx, p in enumerate(doc.paragraphs[:40]):  # check first 40 paragraphs (cover/intro)
            if p_idx in toc_indices:
                continue
            txt = p.text.strip()
            if not txt or len(txt) > 120:
                continue

            for f_def in CANONICAL_ARM_FIELDS:
                if f_def["key"] in found_arm_keys:
                    continue
                for pat in f_def["patterns"]:
                    if re.search(r"\b" + pat + r"\b", txt, re.IGNORECASE):
                        is_meta = f_def["key"] in ACADEMIC_METADATA_KEYS
                        candidate_text_fields.append({
                            "id": f"field_{len(candidate_text_fields) + 1}",
                            "template_element": txt,
                            "original_text": txt,
                            "sample_text": txt,
                            "arm_field": f_def["key"],
                            "action": "fixed" if is_meta else "replace",
                            "is_explicit_placeholder": False,
                            "is_academic_metadata": is_meta,
                            "location": f"Paragraph {p_idx + 1}",
                        })
                        found_arm_keys.add(f_def["key"])
                        break

        # Step 2c: If project_title is not yet detected, heuristically discover cover page title
        if "project_title" not in found_arm_keys:
            # Check for quoted text on cover page (first 15 paragraphs)
            for p_idx, p in enumerate(doc.paragraphs[:15]):
                txt = p.text.strip()
                if not txt:
                    continue
                quote_match = re.search(r'["“]([^"”]{5,100})["”]', txt)
                if quote_match:
                    full_title = quote_match.group(0).strip()
                    cand_title = quote_match.group(1).strip()
                    f_sz = 24.0
                    if p.runs and p.runs[0].font.size and p.runs[0].font.size.pt:
                        f_sz = round(p.runs[0].font.size.pt, 1)
                    candidate_text_fields.insert(0, {
                        "id": f"field_{len(candidate_text_fields) + 1}",
                        "template_element": full_title,
                        "original_text": full_title,
                        "inner_title": cand_title,
                        "sample_text": txt,
                        "arm_field": "project_title",
                        "action": "replace",
                        "is_explicit_placeholder": False,
                        "layout_metrics": {
                            "font_size_pt": f_sz,
                            "word_count": len(cand_title.split()),
                            "char_count": len(cand_title),
                        },
                        "location": f"Paragraph {p_idx + 1} (Cover Title)",
                    })
                    found_arm_keys.add("project_title")
                    break

            # If still not found, check paragraphs following "ON" / "REPORT ON"
            if "project_title" not in found_arm_keys:
                found_on = False
                for p_idx, p in enumerate(doc.paragraphs[:15]):
                    txt = p.text.strip()
                    if not txt:
                        continue
                    upper = txt.upper()
                    if upper in ("ON", "A PROJECT REPORT ON", "A SEMINAR REPORT ON", "PRESENTATION ON", "PROJECT REPORT ON"):
                        found_on = True
                        continue
                    if found_on:
                        if any(sub in upper for sub in ("SUBMITTED BY", "PRESENTED BY", "GUIDED BY", "DEPARTMENT OF", "BACHELOR OF")):
                            break
                        if len(txt) >= 4:
                            candidate_text_fields.insert(0, {
                                "id": f"field_{len(candidate_text_fields) + 1}",
                                "template_element": txt,
                                "sample_text": txt,
                                "arm_field": "project_title",
                                "action": "replace",
                                "is_explicit_placeholder": False,
                                "location": f"Paragraph {p_idx + 1} (Cover Title)",
                            })
                            found_arm_keys.add("project_title")
                            break

        # Step 2d: Extract Replaceable Topic Matter Across Document Sections / Slides
        is_presentation = page_settings.get("orientation") == "landscape" or any(
            re.match(r"^Pg\.?\s*\d+", p.text.strip(), re.IGNORECASE) for p in doc.paragraphs
        )

        if is_presentation:
            slides_data = []
            current_slide_paras = []
            has_pg_markers = any(re.match(r"^Pg\.?\s*\d+", p.text.strip(), re.IGNORECASE) for p in doc.paragraphs)
            for p_idx, p in enumerate(doc.paragraphs):
                t = p.text.strip()
                if not t:
                    continue
                is_boundary = False
                if has_pg_markers:
                    is_boundary = bool(re.match(r"^Pg\.?\s*\d+", t, re.IGNORECASE))
                else:
                    has_col_br = 'w:br' in p._p.xml and 'column' in p._p.xml
                    is_heading = (p_idx > 0 and len(t) < 50 and t.isupper() and len(t.split()) <= 7 and not t.startswith("P0"))
                    if has_col_br or is_heading:
                        is_boundary = True
                if is_boundary and current_slide_paras:
                    slides_data.append(current_slide_paras)
                    current_slide_paras = [(p_idx, p)]
                else:
                    current_slide_paras.append((p_idx, p))
            if current_slide_paras:
                slides_data.append(current_slide_paras)

            content_slide_idx = 0
            for s_idx, sl in enumerate(slides_data):
                if s_idx == 0:
                    continue  # Cover slide handled above
                if any(p.text.strip().upper() in ("CONTENTS", "AGENDA") or "CONTENTS" in p.text.strip().upper() for _, p in sl):
                    # TOC slide: parse TOC items that are project-specific
                    for p_idx, p in sl:
                        t = p.text.strip()
                        if not t or t.upper() in ("CONTENTS", "AGENDA") or re.match(r"^Pg\.?\s*\d+", t, re.IGNORECASE):
                            continue
                        # Skip fixed running headers / credentials in TOC slide
                        t_upper = t.upper()
                        if (
                            any(lbl in t_upper for lbl in ("ACADEMIC REPORT", "PROJECT REPORT", "SEMINAR REPORT", "TECHNICAL REPORT", "COLLEGE", "DEPARTMENT OF", "UNIVERSITY", "INSTITUTE"))
                            or re.search(r"^(academic|project|seminar|technical)\s+report$", t, re.IGNORECASE)
                            or re.match(r"^(QUERIES\??|Thank\s*You)", t, re.IGNORECASE)
                        ):
                            continue
                        clean_t = t.rstrip(":-").strip()
                        if clean_t.upper() not in ("ABSTRACT", "INTRODUCTION", "OBJECTIVES", "ADVANTAGES AND DISADVANTAGES", "ADVANTAGES & DISADVANTAGES", "PROBLEMS WE OBSERVED", "PROBLEMS OBSERVED", "CONCLUSION", "REFERENCES"):
                            candidate_text_fields.append({
                                "id": f"field_{len(candidate_text_fields) + 1}",
                                "template_element": t,
                                "original_text": t,
                                "sample_text": t,
                                "arm_field": f"toc_item_{p_idx}",
                                "section_heading": "Table of Contents",
                                "action": "replace",
                                "is_replaceable": True,
                                "content_type": "toc_item",
                                "location": f"Slide {s_idx + 1} / Paragraph {p_idx + 1} (TOC)",
                            })
                    continue

                body_entries = [
                    (p_idx, p) for p_idx, p in sl
                    if p.text.strip()
                    and not re.match(r"^(Pg\.?\s*\d+|QUERIES\??|Thank You)", p.text.strip(), re.IGNORECASE)
                    and not re.search(r"^(academic|project|seminar|technical)\s+report$", p.text.strip(), re.IGNORECASE)
                    and not any(k in p.text.strip().upper() for k in ("COLLEGE OF", "DEPARTMENT OF", "ACADEMIC REPORT", "PROJECT REPORT", "SEMINAR REPORT"))
                ]
                if not body_entries:
                    continue

                content_slide_idx += 1
                first_t = body_entries[0][1].text.strip()
                slide_heading = None
                content_items = []

                if body_entries[0][1].style.name.startswith("Heading") or (len(first_t) < 40 and first_t.endswith(":-")) or (len(first_t) < 55 and first_t.isupper() and len(first_t.split()) <= 7):
                    slide_heading = first_t.rstrip(":-")
                    content_items = body_entries[1:]
                else:
                    content_items = body_entries

                mapped_sec_key = None
                if slide_heading:
                    h_upper = slide_heading.upper()
                    if "OBJECTIVE" in h_upper:
                        mapped_sec_key = "objectives"
                    elif "ADVANTAGE" in h_upper:
                        mapped_sec_key = "advantages"
                    elif "DISADVANTAGE" in h_upper:
                        mapped_sec_key = "disadvantages"
                    elif "PROBLEM" in h_upper:
                        mapped_sec_key = "problems_observed"
                    elif "CONCLUSION" in h_upper:
                        mapped_sec_key = "conclusion"
                    elif "REFERENCE" in h_upper:
                        mapped_sec_key = "references"
                    else:
                        mapped_sec_key = f"slide_{s_idx + 1}"
                        # Project-specific heading: register heading itself as replaceable field
                        candidate_text_fields.append({
                            "id": f"field_{len(candidate_text_fields) + 1}",
                            "template_element": first_t,
                            "original_text": first_t,
                            "sample_text": first_t,
                            "arm_field": f"slide_{s_idx + 1}_heading",
                            "section_heading": slide_heading,
                            "action": "replace",
                            "is_replaceable": True,
                            "content_type": "heading",
                            "location": f"Slide {s_idx + 1} Heading",
                        })

                if not mapped_sec_key:
                    all_slide_text = " ".join([p.text.strip() for _, p in content_items])
                    if "In conclusion" in all_slide_text or "Conclusion" in all_slide_text:
                        mapped_sec_key = "conclusion"
                    elif any(k in all_slide_text for k in ("NFPA", "OSHA", "IEEE", "ISO", "Standards", "Regulations")):
                        mapped_sec_key = "references"
                    elif any(k in all_slide_text for k in ("Overloaded Sockets", "Damaged Equipment", "Wiring Faults", "Problems")):
                        mapped_sec_key = "problems_observed"
                    elif content_slide_idx == 1:
                        mapped_sec_key = "abstract"
                    elif content_slide_idx == 2:
                        mapped_sec_key = "introduction"
                    else:
                        mapped_sec_key = f"slide_{s_idx + 1}"

                if not mapped_sec_key:
                    continue

                if len(content_items) == 1:
                    p_idx, p_obj = content_items[0]
                    p_txt = p_obj.text.strip()
                    if p_txt and len(p_txt) > 20:
                        f_sz = 14.0
                        if p_obj.runs and p_obj.runs[0].font.size and p_obj.runs[0].font.size.pt:
                            f_sz = round(p_obj.runs[0].font.size.pt, 1)
                        candidate_text_fields.append({
                            "id": f"field_{len(candidate_text_fields) + 1}",
                            "template_element": p_txt,
                            "original_text": p_txt,
                            "sample_text": p_txt[:80],
                            "arm_field": mapped_sec_key,
                            "section_heading": slide_heading or mapped_sec_key.title(),
                            "action": "replace",
                            "is_replaceable": True,
                            "content_type": "paragraph",
                            "layout_metrics": {
                                "font_size_pt": f_sz,
                                "word_count": len(p_txt.split()),
                                "char_count": len(p_txt),
                            },
                            "location": f"Slide {s_idx + 1} / Paragraph {p_idx + 1}",
                        })
                        found_arm_keys.add(mapped_sec_key)
                else:
                    sub_sec = mapped_sec_key
                    sub_idx = 1
                    for p_idx, p_obj in content_items:
                        p_txt = p_obj.text.strip()
                        if not p_txt or len(p_txt) < 5:
                            continue
                        if p_txt.lower().startswith("disadvantages"):
                            sub_sec = "disadvantages"
                            sub_idx = 1
                            continue
                        if p_txt.lower().startswith("advantages"):
                            sub_sec = "advantages"
                            sub_idx = 1
                            continue

                        field_key = f"{sub_sec}_{sub_idx}"
                        f_sz = 14.0
                        if p_obj.runs and p_obj.runs[0].font.size and p_obj.runs[0].font.size.pt:
                            f_sz = round(p_obj.runs[0].font.size.pt, 1)
                        candidate_text_fields.append({
                            "id": f"field_{len(candidate_text_fields) + 1}",
                            "template_element": p_txt,
                            "original_text": p_txt,
                            "sample_text": p_txt[:80],
                            "arm_field": field_key,
                            "section_heading": slide_heading or sub_sec.title(),
                            "action": "replace",
                            "is_replaceable": True,
                            "content_type": "bullet",
                            "layout_metrics": {
                                "font_size_pt": f_sz,
                                "word_count": len(p_txt.split()),
                                "char_count": len(p_txt),
                            },
                            "location": f"Slide {s_idx + 1} / Paragraph {p_idx + 1}",
                        })
                        found_arm_keys.add(field_key)
                        sub_idx += 1
        else:
            current_chapter = None
            current_chapter_heading = None
            for p_idx, p in enumerate(doc.paragraphs):
                p_txt = p.text.strip()
                if not p_txt:
                    continue
                is_heading = p.style.name.startswith("Heading") or bool(
                    re.match(r"^(\d+\.|\bChapter\s+\d+:?)\s+[A-Z\s]{3,}", p_txt, re.IGNORECASE)
                )
                if is_heading:
                    h_upper = p_txt.upper()
                    for f_def in CANONICAL_ARM_FIELDS:
                        if any(re.search(pat, h_upper) for pat in f_def["patterns"]):
                            current_chapter = f_def["key"]
                            current_chapter_heading = p_txt
                            break
                    continue

                if current_chapter and len(p_txt) > 50 and current_chapter not in found_arm_keys:
                    candidate_text_fields.append({
                        "id": f"field_{len(candidate_text_fields) + 1}",
                        "template_element": p_txt,
                        "original_text": p_txt,
                        "sample_text": p_txt[:80],
                        "arm_field": current_chapter,
                        "section_heading": current_chapter_heading or current_chapter.title(),
                        "action": "replace",
                        "is_replaceable": True,
                        "content_type": "paragraph",
                        "location": f"Paragraph {p_idx + 1}",
                    })
                    found_arm_keys.add(current_chapter)

        # Check tables for placeholders or key labels
        for t_idx, tbl in enumerate(doc.tables):
            for r_idx, row in enumerate(tbl.rows):
                for c_idx, cell in enumerate(row.cells):
                    matches = bracket_pattern.findall(cell.text)
                    for raw_key in matches:
                        clean_key = raw_key.strip().lower().replace(" ", "_")
                        if clean_key in seen_placeholders:
                            continue
                        seen_placeholders.add(clean_key)
                        matched_arm_key = clean_key
                        for f_def in CANONICAL_ARM_FIELDS:
                            if f_def["key"] == clean_key or any(re.search(pat, clean_key) for pat in f_def["patterns"]):
                                matched_arm_key = f_def["key"]
                                break
                        candidate_text_fields.append({
                            "id": f"field_{len(candidate_text_fields) + 1}",
                            "template_element": f"{{{{{raw_key}}}}}",
                            "sample_text": cell.text[:80],
                            "arm_field": matched_arm_key,
                            "action": "replace",
                            "is_explicit_placeholder": True,
                            "location": f"Table {t_idx + 1}, Cell ({r_idx}, {c_idx})",
                        })
                        found_arm_keys.add(matched_arm_key)

        # Ensure primary fields have at least candidate entries if none matched and document contains text
        has_any_text = any(bool(p.text.strip()) for p in doc.paragraphs) or any(
            bool(c.text.strip()) for tbl in doc.tables for r in tbl.rows for c in r.cells
        )
        if not candidate_text_fields and has_any_text:
            candidate_text_fields = [
                {
                    "id": "field_1",
                    "template_element": "Project Title",
                    "sample_text": "Sample Project Title / Header",
                    "arm_field": "project_title",
                    "action": "replace",
                    "is_explicit_placeholder": False,
                    "location": "Title Page Header",
                },
                {
                    "id": "field_2",
                    "template_element": "Student Name",
                    "sample_text": "Candidate / Student Name",
                    "arm_field": "student_name",
                    "action": "replace",
                    "is_explicit_placeholder": False,
                    "location": "Candidate Details",
                },
                {
                    "id": "field_3",
                    "template_element": "Roll Number",
                    "sample_text": "Hall Ticket / Reg No",
                    "arm_field": "roll_number",
                    "action": "replace",
                    "is_explicit_placeholder": False,
                    "location": "Candidate Details",
                },
                {
                    "id": "field_4",
                    "template_element": "Introduction",
                    "sample_text": "Chapter 1: Introduction",
                    "arm_field": "introduction",
                    "action": "replace",
                    "is_explicit_placeholder": False,
                    "location": "Chapter 1",
                },
            ]

        # 3. Detect Images in Document (Intelligent Classification: Logos vs Replaceable Topic Visuals)
        candidate_images: List[Dict[str, Any]] = []
        try:
            from apps.api.services.intelligent_image_service import intelligent_image_service
            intel_imgs = intelligent_image_service.analyze_docx_images(file_path)
            if intel_imgs:
                for img in intel_imgs:
                    if "is_logo" not in img:
                        img["is_logo"] = (img.get("classification") == "college_logo")
                candidate_images = intel_imgs
        except Exception as e:
            logger.warning(f"Intelligent image analysis fallback: {e}")

        # Fallback to basic rels scan if intelligent scan was empty
        if not candidate_images:
            image_idx = 0
            doc_part = doc.part
            for rel_id, rel in doc_part.rels.items():
                if "image" in rel.target_ref.lower():
                    image_idx += 1
                    is_cover_or_header = image_idx == 1
                    candidate_images.append({
                        "id": f"img_{image_idx}",
                        "rel_id": rel_id,
                        "label": f"College Logo / Header Image" if is_cover_or_header else f"Document Figure {image_idx - 1}",
                        "arm_image_field": f"image_{image_idx}",
                        "action": "fixed" if is_cover_or_header else "replace",
                        "is_logo": is_cover_or_header,
                        "description": "Cover page institutional emblem (Preserved)" if is_cover_or_header else "Report figure / architecture diagram",
                    })

        # Also check if explicit {{IMAGE_1}} tags exist in text
        for p_idx, p in enumerate(doc.paragraphs):
            for slot in ["image_1", "image_2", "image_3"]:
                if f"{{{{{slot}}}}}" in p.text.lower():
                    # check if already in candidate_images
                    if not any(img["arm_image_field"] == slot for img in candidate_images):
                        candidate_images.append({
                            "id": f"slot_{slot}",
                            "rel_id": None,
                            "label": f"Placeholder {slot.upper()}",
                            "arm_image_field": slot,
                            "action": "replace",
                            "is_logo": False,
                            "description": f"Explicit placeholder tag {{{{slot.upper()}}}} in Paragraph {p_idx + 1}",
                        })

        if not candidate_images:
            candidate_images = [
                {
                    "id": "img_1",
                    "rel_id": None,
                    "label": "Primary Report Illustration (image_1)",
                    "arm_image_field": "image_1",
                    "action": "replace",
                    "is_logo": False,
                    "description": "Designated report figure slot",
                }
            ]

        # 4. Summary of Inviolable Fixed Elements
        fixed_elements_summary = {
            "college_logo": "Protected — Fixed cover page emblem",
            "page_borders": "Protected — Exact page borders preserved",
            "headers_footers": "Protected — Header/footer strings & numbering preserved",
            "page_dimensions": f"{page_settings['width_in']}\" x {page_settings['height_in']}\" ({page_settings['orientation']})",
            "margins": f"Top: {page_settings['top_margin_in']}\", Bottom: {page_settings['bottom_margin_in']}\", Left: {page_settings['left_margin_in']}\", Right: {page_settings['right_margin_in']}\"",
            "watermarks_and_shapes": "Protected — Background watermarks & shapes unmodified",
        }

        return {
            "page_settings": page_settings,
            "detected_text_fields": candidate_text_fields,
            "detected_images": candidate_images,
            "fixed_elements_summary": fixed_elements_summary,
            "total_paragraphs": len(doc.paragraphs),
            "total_tables": len(doc.tables),
            "total_sections": len(doc.sections),
        }

    @classmethod
    def register_custom_template(
        cls,
        file_bytes: bytes,
        filename: str,
        template_name: str,
        owner_id: str,
        institution: Optional[str] = None,
        department: Optional[str] = None,
        report_type: Optional[str] = "Seminar",
    ) -> Dict[str, Any]:
        """
        Stores original template DOCX file untouched.
        Performs structural analysis on the DOCX and creates template record.
        """
        ext = cls.validate_template_file(file_bytes, filename)

        template_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # 1. Save untouched original file in local/cloud storage
        storage_provider = get_storage_provider()
        storage_rel_path = f"users/{owner_id}/templates/{template_id}/{filename}"
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        storage_provider.upload_file(
            bucket=settings.storage.bucket_templates,
            path=storage_rel_path,
            data=file_bytes,
            content_type=content_type,
        )

        local_storage_path = os.path.abspath(
            os.path.join(".storage", settings.storage.bucket_templates, storage_rel_path)
        )
        os.makedirs(os.path.dirname(local_storage_path), exist_ok=True)
        with open(local_storage_path, "wb") as f:
            f.write(file_bytes)

        upload_sha256 = hashlib.sha256(file_bytes).hexdigest()
        upload_size = len(file_bytes)
        with open(local_storage_path, "rb") as f:
            stored_bytes = f.read()
        stored_sha256 = hashlib.sha256(stored_bytes).hexdigest()
        stored_size = len(stored_bytes)

        log_upload = (
            f"\n[RAW-TEMPLATE-STORED]\n"
            f"template_id={template_id}\n"
            f"filename={filename}\n"
            f"format={ext}\n"
            f"upload_size={upload_size}\n"
            f"upload_sha256={upload_sha256}\n"
            f"stored_path={local_storage_path}\n"
            f"stored_size={stored_size}\n"
            f"stored_sha256={stored_sha256}\n"
            f"identical={upload_sha256 == stored_sha256}\n"
        )
        print(log_upload)
        logger.info(log_upload)

        # 2. Analyze template DOCX
        analysis = cls.analyze_template_docx(local_storage_path)

        # 3. Create Record
        record: Dict[str, Any] = {
            "id": template_id,
            "owner_id": owner_id,
            "user_id": owner_id,
            "name": template_name.strip() or filename,
            "institution": institution.strip() if institution else "College / Institution",
            "department": department.strip() if department else None,
            "report_type": report_type or "Seminar",
            "file_type": "docx",
            "source_file_type": "docx",
            "source_format": "docx",
            "converted_from_pdf": False,
            "file_size": len(file_bytes),
            "original_file_path": local_storage_path,
            "original_pdf_path": None,
            "storage_path": storage_rel_path,
            "converted_docx_path": local_storage_path,
            "working_docx_path": local_storage_path,
            "working_storage_path": storage_rel_path,
            "file_path": local_storage_path,
            "path": local_storage_path,
            "status": "ready",
            "analysis_status": "analyzed",
            "is_locked": True,
            "is_institution_preset": False,
            "is_master": False,
            "active": True,
            "page_settings": analysis["page_settings"],
            "field_mapping": analysis["detected_text_fields"],
            "image_mapping": analysis["detected_images"],
            "fixed_elements_summary": analysis["fixed_elements_summary"],
            "created_at": now,
            "updated_at": now,
        }

        # 5. Save to in-memory store and write metadata.json to disk
        _CUSTOM_TEMPLATES_STORE[template_id] = record
        try:
            import json
            meta_path = os.path.join(os.path.dirname(local_storage_path), "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(record, mf, indent=2)
        except Exception as me:
            logger.warning(f"Could not write metadata.json: {me}")

        # 6. Persist to Supabase if configured
        client = db_manager.client
        if client:
            try:
                db_record = {
                    "id": template_id,
                    "name": record["name"],
                    "user_id": owner_id if len(owner_id) == 36 else None,
                    "owner_id": owner_id if len(owner_id) == 36 else None,
                    "original_file_path": local_storage_path,
                    "storage_path": storage_rel_path,
                    "file_type": "docx",
                    "file_size": len(file_bytes),
                    "status": "analyzed",
                    "is_locked": True,
                    "created_at": now,
                    "updated_at": now,
                }
                client.table("templates").insert(db_record).execute()
            except Exception as e:
                logger.warning(f"Failed to insert custom template into Supabase (in-memory cached): {e}")

        logger.info(f"Registered custom college template '{record['name']}' ({template_id})")
        return record

    @classmethod
    def get_template(cls, template_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves template by ID, enforcing user authorization with automatic disk fallback."""
        template = _CUSTOM_TEMPLATES_STORE.get(template_id)
        if not template:
            from apps.api.routers.templates import _TEMPLATES_DB
            template = _TEMPLATES_DB.get(template_id)

        if not template:
            client = db_manager.client
            if client:
                try:
                    res = client.table("templates").select("*").eq("id", template_id).execute()
                    if res.data and len(res.data) > 0:
                        template = res.data[0]
                except Exception as e:
                    logger.error(f"Error querying template {template_id}: {e}")

        # Disk fallback: Locate template directory in .storage
        if not template:
            base_storage = os.path.abspath(".storage")
            if os.path.exists(base_storage):
                import json
                for root, dirs, files in os.walk(base_storage):
                    if template_id in root or template_id in dirs:
                        t_dir = root if template_id in root else os.path.join(root, template_id)
                        meta_file = os.path.join(t_dir, "metadata.json")
                        if os.path.exists(meta_file):
                            try:
                                with open(meta_file, "r", encoding="utf-8") as mf:
                                    template = json.load(mf)
                            except Exception:
                                pass
                        if not template and os.path.exists(t_dir):
                            files_in_dir = os.listdir(t_dir)
                            pdf_files = [f for f in files_in_dir if f.lower().endswith(".pdf")]
                            docx_files = [f for f in files_in_dir if f.lower().endswith(".docx")]

                            parts = t_dir.replace("\\", "/").split("/")
                            owner_id = "usr_demo_student"
                            if "users" in parts:
                                u_idx = parts.index("users")
                                if u_idx + 1 < len(parts):
                                    owner_id = parts[u_idx + 1]

                            if pdf_files:
                                orig_f = pdf_files[0]
                                orig_path = os.path.abspath(os.path.join(t_dir, orig_f))
                                if docx_files:
                                    working_path = os.path.abspath(os.path.join(t_dir, docx_files[0]))
                                else:
                                    stem = os.path.splitext(orig_f)[0]
                                    working_path = os.path.abspath(os.path.join(t_dir, f"{stem}_working.docx"))
                                    try:
                                        from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                                        pdf_to_docx_service.convert_pdf_file_to_docx(orig_path, working_path)
                                    except Exception as ex:
                                        logger.warning(f"Could not convert PDF template during disk recovery: {ex}")

                                template = {
                                    "id": template_id,
                                    "owner_id": owner_id,
                                    "user_id": owner_id,
                                    "name": orig_f.replace(".pdf", ""),
                                    "original_file_path": orig_path,
                                    "original_pdf_path": orig_path,
                                    "storage_path": working_path,
                                    "converted_docx_path": working_path,
                                    "working_docx_path": working_path,
                                    "file_path": working_path,
                                    "path": working_path,
                                    "converted_from_pdf": True,
                                    "file_type": "docx",
                                    "source_file_type": "pdf",
                                    "source_format": "pdf",
                                    "file_size": os.path.getsize(orig_path),
                                    "status": "analyzed",
                                    "is_locked": True,
                                    "created_at": datetime.now(timezone.utc).isoformat(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                }
                            elif docx_files:
                                orig_f = docx_files[0]
                                orig_path = os.path.abspath(os.path.join(t_dir, orig_f))
                                template = {
                                    "id": template_id,
                                    "owner_id": owner_id,
                                    "user_id": owner_id,
                                    "name": orig_f.replace(".docx", ""),
                                    "original_file_path": orig_path,
                                    "storage_path": orig_path,
                                    "converted_docx_path": orig_path,
                                    "working_docx_path": orig_path,
                                    "file_path": orig_path,
                                    "path": orig_path,
                                    "converted_from_pdf": False,
                                    "file_type": "docx",
                                    "source_file_type": "docx",
                                    "file_size": os.path.getsize(orig_path),
                                    "status": "analyzed",
                                    "is_locked": True,
                                    "created_at": datetime.now(timezone.utc).isoformat(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                }
                        if template:
                            _CUSTOM_TEMPLATES_STORE[template_id] = template
                            break

        if not template:
            return None

        # Verify and guarantee that converted PDF templates point to DOCX, not PDF
        if template.get("converted_from_pdf") or template.get("source_format") == "pdf" or str(template.get("file_type", "")).lower() == "pdf":
            cand_docx = (
                template.get("converted_docx_path")
                or template.get("working_docx_path")
                or template.get("storage_path")
            )
            if not cand_docx or cand_docx.lower().endswith(".pdf") or not os.path.exists(cand_docx):
                # Search for docx in the same folder as original_file_path
                orig_pdf = template.get("original_pdf_path") or template.get("original_file_path")
                if orig_pdf and os.path.exists(orig_pdf):
                    stem = os.path.splitext(orig_pdf)[0]
                    target_docx = f"{stem}_working.docx"
                    if os.path.exists(target_docx):
                        template["converted_docx_path"] = target_docx
                        template["working_docx_path"] = target_docx
                        template["storage_path"] = target_docx
                        template["file_path"] = target_docx
                        template["path"] = target_docx
                    else:
                        try:
                            from apps.api.services.pdf_to_docx_service import pdf_to_docx_service
                            target_docx, _, _ = pdf_to_docx_service.convert_pdf_file_to_docx(orig_pdf, target_docx)
                            template["converted_docx_path"] = target_docx
                            template["working_docx_path"] = target_docx
                            template["storage_path"] = target_docx
                            template["file_path"] = target_docx
                            template["path"] = target_docx
                        except Exception as ex:
                            logger.error(f"Failed to auto-convert PDF template {orig_pdf} to DOCX: {ex}")

        # Verify ownership if user_id is provided and template is not a public preset
        if user_id and not template.get("is_institution_preset"):
            owner = template.get("owner_id") or template.get("user_id")
            if owner and str(owner) != str(user_id) and owner != "usr_demo_student":
                raise PermissionError("You do not have permission to access this college template.")

        return template

    @classmethod
    def update_mappings(
        cls,
        template_id: str,
        field_mapping: List[Dict[str, Any]],
        image_mapping: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Saves verified user mapping for the custom template."""
        template = cls.get_template(template_id, user_id)
        if not template:
            raise ValueError(f"Template {template_id} not found.")

        template["field_mapping"] = field_mapping
        template["image_mapping"] = image_mapping
        template["status"] = "ready"
        template["analysis_status"] = "completed"
        template["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Persist updated mappings to metadata.json on disk
        meta_dir = None
        orig_p = template.get("original_file_path") or template.get("storage_path")
        if orig_p and os.path.exists(orig_p):
            meta_dir = os.path.dirname(os.path.abspath(orig_p))
        elif orig_p and os.path.exists(os.path.dirname(os.path.abspath(orig_p))):
            meta_dir = os.path.dirname(os.path.abspath(orig_p))
        else:
            base_storage = os.path.abspath(".storage")
            if os.path.exists(base_storage):
                for root, dirs, _ in os.walk(base_storage):
                    if template_id in root or template_id in dirs:
                        meta_dir = root if template_id in root else os.path.join(root, template_id)
                        break

        if meta_dir and os.path.exists(meta_dir):
            try:
                import json
                meta_path = os.path.join(meta_dir, "metadata.json")
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(template, mf, indent=2)
                logger.info(f"[CUSTOM-TEMPLATE] Persisted updated metadata to {meta_path}")
            except Exception as me:
                logger.warning(f"[CUSTOM-TEMPLATE] Could not write metadata.json: {me}")

        _CUSTOM_TEMPLATES_STORE[template_id] = template
        from apps.api.routers.templates import _TEMPLATES_DB
        _TEMPLATES_DB[template_id] = template

        return template

    @classmethod
    def _scan_and_load_disk_templates(cls):
        """Scans .storage for stored templates and loads them into memory."""
        base_storage = os.path.abspath(".storage")
        if not os.path.exists(base_storage):
            return
        import json
        for root, dirs, files in os.walk(base_storage):
            folder_name = os.path.basename(root)
            if (folder_name.startswith("tpl_") or len(folder_name) == 36) and folder_name not in _CUSTOM_TEMPLATES_STORE:
                meta_file = os.path.join(root, "metadata.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            rec = json.load(mf)
                            tid = rec.get("id") or folder_name
                            _CUSTOM_TEMPLATES_STORE[tid] = rec
                            continue
                    except Exception:
                        pass
                for f in files:
                    if f.endswith((".docx", ".pdf")):
                        f_path = os.path.abspath(os.path.join(root, f))
                        parts = root.replace("\\", "/").split("/")
                        owner_id = "usr_demo_student"
                        if "users" in parts:
                            u_idx = parts.index("users")
                            if u_idx + 1 < len(parts):
                                owner_id = parts[u_idx + 1]
                        rec = {
                            "id": folder_name,
                            "owner_id": owner_id,
                            "user_id": owner_id,
                            "name": f.replace(".docx", "").replace(".pdf", ""),
                            "original_file_path": f_path,
                            "storage_path": f_path,
                            "file_type": "docx" if f.endswith(".docx") else "pdf",
                            "file_size": os.path.getsize(f_path),
                            "status": "analyzed",
                            "is_locked": True,
                        }
                        _CUSTOM_TEMPLATES_STORE[folder_name] = rec
                        break

    @classmethod
    def list_templates_for_user(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists presets plus custom templates belonging to user."""
        cls._scan_and_load_disk_templates()
        results = []
        user_key = str(user_id) if user_id else "usr_demo_student"

        for t in _CUSTOM_TEMPLATES_STORE.values():
            owner = str(t.get("owner_id") or t.get("user_id") or "")
            if t.get("is_institution_preset") or owner == user_key or owner == "usr_demo_student" or not user_id:
                results.append(t)

        return results


custom_template_service = CustomTemplateService()
# Initial scan on module load
custom_template_service._scan_and_load_disk_templates()
