"""
ARM Stage 10 - In-Place DOCX Template Replacement Engine
Clones the authoritative College Master Template and substitutes structured
matter and images directly in-place, strictly preserving original fonts, colors,
headings, spacing, margins, logos, headers, footers, page structure, and visual style.
"""

import os
import re
import uuid
import copy
import shutil
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Set
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from apps.api.core.logging import get_logger
from apps.api.services.master_template_service import CANONICAL_FIELDS, MASTER_TEMPLATE_ID
from packages.replacement_engine.base import (
    BaseReplacementEngine,
    ReplacementState,
    FieldReplacementAudit,
    ReplacementErrorDetail,
    ReplacementResult,
    FIXED_ELEMENTS,
    REPLACEABLE_ELEMENTS,
)

logger = get_logger("replacement_engine.docx")


class DocxTemplateReplacementEngine(BaseReplacementEngine):
    """
    Precision in-place DOCX template replacement engine.
    Ensures that the college template is the absolute source of truth.
    Never redesigns the document or converts it to plain text.
    """

    def __init__(self, canonical_fields: Optional[List[Dict[str, Any]]] = None):
        self.canonical_fields = canonical_fields or CANONICAL_FIELDS
        self._field_map = {f["field_name"]: f for f in self.canonical_fields}

    def replace(
        self,
        template_path: str,
        field_values: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        job_id: Optional[str] = None,
        field_mapping: Optional[List[Dict[str, Any]]] = None,
        image_mapping: Optional[List[Dict[str, Any]]] = None,
    ) -> ReplacementResult:
        """
        Executes in-place replacement on the provided template DOCX.
        Strictly preserves original template formatting, layout, borders, logos, and geometry.
        """
        job_id = job_id or str(uuid.uuid4())
        image_assets = image_assets or {}
        audit_list: List[FieldReplacementAudit] = []
        warnings: List[str] = []
        errors: List[ReplacementErrorDetail] = []
        fields_replaced_count = 0
        images_replaced_count = 0

        if not os.path.exists(template_path):
            err_msg = f"Master college template file not found at: '{template_path}'"
            logger.error(err_msg)
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="template_file", reason=err_msg)],
            )

        # Generate target output path if not provided
        if not output_path:
            output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"arm_report_{job_id[:8]}.docx")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Primary Engine: Delegate directly to PackageLevelDocxEngine to operate at OOXML package level
        # Strictly prevents python-docx from re-serializing unmodeled XML structures (w:pgBorders, VML lines, etc.)
        from packages.replacement_engine.package_engine import PackageLevelDocxEngine
        return PackageLevelDocxEngine.replace(
            template_path=template_path,
            field_values=field_values,
            image_assets=image_assets,
            output_path=output_path,
            job_id=job_id,
            field_mapping=field_mapping,
            image_mapping=image_mapping,
        )

        try:
            # 1. Load the template DOCX directly (The College Template is the Source of Truth)
            doc = docx.Document(template_path)
        except Exception as e:
            err_msg = f"Failed to parse template DOCX: {str(e)}"
            logger.error(err_msg)
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="template_parse", reason=err_msg)],
            )

        # Record exact original section dimensions to guarantee zero unwanted resizing
        original_geometries = []
        for sec in doc.sections:
            original_geometries.append({
                "page_width": sec.page_width,
                "page_height": sec.page_height,
                "orientation": sec.orientation,
                "top_margin": sec.top_margin,
                "bottom_margin": sec.bottom_margin,
                "left_margin": sec.left_margin,
                "right_margin": sec.right_margin,
            })

        # Combine text fields into a normalized key mapping (excluding image slots which are embedded as real pictures)
        image_field_names = {f["field_name"] for f in self.canonical_fields if f.get("field_type") == "image"}
        image_field_names.update(["image_1", "image_2", "image_3"])

        # Determine allowed replaceable fields if custom field_mapping is provided
        allowed_replace_fields: Optional[Set[str]] = None
        custom_phrase_replacements: Dict[str, str] = {}
        if field_mapping is not None:
            allowed_replace_fields = set()
            for fm in field_mapping:
                action = fm.get("action", "replace").lower()
                arm_f = fm.get("arm_field")
                tpl_elem = fm.get("template_element", "")
                if action == "replace" and arm_f:
                    allowed_replace_fields.add(arm_f)
                    if tpl_elem and not (tpl_elem.startswith("{{") and tpl_elem.endswith("}}")):
                        custom_phrase_replacements[tpl_elem] = arm_f

        # Ensure FIXED elements are strictly protected from modification
        # Only explicitly configured REPLACEABLE elements may be substituted
        all_replacements: Dict[str, Any] = {}
        for k, v in field_values.items():
            if k in FIXED_ELEMENTS:
                logger.debug(f"Fixed element '{k}' strictly protected from modification.")
                continue
            if allowed_replace_fields is not None and k not in allowed_replace_fields:
                logger.debug(f"Field '{k}' not marked as replaceable in template mapping.")
                continue
            if v is not None and k not in image_field_names:
                # Apply configurable content length limits to prevent layout expansion
                field_spec = self._field_map.get(k)
                if field_spec and "content_limits" in field_spec:
                    limits = field_spec["content_limits"]
                    max_words = limits.get("max_words")
                    max_length = limits.get("max_length")
                    max_items = limits.get("max_items")
                    if isinstance(v, str):
                        words = v.split()
                        if max_words and len(words) > max_words:
                            v = " ".join(words[:max_words])
                        if max_length and len(v) > max_length:
                            v = v[:max_length]
                    elif isinstance(v, list) and max_items and len(v) > max_items:
                        v = v[:max_items]

                all_replacements[k] = v

        # 2. Track which fields were successfully replaced
        replaced_fields: Set[str] = set()

        # Capture initial template text before any replacements occur
        initial_blobs = [p.text for p in doc.paragraphs]
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    initial_blobs.append(cell.text)
        for sec in doc.sections:
            for hp in [getattr(sec, "header", None), getattr(sec, "first_page_header", None), getattr(sec, "footer", None)]:
                if hp:
                    for p in hp.paragraphs:
                        initial_blobs.append(p.text)
        self._initial_template_text = " ".join(initial_blobs).lower()

        # Step 2a: Run-level placeholder replacement across body paragraphs (with multi-paragraph & list expansion)
        for p in list(doc.paragraphs):
            self._replace_placeholders_in_paragraph(p, all_replacements, replaced_fields, doc=doc)

        # Step 2b: Basic tables support: cell placeholder substitution & dynamic row expansion
        for table in list(doc.tables):
            self._process_table(table, all_replacements, replaced_fields)

        # Step 2c: Run-level placeholder replacement across all header and footer variations
        # Covers primary header, first-page header, even-page header, and respective footers & tables
        for section in doc.sections:
            header_footer_parts = [
                getattr(section, "header", None),
                getattr(section, "first_page_header", None),
                getattr(section, "even_page_header", None),
                getattr(section, "footer", None),
                getattr(section, "first_page_footer", None),
                getattr(section, "even_page_footer", None),
            ]
            for part in header_footer_parts:
                if part is None:
                    continue
                try:
                    for p in list(part.paragraphs):
                        self._replace_placeholders_in_paragraph(p, all_replacements, replaced_fields)
                    for table in list(part.tables):
                        self._process_table(table, all_replacements, replaced_fields)
                except Exception as ex:
                    logger.debug(f"Header/Footer part processing skipped: {ex}")

        # Step 2c-2: Custom phrase substitutions for mapped text elements without {{...}} brackets
        if custom_phrase_replacements:
            for tpl_phrase, arm_k in custom_phrase_replacements.items():
                rep_val = all_replacements.get(arm_k)
                if rep_val is not None and arm_k not in replaced_fields:
                    target_txt = str(rep_val)
                    for p in list(doc.paragraphs):
                        if tpl_phrase.lower() in p.text.lower():
                            for run in p.runs:
                                if tpl_phrase.lower() in run.text.lower():
                                    idx = run.text.lower().find(tpl_phrase.lower())
                                    run.text = run.text[:idx] + target_txt + run.text[idx + len(tpl_phrase):]
                                    replaced_fields.add(arm_k)
                                    fields_replaced_count += 1
                                    break
                            if arm_k in replaced_fields:
                                break

        # Step 2d: Image placeholders & mapped images replacement
        if image_mapping is not None:
            # Custom image mapping mode: only replace images where action == "replace"
            for im in image_mapping:
                action = im.get("action", "fixed").lower()
                arm_img_f = im.get("arm_image_field", "image_1")
                rel_id = im.get("rel_id")
                if action == "replace":
                    img_src = image_assets.get(arm_img_f) or field_values.get(arm_img_f)
                    if isinstance(img_src, dict):
                        img_src = img_src.get("storage_path") or img_src.get("file_path") or img_src.get("url")

                    if img_src and os.path.exists(str(img_src)):
                        # Case A: If it's an existing image in the document with rel_id
                        if rel_id and rel_id in doc.part.rels:
                            rel = doc.part.rels[rel_id]
                            if hasattr(rel, "target_part") and hasattr(rel.target_part, "_blob"):
                                try:
                                    with open(str(img_src), "rb") as f_img:
                                        rel.target_part._blob = f_img.read()
                                    images_replaced_count += 1
                                    replaced_fields.add(arm_img_f)
                                except Exception as img_ex:
                                    warnings.append(f"Failed to update embedded image blob for {rel_id}: {img_ex}")
                        else:
                            # Case B: Replace placeholder tag {{IMAGE_1}}
                            inserted = self._replace_image_slot(doc, arm_img_f, str(img_src))
                            if inserted:
                                images_replaced_count += 1
                                replaced_fields.add(arm_img_f)
                    else:
                        warnings.append(f"Image asset for '{arm_img_f}' not found on disk: '{img_src}'")
        else:
            # Default template mode: use img_slots
            img_slots = {
                "image_1": image_assets.get("image_1") or field_values.get("image_1"),
                "image_2": image_assets.get("image_2") or field_values.get("image_2"),
                "image_3": image_assets.get("image_3") or field_values.get("image_3"),
            }

            for img_field, img_val in img_slots.items():
                if img_val:
                    img_path = img_val
                    img_caption = None
                    if isinstance(img_val, dict):
                        img_path = img_val.get("storage_path") or img_val.get("file_path") or img_val.get("url")
                        img_caption = img_val.get("caption") or img_val.get("title")

                    if img_path and os.path.exists(str(img_path)):
                        inserted = self._replace_image_slot(doc, img_field, str(img_path), img_caption)
                        if inserted:
                            replaced_fields.add(img_field)
                            images_replaced_count += 1
                    else:
                        field_def = self._field_map.get(img_field)
                        if field_def and field_def.get("is_required"):
                            errors.append(
                                ReplacementErrorDetail(
                                    field=img_field,
                                    reason=f"Image asset file does not exist on disk: '{img_path}'"
                                )
                            )
                        else:
                            warnings.append(f"Image asset for '{img_field}' not found on disk: '{img_path}'")

        # Step 2e: Section matter substitution for college templates lacking explicit {{...}} brackets
        # (e.g. templates containing pre-filled sections like ABSTRACT, INTRODUCTION, OBJECTIVES)
        if field_mapping is None and len(all_replacements) > 1 and not replaced_fields:
            self._replace_section_matter_fallback(doc, all_replacements, replaced_fields)

        # Step 2f: Clean up unprovided optional placeholders (e.g. {{IMAGE_2}}, {{IMAGE_3}}, {{ADVANTAGES}} etc.)
        for fld in self.canonical_fields:
            if not fld.get("is_required", False) and fld["field_name"] not in replaced_fields:
                p_tag = fld.get("placeholder_identifier", f"{{{{{fld['field_name'].upper()}}}}}")
                for p in list(doc.paragraphs):
                    if p_tag in p.text:
                        self._apply_run_substitution(p, p_tag, "")
                for tbl in list(doc.tables):
                    for row in tbl.rows:
                        for cell in row.cells:
                            for p in list(cell.paragraphs):
                                if p_tag in p.text:
                                    self._apply_run_substitution(p, p_tag, "")

        # 3. Compile Audit and Validation
        for fld in self.canonical_fields:
            name = fld["field_name"]
            is_req = fld.get("is_required", False)
            placeholder = fld.get("placeholder_identifier", f"{{{{{name.upper()}}}}}")
            field_type = fld.get("field_type", "text")

            is_replaced = name in replaced_fields
            val = all_replacements.get(name)
            placeholder_in_template = (
                placeholder.lower() in self._initial_template_text
                or f"{{{name.lower()}}}" in self._initial_template_text
                or f"{{{{{name.lower()}}}}}" in self._initial_template_text
            )

            if is_replaced:
                fields_replaced_count += 1
                snippet = str(val)[:120] if val else None
                audit_list.append(
                    FieldReplacementAudit(
                        field_name=name,
                        placeholder=placeholder,
                        field_type=field_type,
                        replaced=True,
                        new_snippet=snippet,
                        formatting_preserved=True,
                    )
                )
            else:
                if is_req and placeholder_in_template:
                    if val is not None:
                        reason = f"Required field '{name}' ({placeholder}) was not found in the Master Template structure."
                        errors.append(ReplacementErrorDetail(field=name, reason=reason))
                        audit_list.append(
                            FieldReplacementAudit(
                                field_name=name,
                                placeholder=placeholder,
                                field_type=field_type,
                                replaced=False,
                                formatting_preserved=False,
                                error=reason,
                            )
                        )
                    else:
                        reason = f"Required field '{name}' was not provided in student generated content."
                        errors.append(ReplacementErrorDetail(field=name, reason=reason))
                        audit_list.append(
                            FieldReplacementAudit(
                                field_name=name,
                                placeholder=placeholder,
                                field_type=field_type,
                                replaced=False,
                                formatting_preserved=False,
                                error=reason,
                            )
                        )
                else:
                    audit_list.append(
                        FieldReplacementAudit(
                            field_name=name,
                            placeholder=placeholder,
                            field_type=field_type,
                            replaced=False,
                            formatting_preserved=True,
                            error=None,
                        )
                    )
        is_success = len(errors) == 0

        # 4. Save the finalized document (Enforce absolute geometry preservation)
        try:
            for s_idx, sec in enumerate(doc.sections):
                if s_idx < len(original_geometries):
                    orig = original_geometries[s_idx]
                    if sec.page_width != orig["page_width"]:
                        sec.page_width = orig["page_width"]
                    if sec.page_height != orig["page_height"]:
                        sec.page_height = orig["page_height"]
                    if sec.top_margin != orig["top_margin"]:
                        sec.top_margin = orig["top_margin"]
                    if sec.bottom_margin != orig["bottom_margin"]:
                        sec.bottom_margin = orig["bottom_margin"]
                    if sec.left_margin != orig["left_margin"]:
                        sec.left_margin = orig["left_margin"]
                    if sec.right_margin != orig["right_margin"]:
                        sec.right_margin = orig["right_margin"]

            doc.save(output_path)
            logger.info(f"Successfully generated replaced document at: {output_path}")

            # 5. Pre-delivery Structural Validation
            from packages.replacement_engine.validator import ReplacementValidator
            pkg_val = ReplacementValidator.validate_package_preservation(
                original_docx_path=template_path,
                generated_docx_path=output_path,
                allowed_replaced_fields=replaced_fields,
                allowed_replaced_media=set(image_assets.keys()),
            )
            if not pkg_val.get("is_valid", True):
                for p_err in pkg_val.get("errors", []):
                    errors.append(ReplacementErrorDetail(field=p_err["field"], reason=p_err["reason"]))
                is_success = len(errors) == 0
        except Exception as e:
            err_msg = f"Failed to save replaced DOCX: {str(e)}"
            logger.error(err_msg)
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="save_error", reason=err_msg)],
            )

        return ReplacementResult(
            success=is_success,
            job_id=job_id,
            state=ReplacementState.COMPLETED if is_success else ReplacementState.FAILED,
            template_path=template_path,
            output_docx_path=output_path,
            fields_replaced=fields_replaced_count,
            total_fields=len(self.canonical_fields),
            images_replaced=images_replaced_count,
            audit=audit_list,
            warnings=warnings,
            errors=errors,
            metadata={
                "template_source": template_path,
                "sections_count": len(doc.sections),
                "paragraphs_count": len(doc.paragraphs),
                "tables_count": len(doc.tables),
            }
        )

    def _replace_placeholders_in_paragraph(
        self,
        paragraph,
        replacements: Dict[str, Any],
        replaced_fields: Set[str],
        doc: Optional[Any] = None,
    ):
        """
        Safely replaces placeholders in a paragraph while preserving:
        - Font name, font size, bold, italic, underline, text color
        - Heading styles & outline levels (e.g. Heading 1, Heading 2)
        - Multi-paragraph expansion with sibling paragraph creation
        - List item expansion with bullet/citation styling
        - Standalone tabular data replacement
        """
        p_text = paragraph.text
        if not p_text or ("{" not in p_text):
            return

        # Build normalized lookup for case-insensitive matching
        lower_replacements = {k.lower(): (k, v) for k, v in replacements.items()}

        # 1. Discover all tokens in the paragraph (e.g. {{PROJECT_TITLE}}, {project_title})
        tokens_found = re.findall(r'\{\{([a-zA-Z0-9_]+)\}\}|\{([a-zA-Z0-9_]+)\}', p_text)
        candidate_field_names: Set[str] = set()
        for g1, g2 in tokens_found:
            cand = (g1 or g2).lower()
            if cand in lower_replacements:
                candidate_field_names.add(lower_replacements[cand][0])

        # Also check all replacement keys directly
        for f_name in replacements.keys():
            if f_name.lower() in p_text.lower():
                candidate_field_names.add(f_name)

        for field_name in candidate_field_names:
            value = replacements.get(field_name)
            if value is None:
                continue

            patterns = [
                f"{{{{{field_name.upper()}}}}}",
                f"{{{{{field_name.lower()}}}}}",
                f"{{{{{field_name}}}}}",
                f"{{{field_name.upper()}}}",
                f"{{{field_name.lower()}}}",
                f"{{{field_name}}}",
            ]

            matched_pattern = None
            for pat in patterns:
                if pat in p_text:
                    matched_pattern = pat
                    break

            if not matched_pattern:
                continue

            # Check if this paragraph is solely the placeholder (standalone block)
            is_standalone = paragraph.text.strip() == matched_pattern

            # Case A: Standalone structured table data (list of dicts)
            if is_standalone and isinstance(value, list) and value and isinstance(value[0], dict) and doc:
                self._insert_structured_table(doc, paragraph, value)
                replaced_fields.add(field_name)
                return

            # Case B: Standalone list expansion into distinct bullet paragraphs
            if is_standalone and isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
                if items:
                    self._expand_list_paragraphs(paragraph, field_name, items)
                    replaced_fields.add(field_name)
                    return
                else:
                    self._apply_run_substitution(paragraph, matched_pattern, "")
                    replaced_fields.add(field_name)
                    p_text = paragraph.text
                    continue

            # Case C: Standalone multi-paragraph expansion
            if is_standalone and isinstance(value, str):
                chunks = [c.strip() for c in re.split(r'\n{2,}|\r\n{2,}', value) if c.strip()]
                if len(chunks) > 1:
                    self._expand_multiparagraph_content(paragraph, chunks)
                    replaced_fields.add(field_name)
                    return

            # Case D: Inline text substitution (within sentence or heading)
            if isinstance(value, list):
                rep_str = "\n".join([f"•  {item}" for item in value])
            else:
                rep_str = str(value)

            # If inside a heading, strip newlines to keep heading compact
            style_name = getattr(paragraph.style, "name", "")
            if "Heading" in style_name or "Title" in style_name:
                rep_str = rep_str.replace("\n", " ").strip()

            self._apply_run_substitution(paragraph, matched_pattern, rep_str)
            p_text = paragraph.text
            replaced_fields.add(field_name)

    def _expand_list_paragraphs(self, paragraph, field_name: str, items: List[str]):
        """
        Expands a list of items into distinct bullet paragraphs, preserving
        paragraph style, indentation, line spacing, and run typography.
        """
        base_font_name = None
        base_font_size = None
        base_bold = None
        base_italic = None
        base_color = None
        if paragraph.runs:
            r0 = paragraph.runs[0]
            base_font_name = r0.font.name
            base_font_size = r0.font.size
            base_bold = r0.bold
            base_italic = r0.italic
            base_color = r0.font.color.rgb if r0.font.color else None

        is_ref = "reference" in field_name.lower()

        # Update initial paragraph with item 0
        p0_prefix = "[1]  " if is_ref else "•   "
        if paragraph.runs:
            paragraph.runs[0].text = f"{p0_prefix}{items[0]}"
            for r in paragraph.runs[1:]:
                r.text = ""
        else:
            r0 = paragraph.add_run(f"{p0_prefix}{items[0]}")
            self._apply_run_font_props(r0, base_font_name, base_font_size, base_bold, base_italic, base_color)

        curr_p = paragraph
        for idx, item in enumerate(items[1:], start=2):
            prefix = f"[{idx}]  " if is_ref else "•   "
            new_elm = OxmlElement('w:p')
            curr_p._p.addnext(new_elm)
            new_p = docx.text.paragraph.Paragraph(new_elm, paragraph._parent)

            # Preserve paragraph format
            try:
                new_p.style = paragraph.style
            except Exception:
                pass
            new_p.alignment = paragraph.alignment
            new_p.paragraph_format.space_before = Pt(2.0)
            new_p.paragraph_format.space_after = Pt(4.0)
            new_p.paragraph_format.line_spacing = paragraph.paragraph_format.line_spacing

            run = new_p.add_run(f"{prefix}{item}")
            self._apply_run_font_props(run, base_font_name, base_font_size, base_bold, base_italic, base_color)
            curr_p = new_p

    def _expand_multiparagraph_content(self, paragraph, chunks: List[str]):
        """
        Expands multi-paragraph text into distinct sibling paragraphs,
        preserving style, margins, spacing, and font typography across all paragraphs.
        """
        base_font_name = None
        base_font_size = None
        base_bold = None
        base_italic = None
        base_color = None
        if paragraph.runs:
            r0 = paragraph.runs[0]
            base_font_name = r0.font.name
            base_font_size = r0.font.size
            base_bold = r0.bold
            base_italic = r0.italic
            base_color = r0.font.color.rgb if r0.font.color else None

        # First chunk replaces paragraph 0
        if paragraph.runs:
            paragraph.runs[0].text = chunks[0]
            for r in paragraph.runs[1:]:
                r.text = ""
        else:
            r0 = paragraph.add_run(chunks[0])
            self._apply_run_font_props(r0, base_font_name, base_font_size, base_bold, base_italic, base_color)

        curr_p = paragraph
        for chunk in chunks[1:]:
            new_elm = OxmlElement('w:p')
            curr_p._p.addnext(new_elm)
            new_p = docx.text.paragraph.Paragraph(new_elm, paragraph._parent)

            try:
                new_p.style = paragraph.style
            except Exception:
                pass
            new_p.alignment = paragraph.alignment
            new_p.paragraph_format.space_before = paragraph.paragraph_format.space_before
            new_p.paragraph_format.space_after = paragraph.paragraph_format.space_after
            new_p.paragraph_format.line_spacing = paragraph.paragraph_format.line_spacing

            run = new_p.add_run(chunk)
            self._apply_run_font_props(run, base_font_name, base_font_size, base_bold, base_italic, base_color)
            curr_p = new_p

    def _apply_run_font_props(self, run, name, size, bold, italic, color):
        """Copies font typography onto a newly created run."""
        if name:
            run.font.name = name
        if size:
            run.font.size = size
        if bold is not None:
            run.bold = bold
        if italic is not None:
            run.italic = italic
        if color:
            run.font.color.rgb = color

    def _process_table(self, table, replacements: Dict[str, Any], replaced_fields: Set[str]):
        """
        Processes a table:
        1. Checks for dynamic row expansion if any row contains placeholders for list-of-dicts data.
        2. Substitutes cell placeholders across all cells while preserving cell formatting.
        """
        # Step 1: Check dynamic row expansion
        for field_name, value in replacements.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                sample_item = value[0]
                item_keys = set(sample_item.keys())

                for row in list(table.rows):
                    row_text = " ".join(c.text for c in row.cells)
                    matched_keys = [
                        k for k in item_keys
                        if f"{{{{{k}}}}}" in row_text.lower()
                        or f"{{{k}}}" in row_text.lower()
                        or f"{{{{{k.upper()}}}}}" in row_text
                        or f"{{{k.upper()}}}" in row_text
                    ]
                    if matched_keys:
                        template_tr_xml = copy.deepcopy(row._tr)
                        curr_tr = row._tr
                        for item_idx, record in enumerate(value):
                            if item_idx == 0:
                                target_row = row
                            else:
                                new_tr = copy.deepcopy(template_tr_xml)
                                curr_tr.addnext(new_tr)
                                curr_tr = new_tr
                                target_row = docx.table._Row(new_tr, table)

                            for cell in target_row.cells:
                                for p in cell.paragraphs:
                                    self._replace_placeholders_in_paragraph(p, record, set())
                        replaced_fields.add(field_name)
                        break

        # Step 2: Regular cell placeholder substitution
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    self._replace_placeholders_in_paragraph(p, replacements, replaced_fields)

    def _insert_structured_table(self, doc, paragraph, data: List[Dict[str, Any]]):
        """
        Inserts a styled academic table corresponding to structured list-of-dicts data,
        positioning it exactly where the placeholder paragraph was.
        """
        if not data or not isinstance(data[0], dict):
            return

        headers = list(data[0].keys())
        tbl = doc.add_table(rows=len(data) + 1, cols=len(headers))
        tbl.autofit = True

        # Header row formatting
        hdr_row = tbl.rows[0]
        for col_idx, h in enumerate(headers):
            cell = hdr_row.cells[col_idx]
            cell.text = str(h).replace('_', ' ').title()
            if cell.paragraphs and cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.name = "Times New Roman"
                cell.paragraphs[0].runs[0].font.size = Pt(10)
            try:
                shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F3F4F6"/>')
                cell._tc.get_or_add_tcPr().append(shading)
            except Exception:
                pass

        # Data rows formatting
        for r_idx, item in enumerate(data):
            row = tbl.rows[r_idx + 1]
            for c_idx, h in enumerate(headers):
                cell = row.cells[c_idx]
                cell.text = str(item.get(h, ''))
                if cell.paragraphs and cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].font.name = "Times New Roman"
                    cell.paragraphs[0].runs[0].font.size = Pt(9.5)

        paragraph._p.addnext(tbl._tbl)
        paragraph._p.getparent().remove(paragraph._p)

    def _apply_run_substitution(self, paragraph, target_token: str, replacement_text: str):
        """
        Performs precise run-level replacement so formatting (font, size, color, bold)
        is completely preserved, even when placeholders span across split runs.
        """
        if target_token not in paragraph.text:
            return

        runs = paragraph.runs
        if not runs:
            paragraph.text = paragraph.text.replace(target_token, replacement_text)
            return

        # Case 1: Simple single run match
        for run in runs:
            if target_token in run.text:
                run.text = run.text.replace(target_token, replacement_text)
                return

        # Case 2: Precise Multi-Run Span Stitching
        full_text = "".join(r.text for r in runs)
        if target_token in full_text:
            start_idx = full_text.index(target_token)
            end_idx = start_idx + len(target_token)

            char_count = 0
            start_run_idx = None
            end_run_idx = None

            for idx, r in enumerate(runs):
                run_len = len(r.text)
                run_start = char_count
                run_end = char_count + run_len
                char_count = run_end

                if start_run_idx is None and run_start <= start_idx < run_end:
                    start_run_idx = idx
                if run_start < end_idx <= run_end:
                    end_run_idx = idx
                    break

            if start_run_idx is not None and end_run_idx is not None:
                if start_run_idx == end_run_idx:
                    runs[start_run_idx].text = runs[start_run_idx].text.replace(target_token, replacement_text)
                else:
                    run_0_start = sum(len(runs[k].text) for k in range(start_run_idx))
                    before = runs[start_run_idx].text[:start_idx - run_0_start]
                    run_end_start = sum(len(runs[k].text) for k in range(end_run_idx))
                    after = runs[end_run_idx].text[end_idx - run_end_start:]

                    runs[start_run_idx].text = before + replacement_text
                    for k in range(start_run_idx + 1, end_run_idx):
                        runs[k].text = ""
                    runs[end_run_idx].text = after
                return

        # Fallback: Assign new text while preserving primary run's style
        new_text = full_text.replace(target_token, replacement_text)
        first_run = runs[0]
        font_name = first_run.font.name
        font_size = first_run.font.size
        bold = first_run.bold
        italic = first_run.italic
        color = first_run.font.color.rgb if first_run.font.color else None

        for r in runs[1:]:
            r.text = ""
        first_run.text = new_text
        self._apply_run_font_props(first_run, font_name, font_size, bold, italic, color)

    def _replace_image_slot(
        self,
        doc,
        slot_name: str,
        image_path: str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Replaces an image placeholder with an embedded picture and formatted caption.
        Preserves page margins and centering.
        """
        patterns = [
            f"{{{{{slot_name.upper()}}}}}",
            f"{{{{{slot_name.lower()}}}}}",
            f"{{{{{slot_name}}}}}",
            f"{{{slot_name.upper()}}}",
            f"{{{slot_name.lower()}}}",
            f"{{{slot_name}}}",
        ]

        # Calculate safe picture width respecting printable page margins
        max_width = Inches(5.5)
        if doc.sections:
            sec = doc.sections[0]
            try:
                avail = sec.page_width - sec.left_margin - sec.right_margin
                if avail > Inches(2.0):
                    max_width = min(avail, Inches(5.8))
            except Exception:
                pass

        for p in list(doc.paragraphs):
            full_txt = p.text
            for pat in patterns:
                if pat in full_txt:
                    p.text = ""
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(8.0)
                    p.paragraph_format.space_after = Pt(4.0)

                    run = p.add_run()
                    self._safe_add_picture(run, image_path, width=max_width)

                    if caption:
                        # Insert caption paragraph immediately following image
                        cap_elm = OxmlElement('w:p')
                        p._p.addnext(cap_elm)
                        cap_p = docx.text.paragraph.Paragraph(cap_elm, p._parent)
                        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        cap_p.paragraph_format.space_before = Pt(2.0)
                        cap_p.paragraph_format.space_after = Pt(8.0)
                        cap_run = cap_p.add_run(caption)
                        cap_run.font.name = "Times New Roman"
                        cap_run.font.size = Pt(9.5)
                        cap_run.italic = True
                        cap_run.font.color.rgb = RGBColor(90, 90, 90)

                    return True

        # Fallback search inside tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        full_txt = p.text
                        for pat in patterns:
                            if pat in full_txt:
                                p.text = ""
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run = p.add_run()
                                self._safe_add_picture(run, image_path, width=Inches(3.2))
                                if caption:
                                    cap_elm = OxmlElement('w:p')
                                    p._p.addnext(cap_elm)
                                    cap_p = docx.text.paragraph.Paragraph(cap_elm, cell)
                                    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    cap_p.paragraph_format.space_before = Pt(2.0)
                                    cap_p.paragraph_format.space_after = Pt(4.0)
                                    cap_run = cap_p.add_run(caption)
                                    cap_run.font.size = Pt(9.0)
                                    cap_run.italic = True
                                return True
        return False

    def _safe_add_picture(self, run, image_path: str, width):
        """Safely inserts a picture into a run, auto-converting JP2/unsupported formats via Pillow if needed."""
        try:
            run.add_picture(image_path, width=width)
        except Exception:
            try:
                from PIL import Image as PILImage
                import io
                with PILImage.open(image_path) as pil_img:
                    buf = io.BytesIO()
                    # Convert to standard RGB or RGBA PNG
                    save_format = "PNG"
                    mode = "RGBA" if pil_img.mode in ("RGBA", "LA") else "RGB"
                    pil_img.convert(mode).save(buf, format=save_format)
                    buf.seek(0)
                    run.add_picture(buf, width=width)
            except Exception as e2:
                logger.error(f"Failed to embed image {image_path}: {e2}")
                raise

    def _replace_section_matter_fallback(
        self,
        doc,
        replacements: Dict[str, Any],
        replaced_fields: Set[str]
    ):
        """
        For standard college templates that do not contain {{...}} tokens
        (such as pre-filled sample reports with sections like ABSTRACT, INTRODUCTION, OBJECTIVES),
        this finds the section body paragraphs following the heading and replaces the matter
        in-place while strictly preserving the heading and paragraph style.
        """
        section_heading_map = {
            "abstract": "introduction",
            "introduction": "introduction",
            "objectives": "objectives",
            "problem": "problem_statement",
            "problems we observed": "problem_statement",
            "community awareness": "methodology",
            "methodology": "methodology",
            "technologies": "technologies",
            "implementation": "implementation",
            "results": "results",
            "advantages": "advantages",
            "limitations": "limitations",
            "conclusion": "conclusion",
            "references": "references",
        }

        # Also cover title & presentation metadata on cover page if present
        for i, p in enumerate(doc.paragraphs[:10]):
            txt = p.text.strip()
            # Title replacement on Cover Page
            if "project_title" in replacements and "project_title" not in replaced_fields:
                if "presentation on" in txt.lower() or "project report on" in txt.lower():
                    lines = txt.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("“") or line.startswith('"') or (len(line) > 10 and line.isupper()):
                            new_lines.append(f'"{replacements["project_title"]}"')
                            replaced_fields.add("project_title")
                        else:
                            new_lines.append(line)
                    if "project_title" in replaced_fields:
                        p.text = "\n".join(new_lines)

            # Guide Name replacement on Cover Page
            if "guide_name" in replacements and "guide_name" not in replaced_fields:
                if "under the guidance of" in txt.lower():
                    lines = txt.split("\n")
                    if len(lines) > 1:
                        lines[1] = str(replacements["guide_name"])
                        p.text = "\n".join(lines)
                        replaced_fields.add("guide_name")

            # Student Name / Roll Number replacement on Cover Page
            if "student_name" in replacements and "student_name" not in replaced_fields:
                if "presented by" in txt.lower() and i + 1 < len(doc.paragraphs):
                    next_p = doc.paragraphs[i + 1]
                    if next_p.text.strip():
                        next_p.text = f"{replacements['student_name']}   {replacements.get('roll_number', '')}"
                        replaced_fields.add("student_name")
                        if "roll_number" in replacements:
                            replaced_fields.add("roll_number")

        # Scan for section headings and update the subsequent content paragraph
        for i, p in enumerate(doc.paragraphs):
            t_strip = p.text.strip().lower()
            clean_heading = re.sub(r'[^a-zA-Z\s]', '', t_strip).strip()

            target_field = None
            for key, field_key in section_heading_map.items():
                if clean_heading == key or clean_heading.startswith(key):
                    target_field = field_key
                    break

            if target_field and target_field in replacements and target_field not in replaced_fields:
                val = replacements[target_field]
                for j in range(i + 1, min(i + 5, len(doc.paragraphs))):
                    body_p = doc.paragraphs[j]
                    b_txt = body_p.text.strip()
                    if len(b_txt) < 30 and (b_txt.isupper() or "•" in b_txt or "contents" in b_txt.lower()):
                        break

                    if len(b_txt) > 20:
                        orig_runs = body_p.runs
                        font_name = orig_runs[0].font.name if orig_runs and orig_runs[0].font.name else "Times New Roman"
                        font_size = orig_runs[0].font.size if orig_runs and orig_runs[0].font.size else Pt(11)
                        color = orig_runs[0].font.color.rgb if orig_runs and orig_runs[0].font.color else None

                        if isinstance(val, list):
                            rep_str = "\n".join([f"•  {item}" for item in val])
                        else:
                            rep_str = str(val)

                        body_p.text = rep_str
                        if body_p.runs:
                            body_p.runs[0].font.name = font_name
                            body_p.runs[0].font.size = font_size
                            if color:
                                body_p.runs[0].font.color.rgb = color

                        replaced_fields.add(target_field)
                        break
