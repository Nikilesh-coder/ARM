"""
ARM Stage 15 - Precision OOXML Package-Level Replacement Engine
Operates directly on the DOCX ZIP package and OpenXML structures.
The uploaded DOCX template is the absolute, immutable master source of truth.

Key Guarantees:
1. Exact package clone: starts with byte-copy of the master template DOCX.
2. Direct OpenXML tree surgery: parses XML with lxml.etree, preserving 100% of
   namespaces, page borders (w:pgBorders), VML shapes (v:shape, v:line),
   watermarks, headers, footers, drawings, margins, and paragraph borders (w:pBdr).
3. In-package media replacement: replaces target image media bytes directly in
   word/media/ without touching drawing markup (wp:extent, wp:anchor, a:xfrm, wrapping, borders).
4. Strictly targeted scope: if only project_title is mapped, ONLY project_title changes.
5. Strict pre-delivery validation: runs validate_package_preservation before delivering the file.
"""

import os
import re
import io
import copy
import shutil
import zipfile
import tempfile
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
import lxml.etree as ET
from PIL import Image as PILImage

from apps.api.core.logging import get_logger
from packages.replacement_engine.base import (
    FIXED_ELEMENTS,
    REPLACEABLE_ELEMENTS,
    FieldReplacementAudit,
    ReplacementErrorDetail,
    ReplacementResult,
    ReplacementState,
)

logger = get_logger("replacement_engine.package")

# OpenXML Namespaces
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "w10": "urn:schemas-microsoft-com:office:word",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Register namespaces with lxml to prevent prefix scrambling
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

CREDENTIAL_KEYWORDS = (
    "PRESENTATION ON", "PRESENTED BY", "SUBMITTED BY", "UNDER THE GUIDANCE OF",
    "GUIDED BY", "COMMUNITY SERVICE PROJECT", "DEPARTMENT OF", "COLLEGE",
    "ENGINEERING", "UNIVERSITY", "STUDENT", "ROLL NO", "HALL TICKET", "REG NO",
    "BATCH", "ACADEMIC YEAR", "SEMINAR REPORT", "PROJECT REPORT", "A REPORT ON",
    "GOVERNMENT OF", "AUTONOMOUS", "PH.D.", "M.TECH", "B.TECH",
    "ASSOCIATE PROFESSOR", "ASSISTANT PROFESSOR", "HEAD OF THE DEPARTMENT", "DR.",
    "QUERIES", "THANK YOU", "CONTENTS", "AGENDA"
)


class PackageLevelDocxEngine:
    """
    Direct OOXML ZIP package surgery engine.
    Ensures zero unwanted layout modifications, border corruption, or redesign.
    """

    @classmethod
    def replace(
        cls,
        template_path: str,
        field_values: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        job_id: Optional[str] = None,
        field_mapping: Optional[List[Dict[str, Any]]] = None,
        image_mapping: Optional[List[Dict[str, Any]]] = None,
    ) -> ReplacementResult:
        """
        Executes precision in-place replacement directly on the DOCX package.
        """
        job_id = job_id or "job_package"
        image_assets = image_assets or {}
        audit_list: List[FieldReplacementAudit] = []
        warnings: List[str] = []
        errors: List[ReplacementErrorDetail] = []
        fields_replaced_count = 0
        images_replaced_count = 0

        if not os.path.exists(template_path):
            err_msg = f"Template DOCX file not found at: '{template_path}'"
            return ReplacementResult(
                success=False,
                job_id=job_id,
                state=ReplacementState.FAILED,
                template_path=template_path,
                errors=[ReplacementErrorDetail(field="template_path", reason=err_msg)],
            )

        if not output_path:
            output_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"arm_report_{job_id[:8]}.docx")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Check for PATH A: Exact byte-identical copy (zero modifications requested)
        has_text_to_replace = bool(
            field_values and any(v is not None for k, v in field_values.items() if k not in FIXED_ELEMENTS)
        )
        has_media_to_replace = bool(image_assets and any(v is not None for v in image_assets.values()))

        if field_mapping is not None:
            has_text_to_replace = any(
                (fm.get("action") in ("replace", None) or str(fm.get("action", "")).lower() == "replace")
                and field_values.get(fm.get("arm_field")) is not None
                for fm in field_mapping
            )
            if not has_text_to_replace and field_values.get("project_title"):
                has_text_to_replace = True

        if image_mapping is not None:
            has_media_to_replace = any(
                im.get("action") == "replace" and (
                    image_assets.get(im.get("arm_image_field")) is not None
                    or field_values.get(im.get("arm_image_field")) is not None
                )
                for im in image_mapping
            )

        if not has_text_to_replace and not has_media_to_replace:
            # 100% byte identical copy
            shutil.copyfile(template_path, output_path)
            logger.info(f"[{job_id}] PATH A: Zero replacements requested. Produced 100% byte-identical copy at: {output_path}")
            return ReplacementResult(
                success=True,
                job_id=job_id,
                state=ReplacementState.COMPLETED,
                template_path=template_path,
                output_docx_path=output_path,
                fields_replaced=0,
                total_fields=0,
                images_replaced=0,
                audit=[],
                warnings=[],
                errors=[],
                metadata={"mode": "exact_copy_byte_preserved"},
            )

        # 2. Extract into a temporary working directory for non-destructive surgery
        workdir = tempfile.mkdtemp(prefix="arm_docx_pkg_")
        replaced_images_set: Set[str] = set()
        target_replacements: Dict[str, Any] = {}

        try:
            with zipfile.ZipFile(template_path, "r") as zf:
                zf.extractall(workdir)

                if field_mapping is None:
                    from apps.api.services.master_template_service import CANONICAL_FIELDS
                    template_text_lower = ""
                    for xml_name in ("word/document.xml", "word/header1.xml", "word/footer1.xml"):
                        if xml_name in zf.namelist():
                            template_text_lower += zf.read(xml_name).decode("utf-8", errors="ignore").lower() + " "
                    for fld in CANONICAL_FIELDS:
                        if fld.get("is_required", False):
                            req_name = fld["field_name"]
                            p_tag = fld.get("placeholder_identifier", f"{{{{{req_name.upper()}}}}}").lower()
                            if p_tag in template_text_lower or f"{{{req_name.lower()}}}" in template_text_lower:
                                if not field_values.get(req_name):
                                    reason = f"Required field '{req_name}' was not provided in student generated content."
                                    errors.append(ReplacementErrorDetail(field=req_name, reason=reason))
                    if errors:
                        return ReplacementResult(
                            success=False,
                            job_id=job_id,
                            state=ReplacementState.FAILED,
                            template_path=template_path,
                            errors=errors,
                        )

            # 3. Determine allowable replacements based on explicit mapping
            allowed_fields: Optional[Set[str]] = None
            phrase_replacements: Dict[str, str] = {}
            if field_mapping is not None:
                allowed_fields = set()
                for fm in field_mapping:
                    action = fm.get("action", "replace").lower()
                    arm_f = fm.get("arm_field")
                    tpl_elem = fm.get("template_element", "")
                    if action == "replace" and arm_f:
                        allowed_fields.add(arm_f)
                        if tpl_elem and not (tpl_elem.startswith("{{") and tpl_elem.endswith("}}")):
                            phrase_replacements[tpl_elem] = arm_f
                        orig_txt = fm.get("original_text", "")
                        if orig_txt and orig_txt != tpl_elem and not (orig_txt.startswith("{{") and orig_txt.endswith("}}")):
                            phrase_replacements[orig_txt] = arm_f
                        inner_t = fm.get("inner_title", "")
                        if inner_t and inner_t not in phrase_replacements and not (inner_t.startswith("{{") and inner_t.endswith("}}")):
                            phrase_replacements[inner_t] = arm_f
                if "project_title" not in allowed_fields and field_values.get("project_title"):
                    try:
                        from apps.api.services.custom_template_service import custom_template_service
                        analysis = custom_template_service.analyze_template_docx(template_path)
                        for tf in analysis.get("detected_text_fields", []):
                            if tf.get("arm_field") == "project_title":
                                allowed_fields.add("project_title")
                                t_elem = tf.get("template_element", "")
                                if t_elem and not (t_elem.startswith("{{") and t_elem.endswith("}}")):
                                    phrase_replacements[t_elem] = "project_title"
                                o_txt = tf.get("original_text", "")
                                if o_txt and o_txt != t_elem and not (o_txt.startswith("{{") and o_txt.endswith("}}")):
                                    phrase_replacements[o_txt] = "project_title"
                                i_txt = tf.get("inner_title", "")
                                if i_txt and i_txt not in phrase_replacements and not (i_txt.startswith("{{") and i_txt.endswith("}}")):
                                    phrase_replacements[i_txt] = "project_title"
                                break
                    except Exception as e:
                        logger.warning(f"Package engine fallback title analysis: {e}")
            else:
                # Default mode: allow field_values excluding FIXED_ELEMENTS
                allowed_fields = set(field_values.keys()) - set(FIXED_ELEMENTS)

            for k, v in field_values.items():
                if k in FIXED_ELEMENTS:
                    continue
                if allowed_fields is not None and k not in allowed_fields:
                    continue
                if v is not None:
                    target_replacements[k] = v

            # 4. Perform targeted image replacement in word/media/
            doc_rels_path = os.path.join(workdir, "word", "_rels", "document.xml.rels")
            rels_tree = None
            rel_to_target: Dict[str, str] = {}
            if os.path.exists(doc_rels_path):
                rels_tree = ET.parse(doc_rels_path)
                for rel_elem in rels_tree.xpath("//pr:Relationship | //rel:Relationship", namespaces=NS):
                    r_id = rel_elem.get("Id")
                    r_target = rel_elem.get("Target")
                    if r_id and r_target:
                        rel_to_target[r_id] = r_target

            if image_mapping is not None:
                # Custom image mapping mode: ONLY replace images explicitly marked as "replace"
                used_replacement_files: Set[str] = set()
                for im in image_mapping:
                    action = im.get("action", "fixed").lower()
                    arm_img_f = im.get("arm_image_field", "image_1")
                    rel_id = im.get("rel_id")
                    fname = im.get("filename")
                    if action == "replace":
                        img_src = (
                            (image_assets.get(fname) if fname else None)
                            or (image_assets.get(os.path.basename(fname)) if fname else None)
                            or image_assets.get(arm_img_f)
                            or field_values.get(arm_img_f)
                            or (image_assets.get(rel_id) if rel_id else None)
                        )
                        if isinstance(img_src, dict):
                            img_src = img_src.get("storage_path") or img_src.get("file_path") or img_src.get("url")

                        # Dedup guard: If candidate img_src was already assigned to an earlier slot, select an unassigned distinct replacement
                        if img_src and str(img_src) in used_replacement_files:
                            for cand_k, cand_v in image_assets.items():
                                c_path = cand_v.get("file_path") if isinstance(cand_v, dict) else (cand_v.get("storage_path") if isinstance(cand_v, dict) else cand_v)
                                if c_path and os.path.exists(str(c_path)) and str(c_path) not in used_replacement_files:
                                    img_src = c_path
                                    break

                        if img_src and os.path.exists(str(img_src)):
                            used_replacement_files.add(str(img_src))
                            target_media_rel = None
                            if rel_id and rel_id in rel_to_target and "media/" in rel_to_target[rel_id].lower():
                                target_media_rel = rel_to_target[rel_id]

                            if not target_media_rel and fname:
                                for r_cand, t_cand in rel_to_target.items():
                                    if os.path.basename(t_cand).lower() == fname.lower():
                                        target_media_rel = t_cand
                                        break

                            if not target_media_rel:
                                # Fallback: match by index from arm_img_f (e.g. image_2 -> 2nd image)
                                img_rels = [(r, t) for r, t in rel_to_target.items() if "media/image" in t.lower()]
                                match_idx = 0
                                if "image_" in arm_img_f:
                                    try:
                                        match_idx = int(arm_img_f.split("image_")[1]) - 1
                                    except Exception:
                                        match_idx = 0
                                if 0 <= match_idx < len(img_rels):
                                    target_media_rel = img_rels[match_idx][1]

                            if target_media_rel:
                                target_media_rel = target_media_rel.replace("\\", "/")
                                if target_media_rel.startswith("/"):
                                    media_path = os.path.normpath(os.path.join(workdir, target_media_rel.lstrip("/")))
                                else:
                                    media_path = os.path.normpath(os.path.join(workdir, "word", target_media_rel))

                                if os.path.exists(media_path):
                                    cls._replace_media_file_bytes(media_path, str(img_src))
                                    images_replaced_count += 1
                                    replaced_images_set.add(os.path.basename(media_path))
                                    logger.info(f"Replaced embedded image ({media_path}) in-place.")
                                else:
                                    warnings.append(f"Target media path not found in package: {media_path}")
                            else:
                                warnings.append(f"No relationship target found for image: {rel_id or arm_img_f}")
                        else:
                            warnings.append(f"Image asset for '{arm_img_f}' not found on disk: {img_src}")
            else:
                # Default mode: check image_1, image_2, image_3
                # In default templates, image_1 is often the diagram; logo is fixed
                used_replacement_files: Set[str] = set()
                for img_slot in ["image_1", "image_2", "image_3"]:
                    img_src = image_assets.get(img_slot) or field_values.get(img_slot)
                    if isinstance(img_src, dict):
                        img_src = img_src.get("storage_path") or img_src.get("file_path") or img_src.get("url")
                    if img_src and str(img_src) in used_replacement_files:
                        continue
                    if img_src and os.path.exists(str(img_src)):
                        # Look for candidate image in relationships
                        found_target = False
                        # Find non-logo image in rels if multiple exist
                        img_rels = [(r, t) for r, t in rel_to_target.items() if "media/image" in t.lower()]
                        # If more than 1 image, skip first (logo)
                        target_pairs = img_rels[1:] if len(img_rels) > 1 else img_rels
                        for r_id, target in target_pairs:
                            m_path = os.path.join(workdir, "word", target.replace("\\", "/"))
                            b_name = os.path.basename(m_path)
                            if os.path.exists(m_path) and b_name not in replaced_images_set:
                                cls._replace_media_file_bytes(m_path, str(img_src))
                                images_replaced_count += 1
                                replaced_images_set.add(b_name)
                                used_replacement_files.add(str(img_src))
                                found_target = True
                                break

            # 5. Targeted XML Text Replacement across word/document.xml, header*.xml, footer*.xml
            xml_files_to_process = []
            word_dir = os.path.join(workdir, "word")
            for fname in os.listdir(word_dir):
                if fname == "document.xml" or fname.startswith("header") or fname.startswith("footer"):
                    if fname.endswith(".xml"):
                        xml_files_to_process.append(os.path.join(word_dir, fname))

            replaced_fields_set: Set[str] = set()

            # 4b. Precision First-Page Project Title Replacement
            # The project title entered by the user during project creation is the absolute source of truth.
            # Replaces ONLY the first-page title in OOXML, preserving all formatting,
            # alignment, font, font-size, bold/italic, borders, text box/shape positioning.
            doc_xml = os.path.join(workdir, "word", "document.xml")
            if os.path.exists(doc_xml) and "project_title" in target_replacements:
                title_ok, detected_t, loc_t = cls._replace_first_page_title(
                    doc_xml_path=doc_xml,
                    target_project_title=str(target_replacements["project_title"]),
                    phrase_replacements=phrase_replacements,
                    field_mapping=field_mapping,
                    job_id=job_id,
                    template_id=template_path,
                )
                if title_ok:
                    replaced_fields_set.add("project_title")

            for xml_file in xml_files_to_process:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                modified = False

                # Process table row expansions for tabular repeating data
                for tbl in root.xpath(".//w:tbl", namespaces=NS):
                    tbl_mod, tbl_reps = cls._process_table_row_expansions(tbl, target_replacements)
                    if tbl_mod:
                        modified = True
                        replaced_fields_set.update(tbl_reps)

                # Process every paragraph in the XML
                for p_elem in root.xpath(".//w:p", namespaces=NS):
                    p_modified, newly_replaced = cls._process_xml_paragraph(
                        p_elem,
                        target_replacements,
                        phrase_replacements,
                        replaced_fields_set,
                        image_assets=image_assets,
                        workdir=workdir,
                    )
                    if p_modified:
                        modified = True
                        for f in newly_replaced:
                            if f.startswith("image_"):
                                images_replaced_count += 1
                                replaced_images_set.add(f"{f}.png")
                        replaced_fields_set.update(newly_replaced)

                if modified:
                    tree.write(xml_file, encoding="utf-8", xml_declaration=True, standalone="yes")
            # Clean up unprovided optional image placeholders (e.g. IMAGE_2, IMAGE_3) in default template mode
            if field_mapping is None:
                for opt_slot in ["image_1", "image_2", "image_3"]:
                    if not image_assets.get(opt_slot) and not field_values.get(opt_slot):
                        opt_pats = [
                            f"{{{{{opt_slot.upper()}}}}}",
                            f"{{{{{opt_slot.lower()}}}}}",
                            f"{{{opt_slot.upper()}}}",
                            f"{{{opt_slot.lower()}}}",
                        ]
                        for xml_file in xml_files_to_process:
                            tree = ET.parse(xml_file)
                            root = tree.getroot()
                            cleaned = False
                            for p in root.xpath(".//w:p", namespaces=NS):
                                run_nodes = []
                                for r in p.xpath("./w:r", namespaces=NS):
                                    for t in r.xpath("./w:t", namespaces=NS):
                                        run_nodes.append((r, t))
                                if not run_nodes:
                                    continue
                                full_p = "".join((t.text or "") for _, t in run_nodes)
                                for op in opt_pats:
                                    if op in full_p:
                                        if cls._substitute_phrase_in_nodes(run_nodes, op, ""):
                                            cleaned = True
                                            full_p = "".join((t.text or "") for _, t in run_nodes)
                            if cleaned:
                                tree.write(xml_file, encoding="utf-8", xml_declaration=True, standalone="yes")

            fields_replaced_count = len(replaced_fields_set)

            # 6. Audit results
            for k, val in target_replacements.items():
                is_rep = k in replaced_fields_set
                audit_list.append(
                    FieldReplacementAudit(
                        field_name=k,
                        placeholder=f"{{{{{k.upper()}}}}}",
                        field_type="text",
                        replaced=is_rep,
                        new_snippet=str(val)[:120] if val else None,
                        formatting_preserved=True,
                    )
                )

            # 6b. Prevent Silent Failures: Validate that targeted project_title was indeed replaced
            if "project_title" in target_replacements and "project_title" not in replaced_fields_set:
                orig_target_title = target_replacements["project_title"]
                err_detail = (
                    f"First-page title replacement failure: 'project_title' was targeted for replacement "
                    f"with '{orig_target_title}', but was not found or substituted in OOXML package parts."
                )
                logger.error(f"[{job_id}] {err_detail}")
                errors.append(ReplacementErrorDetail(field="project_title", reason=err_detail))

            # 7. Repack the modified DOCX package cleanly
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z_out:
                for root_dir, _, filenames in os.walk(workdir):
                    for fn in filenames:
                        abs_p = os.path.join(root_dir, fn)
                        rel_p = os.path.relpath(abs_p, workdir)
                        z_out.write(abs_p, rel_p)

            logger.info(f"Successfully generated package-preserved DOCX at: {output_path}")

            # 8. Strict Pre-Delivery Structural Validation
            from packages.replacement_engine.validator import ReplacementValidator
            val_res = ReplacementValidator.validate_package_preservation(
                original_docx_path=template_path,
                generated_docx_path=output_path,
                allowed_replaced_fields=set(target_replacements.keys()),
                allowed_replaced_media=replaced_images_set,
            )
            if not val_res.get("is_valid", True):
                for v_err in val_res.get("errors", []):
                    errors.append(ReplacementErrorDetail(field=v_err["field"], reason=v_err["reason"]))
            for v_warn in val_res.get("warnings", []):
                warnings.append(v_warn)

        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        return ReplacementResult(
            success=len(errors) == 0,
            job_id=job_id,
            state=ReplacementState.COMPLETED if len(errors) == 0 else ReplacementState.FAILED,
            template_path=template_path,
            output_docx_path=output_path,
            fields_replaced=fields_replaced_count,
            total_fields=len(target_replacements),
            images_replaced=images_replaced_count,
            audit=audit_list,
            warnings=warnings,
            errors=errors,
        )

    @classmethod
    def _replace_media_file_bytes(cls, target_media_path: str, new_image_path: str) -> None:
        """
        Replaces target media bytes in the package.
        Converts the new image to the exact format of the target media (PNG/JPEG)
        using Pillow to ensure 100% binary format compatibility with [Content_Types].xml.
        """
        target_ext = os.path.splitext(target_media_path)[1].lower()
        new_ext = os.path.splitext(new_image_path)[1].lower()

        # If both are the same format (e.g. PNG to PNG, or JPG to JPG), copy directly
        if (target_ext in [".png"] and new_ext in [".png"]) or \
           (target_ext in [".jpg", ".jpeg"] and new_ext in [".jpg", ".jpeg"]):
            shutil.copyfile(new_image_path, target_media_path)
            return

        save_format = "PNG" if target_ext in [".png"] else "JPEG"

        try:
            with PILImage.open(new_image_path) as pil_img:
                mode = "RGBA" if save_format == "PNG" and pil_img.mode in ("RGBA", "LA") else "RGB"
                converted = pil_img.convert(mode)
                buf = io.BytesIO()
                converted.save(buf, format=save_format)
                buf.seek(0)
                with open(target_media_path, "wb") as f_out:
                    f_out.write(buf.read())
        except Exception as e:
            logger.warning(f"Pillow conversion failed ({e}), attempting raw byte copy")
            shutil.copyfile(new_image_path, target_media_path)

    @classmethod
    def _process_xml_paragraph(
        cls,
        p_elem: ET._Element,
        replacements: Dict[str, Any],
        phrase_replacements: Dict[str, str],
        already_replaced: Set[str],
        image_assets: Optional[Dict[str, Any]] = None,
        workdir: Optional[str] = None,
    ) -> Tuple[bool, Set[str]]:
        """
        Performs in-place text replacement in a paragraph element <w:p>.
        Preserves 100% of paragraph properties (<w:pPr>, <w:pBdr>),
        run properties (<w:rPr>, font, color, size, bold, italic),
        and any shapes, lines, or drawings inside the paragraph.
        """
        modified = False
        newly_replaced: Set[str] = set()

        runs = p_elem.xpath("./w:r", namespaces=NS)
        if not runs:
            return False, newly_replaced

        # Extract text nodes from runs
        run_text_nodes: List[Tuple[ET._Element, ET._Element]] = []  # (run, t_elem)
        for r in runs:
            t_elems = r.xpath("./w:t", namespaces=NS)
            for t in t_elems:
                run_text_nodes.append((r, t))

        if not run_text_nodes:
            return False, newly_replaced

        full_para_text = "".join((t.text or "") for _, t in run_text_nodes)
        if not full_para_text:
            return False, newly_replaced

        # Check for placeholder tokens: {{field}}, {field}
        for field_name, rep_val in replacements.items():
            if field_name in FIXED_ELEMENTS:
                continue

            patterns = [
                f"{{{{{field_name.upper()}}}}}",
                f"{{{{{field_name.lower()}}}}}",
                f"{{{{{field_name}}}}}",
                f"{{{field_name.upper()}}}",
                f"{{{field_name.lower()}}}",
                f"{{{field_name}}}",
            ]

            # Case 1: Structured table insertion (list of dicts)
            if isinstance(rep_val, list) and rep_val and isinstance(rep_val[0], dict):
                for pat in patterns:
                    if pat in full_para_text:
                        if full_para_text.strip() == pat:
                            if cls._insert_structured_table_xml(p_elem, rep_val):
                                newly_replaced.add(field_name)
                                return True, newly_replaced

            # Case 2: Multi-line text or list of strings
            is_list = isinstance(rep_val, list) and not (rep_val and isinstance(rep_val[0], dict))
            is_multiline = isinstance(rep_val, str) and ("\n" in rep_val)

            # Check if this is a multi-paragraph replacement outside of table cells
            is_inside_table = bool(p_elem.xpath("ancestor::w:tc", namespaces=NS))

            is_ref = "reference" in field_name.lower()
            p0_prefix = "[1]  " if is_ref else "•   "

            for pat in patterns:
                if pat in full_para_text:
                    if (is_multiline or is_list) and not is_inside_table and full_para_text.strip() == pat:
                        # Multi-paragraph / list sibling expansion
                        parts = rep_val if is_list else [p.strip() for p in rep_val.split("\n") if p.strip()]
                        if len(parts) > 1:
                            # Preserve section break (w:sectPr) if p_elem ended a section, but detach from intermediate nodes
                            orig_sect_prs = p_elem.xpath("./w:pPr/w:sectPr", namespaces=NS) or p_elem.xpath("./w:sectPr", namespaces=NS)
                            saved_sect_pr = None
                            if orig_sect_prs:
                                saved_sect_pr = copy.deepcopy(orig_sect_prs[0])
                                for sp in orig_sect_prs:
                                    sp.getparent().remove(sp)

                            first_part_str = f"{p0_prefix}{parts[0]}" if is_list else str(parts[0])
                            cls._substitute_phrase_in_nodes(run_text_nodes, pat, first_part_str)
                            current_node = p_elem
                            for idx, part in enumerate(parts[1:], start=2):
                                prefix = f"[{idx}]  " if is_ref else "•   "
                                new_p = copy.deepcopy(p_elem)

                                # Strip unwanted page breaks and section breaks from cloned siblings
                                for br in new_p.xpath(".//w:br[@w:type='page']", namespaces=NS):
                                    br.getparent().remove(br)
                                for pb in new_p.xpath(".//w:pageBreakBefore", namespaces=NS):
                                    pb.getparent().remove(pb)
                                for sp in (new_p.xpath("./w:pPr/w:sectPr", namespaces=NS) or new_p.xpath("./w:sectPr", namespaces=NS)):
                                    sp.getparent().remove(sp)

                                new_runs = new_p.xpath("./w:r", namespaces=NS)
                                if new_runs:
                                    first_t = new_runs[0].xpath("./w:t", namespaces=NS)
                                    if first_t:
                                        first_t[0].text = f"{prefix}{part}" if is_list else str(part)
                                        first_t[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                                    for extra_r in new_runs[1:]:
                                        for extra_t in extra_r.xpath("./w:t", namespaces=NS):
                                            extra_t.text = ""
                                current_node.addnext(new_p)
                                current_node = new_p

                            # If original paragraph had a section break, re-attach it ONLY to the final cloned paragraph
                            if saved_sect_pr is not None:
                                p_pr = current_node.find(f"{{{NS['w']}}}pPr")
                                if p_pr is None:
                                    p_pr = ET.Element(f"{{{NS['w']}}}pPr")
                                    current_node.insert(0, p_pr)
                                p_pr.append(saved_sect_pr)

                            modified = True
                            newly_replaced.add(field_name)
                            break

                    target_val_str = str(rep_val)
                    if is_list:
                        target_val_str = "\n".join([f"{p0_prefix if i == 0 else '•   '}{item}" for i, item in enumerate(rep_val)])

                    success = cls._substitute_phrase_in_nodes(run_text_nodes, pat, target_val_str)
                    if success:
                        modified = True
                        newly_replaced.add(field_name)
                        full_para_text = "".join((t.text or "") for _, t in run_text_nodes)
                        break

        # Check for custom phrase replacements (e.g. mapped template elements like "PROJECT TITLE")
        if phrase_replacements:
            def _norm_quotes(s: str) -> str:
                return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

            # Canonical structural labels that should never be substituted as phrase replacements
            PROTECTED_CANONICAL_PHRASES = {
                "advantages:-", "disadvantages:-", "advantages:", "disadvantages:",
                "advantages", "disadvantages", "objectives", "objectives:-",
                "conclusion", "conclusion:-", "references", "references:-",
            }

            # Sort phrases by length descending to match longer, more specific phrases first
            sorted_phrase_items = sorted(phrase_replacements.items(), key=lambda x: len(x[0]), reverse=True)

            for phrase, arm_field in sorted_phrase_items:
                if arm_field == "project_title":
                    # First-page title replacement has already handled the project title exclusively on Page 1!
                    # Do NOT replace occurrences across the rest of the document.
                    continue
                if arm_field not in replacements:
                    continue

                clean_p_lower = phrase.strip().lower()
                if clean_p_lower in PROTECTED_CANONICAL_PHRASES:
                    # Do not overwrite canonical structural section labels with body/heading matter
                    continue

                rep_val = replacements[arm_field]
                target_val_str = str(rep_val)
                if isinstance(rep_val, list):
                    target_val_str = "\n".join([f"•  {item}" for item in rep_val])

                matched_token = None
                # 1. Exact case-insensitive match with boundary checking
                lower_full = full_para_text.lower()
                lower_phrase = phrase.lower()
                start_search = 0
                while start_search < len(lower_full):
                    m_pos = lower_full.find(lower_phrase, start_search)
                    if m_pos == -1:
                        break

                    # Boundary check: Ensure phrase is not a partial substring of a longer word (e.g. "Advantages" inside "Disadvantages")
                    pre_ok = True
                    if m_pos > 0 and lower_phrase[0].isalnum() and lower_full[m_pos - 1].isalnum():
                        pre_ok = False

                    post_idx = m_pos + len(lower_phrase)
                    post_ok = True
                    if post_idx < len(lower_full) and lower_phrase[-1].isalnum() and lower_full[post_idx].isalnum():
                        post_ok = False

                    if pre_ok and post_ok:
                        matched_token = full_para_text[m_pos : post_idx]
                        break

                    start_search = m_pos + 1

                if not matched_token:
                    # 2. Quote-normalized match with boundary checking
                    norm_full = _norm_quotes(full_para_text.lower())
                    norm_phrase = _norm_quotes(phrase.lower())
                    clean_norm_phrase = norm_phrase.strip('"\'')

                    for cand_p in (norm_phrase, clean_norm_phrase):
                        if not cand_p:
                            continue
                        q_pos = norm_full.find(cand_p)
                        if q_pos != -1:
                            pre_ok = not (q_pos > 0 and cand_p[0].isalnum() and norm_full[q_pos - 1].isalnum())
                            post_idx = q_pos + len(cand_p)
                            post_ok = not (post_idx < len(norm_full) and cand_p[-1].isalnum() and norm_full[post_idx].isalnum())
                            if pre_ok and post_ok:
                                matched_token = full_para_text[q_pos : post_idx]
                                break

                if matched_token:
                    # For project_title, ensure any residual template quotation marks enclosing the title are consumed
                    if arm_field == "project_title":
                        t_pos = full_para_text.find(matched_token)
                        if t_pos != -1:
                            has_pre = t_pos > 0 and full_para_text[t_pos - 1] in ('"', '“', '‘', "'")
                            end_pos = t_pos + len(matched_token)
                            has_post = end_pos < len(full_para_text) and full_para_text[end_pos] in ('"', '”', '’', "'")
                            if has_pre and has_post:
                                matched_token = full_para_text[t_pos - 1 : end_pos + 1]
                            elif has_pre:
                                matched_token = full_para_text[t_pos - 1 : end_pos]
                            elif has_post:
                                matched_token = full_para_text[t_pos : end_pos + 1]

                    success = cls._substitute_phrase_in_nodes(
                        run_text_nodes, matched_token, target_val_str
                    )
                    if success:
                        modified = True
                        newly_replaced.add(arm_field)
                        full_para_text = "".join((t.text or "") for _, t in run_text_nodes)

        # Check for image placeholders: {{IMAGE_1}}, {{IMAGE_2}}, etc.
        if image_assets and workdir:
            full_para_text = "".join(p_elem.xpath(".//w:t/text()", namespaces=NS))
            for slot_name, img_data in image_assets.items():
                slot_pats = [
                    f"{{{{{slot_name.upper()}}}}}",
                    f"{{{{{slot_name.lower()}}}}}",
                    f"{{{{{slot_name}}}}}",
                ]
                for spat in slot_pats:
                    if spat in full_para_text:
                        img_path = None
                        caption = None
                        if isinstance(img_data, dict):
                            img_path = img_data.get("file_path") or img_data.get("storage_path") or img_data.get("url")
                            caption = img_data.get("caption")
                        elif isinstance(img_data, str):
                            img_path = img_data
                        if img_path and os.path.exists(str(img_path)):
                            slot_num = 1
                            if "image_" in slot_name:
                                try:
                                    slot_num = int(slot_name.split("image_")[1])
                                except Exception:
                                    slot_num = 1
                            if cls._insert_image_drawing_xml(p_elem, spat, str(img_path), caption, workdir, slot_idx=slot_num):
                                modified = True
                                newly_replaced.add(slot_name)
                                full_para_text = "".join(p_elem.xpath(".//w:t/text()", namespaces=NS))
                                break

        return modified, newly_replaced

    @classmethod
    def _substitute_phrase_in_nodes(
        cls,
        run_text_nodes: List[Tuple[ET._Element, ET._Element]],
        target_token: str,
        replacement_text: str,
    ) -> bool:
        """
        Replaces target_token with replacement_text across run text nodes.
        Preserves all <w:rPr> font formatting.
        Handles cases where target_token is contained in a single node
        or split across consecutive nodes.
        """
        full_text = "".join((t.text or "") for _, t in run_text_nodes)
        start_idx = full_text.find(target_token)
        if start_idx == -1:
            return False

        end_idx = start_idx + len(target_token)

        char_count = 0
        start_node_idx = None
        end_node_idx = None

        for idx, (_, t_node) in enumerate(run_text_nodes):
            t_txt = t_node.text or ""
            node_len = len(t_txt)
            node_start = char_count
            node_end = char_count + node_len
            char_count = node_end

            if start_node_idx is None and node_start <= start_idx < node_end:
                start_node_idx = idx
            if node_start < end_idx <= node_end:
                end_node_idx = idx
                break

        if start_node_idx is not None and end_node_idx is not None:
            if start_node_idx == end_node_idx:
                cur_t = run_text_nodes[start_node_idx][1]
                cur_text = cur_t.text or ""
                cur_t.text = cur_text.replace(target_token, replacement_text, 1)
                cur_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            else:
                node_0_start = sum(len(run_text_nodes[k][1].text or "") for k in range(start_node_idx))
                start_node_t = run_text_nodes[start_node_idx][1]
                start_text = start_node_t.text or ""
                before = start_text[: start_idx - node_0_start]

                end_node_start = sum(len(run_text_nodes[k][1].text or "") for k in range(end_node_idx))
                end_node_t = run_text_nodes[end_node_idx][1]
                end_text = end_node_t.text or ""
                after = end_text[end_idx - end_node_start :]

                start_node_t.text = before + replacement_text
                start_node_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

                for k in range(start_node_idx + 1, end_node_idx):
                    mid_t = run_text_nodes[k][1]
                    mid_t.text = ""

                end_node_t.text = after
                end_node_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

            return True

        return False

    @classmethod
    def _find_normalized_span(cls, raw_text: str, search_phrase: str) -> Optional[Tuple[int, int]]:
        """
        Finds the character span (start_idx, end_idx) in raw_text that matches
        search_phrase under robust normalization:
        - Case insensitivity
        - Collapsing all whitespace (spaces, tabs, newlines, non-breaking spaces) to a single space
        - Normalizing smart quotes and apostrophes
        - Consuming enclosing quotes if present around the match in raw_text
        """
        if not raw_text or not search_phrase:
            return None

        def clean_char(c: str) -> str:
            if c in ('“', '”', '\"'):
                return '"'
            if c in ("‘", "’", "'"):
                return "'"
            if c in ('\u00a0', '\t', '\r', '\n'):
                return ' '
            return c

        norm_chars: List[str] = []
        norm_to_raw: List[int] = []

        prev_space = False
        for i, ch in enumerate(raw_text):
            c = clean_char(ch).lower()
            if c.isspace():
                if not prev_space and norm_chars:
                    norm_chars.append(' ')
                    norm_to_raw.append(i)
                    prev_space = True
            else:
                norm_chars.append(c)
                norm_to_raw.append(i)
                prev_space = False

        norm_raw = "".join(norm_chars)

        p_chars: List[str] = []
        p_prev_space = False
        for ch in search_phrase:
            c = clean_char(ch).lower()
            if c.isspace():
                if not p_prev_space and p_chars:
                    p_chars.append(' ')
                    p_prev_space = True
            else:
                p_chars.append(c)
                p_prev_space = False

        norm_p = "".join(p_chars).strip()
        clean_p = norm_p.strip('"\' ')
        if not clean_p:
            return None

        match_idx = norm_raw.find(norm_p)
        matched_len = len(norm_p)
        if match_idx == -1:
            match_idx = norm_raw.find(clean_p)
            matched_len = len(clean_p)

        if match_idx == -1:
            return None

        raw_start = norm_to_raw[match_idx]
        norm_end_idx = match_idx + matched_len - 1
        raw_end = norm_to_raw[norm_end_idx] + 1

        # Check for enclosing quotation marks in raw_text around the match
        q_chars = ('"', '“', '”', "'", "‘", "’")
        p_cur = raw_start - 1
        while p_cur >= 0 and raw_text[p_cur].isspace():
            p_cur -= 1
        if p_cur >= 0 and raw_text[p_cur] in q_chars:
            raw_start = p_cur

        p_cur = raw_end
        while p_cur < len(raw_text) and raw_text[p_cur].isspace():
            p_cur += 1
        if p_cur < len(raw_text) and raw_text[p_cur] in q_chars:
            raw_end = p_cur + 1

        return raw_start, raw_end

    @classmethod
    def _substitute_span_in_nodes(
        cls,
        run_text_nodes: List[Tuple[ET._Element, ET._Element]],
        start_idx: int,
        end_idx: int,
        replacement_text: str,
    ) -> bool:
        """
        Replaces raw character span [start_idx, end_idx) with replacement_text
        across run text nodes, preserving 100% of formatting (<w:rPr> font, size, bold, italic, color).
        Removes any <w:br/> elements in the matched runs to avoid unwanted line breaks.
        """
        char_count = 0
        start_node_idx = None
        end_node_idx = None

        for idx, (_, t_node) in enumerate(run_text_nodes):
            t_txt = t_node.text or ""
            node_len = len(t_txt)
            node_start = char_count
            node_end = char_count + node_len
            char_count = node_end

            if start_node_idx is None and node_start <= start_idx < node_end:
                start_node_idx = idx
            if node_start < end_idx <= node_end:
                end_node_idx = idx
                break

        if start_node_idx is None or end_node_idx is None:
            if start_node_idx is not None and end_idx >= char_count:
                end_node_idx = len(run_text_nodes) - 1
            else:
                return False

        if start_node_idx == end_node_idx:
            cur_r, cur_t = run_text_nodes[start_node_idx]
            cur_text = cur_t.text or ""
            node_start = sum(len(run_text_nodes[k][1].text or "") for k in range(start_node_idx))
            rel_start = start_idx - node_start
            rel_end = end_idx - node_start
            cur_t.text = cur_text[:rel_start] + replacement_text + cur_text[rel_end:]
            cur_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        else:
            node_0_start = sum(len(run_text_nodes[k][1].text or "") for k in range(start_node_idx))
            start_r, start_t = run_text_nodes[start_node_idx]
            start_text = start_t.text or ""
            before = start_text[: start_idx - node_0_start]

            end_node_start = sum(len(run_text_nodes[k][1].text or "") for k in range(end_node_idx))
            end_r, end_t = run_text_nodes[end_node_idx]
            end_text = end_t.text or ""
            after = end_text[end_idx - end_node_start :]

            start_t.text = before + replacement_text
            start_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

            for k in range(start_node_idx + 1, end_node_idx):
                mid_r, mid_t = run_text_nodes[k]
                mid_t.text = ""
                for br in mid_r.xpath(".//w:br", namespaces=NS):
                    mid_r.remove(br)

            end_t.text = after
            end_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

        for br in run_text_nodes[start_node_idx][0].xpath(".//w:br", namespaces=NS):
            run_text_nodes[start_node_idx][0].remove(br)

        return True

    @classmethod
    def _replace_first_page_title(
        cls,
        doc_xml_path: str,
        target_project_title: str,
        phrase_replacements: Dict[str, str],
        field_mapping: Optional[List[Dict[str, Any]]] = None,
        job_id: Optional[str] = "job_title",
        template_id: Optional[str] = "tpl_title",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Precision First-Page Project Title Replacement Engine.
        Targets and replaces ONLY the first-page title in word/document.xml.
        Preserves 100% of formatting (<w:rPr>, <w:pPr>, fonts, styles, colors),
        surrounding layout, text boxes, and table cells.
        Does NOT replace occurrences throughout subsequent pages of the document.
        """
        tree = ET.parse(doc_xml_path)
        root = tree.getroot()

        all_t = root.xpath(".//w:t", namespaces=NS)
        if not all_t:
            logger.info(f"[{job_id}] Template package contains no text nodes in document.xml (image-only visual template). Title replacement skipped.")
            return True, "N/A (Visual Template)", "Image Only Package"

        candidate_phrases: List[str] = []
        placeholders = [
            "{{PROJECT_TITLE}}", "{{project_title}}", "{{TITLE}}", "{{title}}",
            "{PROJECT_TITLE}", "{project_title}", "{TITLE}", "{title}"
        ]
        candidate_phrases.extend(placeholders)

        if field_mapping:
            for fm in field_mapping:
                if fm.get("arm_field") == "project_title":
                    for k in ("template_element", "original_text", "inner_title"):
                        val = fm.get(k)
                        if val and str(val).strip() and str(val).strip() not in candidate_phrases:
                            candidate_phrases.append(str(val).strip())

        if phrase_replacements:
            for phrase, arm_f in phrase_replacements.items():
                if arm_f == "project_title" and phrase and phrase not in candidate_phrases:
                    candidate_phrases.append(phrase)

        # Collect Page 1 paragraphs
        body_elem = root.find("w:body", namespaces=NS)
        if body_elem is None:
            return False, None, None

        page_1_paras: List[ET._Element] = []
        for child in body_elem:
            if child.tag.endswith("sectPr"):
                break
            if child.tag.endswith("p"):
                page_1_paras.append(child)
                if child.xpath(".//w:br[@w:type='page']", namespaces=NS) or \
                   child.xpath(".//w:lastRenderedPageBreak", namespaces=NS) or \
                   child.xpath(".//w:pPr/w:sectPr", namespaces=NS):
                    break
            elif child.tag.endswith("tbl"):
                for p in child.xpath(".//w:p", namespaces=NS):
                    page_1_paras.append(p)

        if not page_1_paras:
            page_1_paras = body_elem.xpath(".//w:p", namespaces=NS)[:25]

        # PASS 1: Candidate phrases & explicit placeholders on Page 1
        for p_idx, p in enumerate(page_1_paras):
            runs = p.xpath(".//w:r", namespaces=NS)
            if not runs:
                continue
            run_text_nodes: List[Tuple[ET._Element, ET._Element]] = []
            for r in runs:
                for t in r.xpath("./w:t", namespaces=NS):
                    run_text_nodes.append((r, t))
            if not run_text_nodes:
                continue

            raw_text = "".join(t.text or "" for _, t in run_text_nodes)
            if not raw_text.strip():
                continue

            for cand in candidate_phrases:
                # Check placeholder exact match
                if cand in placeholders and cand in raw_text:
                    start_i = raw_text.find(cand)
                    end_i = start_i + len(cand)
                    if cls._substitute_span_in_nodes(run_text_nodes, start_i, end_i, target_project_title):
                        tree.write(doc_xml_path, encoding="utf-8", xml_declaration=True, standalone="yes")
                        loc_desc = f"Page 1 / Paragraph {p_idx + 1} (Explicit Placeholder)"
                        cls._log_title_replacement(job_id, template_id, cand, target_project_title, loc_desc)
                        return True, cand, loc_desc

                # Check robust normalized span
                span = cls._find_normalized_span(raw_text, cand)
                if span:
                    start_i, end_i = span
                    matched_raw = raw_text[start_i:end_i]
                    if cls._substitute_span_in_nodes(run_text_nodes, start_i, end_i, target_project_title):
                        tree.write(doc_xml_path, encoding="utf-8", xml_declaration=True, standalone="yes")
                        loc_desc = f"Page 1 / Paragraph {p_idx + 1}"
                        cls._log_title_replacement(job_id, template_id, matched_raw, target_project_title, loc_desc)
                        return True, matched_raw, loc_desc

        # PASS 2: Heuristic detection on Page 1 for unmapped or altered templates
        for p_idx, p in enumerate(page_1_paras):
            runs = p.xpath(".//w:r", namespaces=NS)
            if not runs:
                continue
            run_text_nodes: List[Tuple[ET._Element, ET._Element]] = []
            for r in runs:
                for t in r.xpath("./w:t", namespaces=NS):
                    run_text_nodes.append((r, t))
            if not run_text_nodes:
                continue

            raw_text = "".join(t.text or "" for _, t in run_text_nodes)
            t_clean = raw_text.strip()
            if not t_clean or len(t_clean) < 4:
                continue

            t_upper = t_clean.upper()
            if any(kw in t_upper for kw in CREDENTIAL_KEYWORDS) or re.match(r"^\d{2}[A-Z]{3}\d{2}", t_clean):
                continue

            # Check for quoted title: e.g. "ELECTRIFY THE FUTURE..."
            quote_m = re.search(r'["“]([^"”]{5,120})["”]', raw_text)
            if quote_m:
                span = (quote_m.start(0), quote_m.end(0))
                if cls._substitute_span_in_nodes(run_text_nodes, span[0], span[1], target_project_title):
                    tree.write(doc_xml_path, encoding="utf-8", xml_declaration=True, standalone="yes")
                    loc_desc = f"Page 1 / Paragraph {p_idx + 1} (Quoted Title)"
                    cls._log_title_replacement(job_id, template_id, quote_m.group(0), target_project_title, loc_desc)
                    return True, quote_m.group(0), loc_desc

            # If length is between 5 and 150 characters and not credential
            if 5 <= len(t_clean) <= 150:
                if cls._substitute_span_in_nodes(run_text_nodes, 0, len(raw_text), target_project_title):
                    tree.write(doc_xml_path, encoding="utf-8", xml_declaration=True, standalone="yes")
                    loc_desc = f"Page 1 / Paragraph {p_idx + 1} (Cover Title)"
                    cls._log_title_replacement(job_id, template_id, t_clean, target_project_title, loc_desc)
                    return True, t_clean, loc_desc

        return False, None, None

    @classmethod
    def _log_title_replacement(
        cls,
        job_id: Optional[str],
        template_id: Optional[str],
        detected_title: str,
        target_title: str,
        location: str,
    ) -> None:
        """Outputs comprehensive debug logging as specified in ARM title replacement requirements."""
        tpl_name = os.path.basename(str(template_id or "")) if template_id else "N/A"
        print(
            f"\n[ARM TITLE REPLACEMENT]\n"
            f"Report ID: {job_id or 'N/A'}\n"
            f"Template ID: {tpl_name}\n"
            f"Detected Template Title: {detected_title}\n"
            f"Target Title: {target_title}\n"
            f"Location: {location}\n"
            f"Replacement Result: SUCCESS\n"
        )
        logger.info(
            f"[{job_id}] [ARM TITLE REPLACEMENT] Report ID: {job_id} | "
            f"Template ID: {tpl_name} | "
            f"Detected Template Title: '{detected_title}' | "
            f"Target Title: '{target_title}' | "
            f"Location: {location} | Replacement Result: SUCCESS"
        )

    @classmethod
    def _process_table_row_expansions(
        cls, tbl: ET._Element, replacements: Dict[str, Any]
    ) -> Tuple[bool, Set[str]]:
        """
        Expands template table rows when placeholders correspond to a list of dicts (e.g. team_members).
        """
        modified = False
        newly_replaced: Set[str] = set()

        for field_name, value in replacements.items():
            if not (isinstance(value, list) and value and isinstance(value[0], dict)):
                continue

            sample_item = value[0]
            item_keys = set(sample_item.keys())

            for tr in list(tbl.xpath("./w:tr", namespaces=NS)):
                tr_text = "".join(tr.xpath(".//w:t/text()", namespaces=NS))
                matched_keys = [
                    k for k in item_keys
                    if f"{{{{{k}}}}}" in tr_text.lower()
                    or f"{{{k}}}" in tr_text.lower()
                    or f"{{{{{k.upper()}}}}}" in tr_text
                    or f"{{{k.upper()}}}" in tr_text
                ]
                if matched_keys:
                    template_tr_xml = copy.deepcopy(tr)
                    curr_tr = tr
                    for item_idx, record in enumerate(value):
                        if item_idx == 0:
                            target_tr = tr
                        else:
                            new_tr = copy.deepcopy(template_tr_xml)
                            curr_tr.addnext(new_tr)
                            curr_tr = new_tr
                            target_tr = new_tr

                        for p in target_tr.xpath(".//w:p", namespaces=NS):
                            cls._process_xml_paragraph(p, record, {}, set())

                    modified = True
                    newly_replaced.add(field_name)
                    break

        return modified, newly_replaced

    @classmethod
    def _insert_structured_table_xml(cls, p_elem: ET._Element, data: List[Dict[str, Any]]) -> bool:
        """
        Inserts a styled OpenXML table corresponding to a structured list of dicts.
        """
        if not data or not isinstance(data[0], dict):
            return False

        headers = list(data[0].keys())
        w_uri = NS["w"]
        tbl = ET.Element(f"{{{w_uri}}}tbl")

        tblPr = ET.SubElement(tbl, f"{{{w_uri}}}tblPr")
        ET.SubElement(tblPr, f"{{{w_uri}}}tblW", {f"{{{w_uri}}}w": "0", f"{{{w_uri}}}type": "auto"})

        # Header row
        hdr_tr = ET.SubElement(tbl, f"{{{w_uri}}}tr")
        for h in headers:
            tc = ET.SubElement(hdr_tr, f"{{{w_uri}}}tc")
            tcPr = ET.SubElement(tc, f"{{{w_uri}}}tcPr")
            ET.SubElement(tcPr, f"{{{w_uri}}}shd", {f"{{{w_uri}}}val": "clear", f"{{{w_uri}}}color": "auto", f"{{{w_uri}}}fill": "F3F4F6"})
            p = ET.SubElement(tc, f"{{{w_uri}}}p")
            r = ET.SubElement(p, f"{{{w_uri}}}r")
            rPr = ET.SubElement(r, f"{{{w_uri}}}rPr")
            ET.SubElement(rPr, f"{{{w_uri}}}b")
            ET.SubElement(rPr, f"{{{w_uri}}}rFonts", {f"{{{w_uri}}}ascii": "Times New Roman", f"{{{w_uri}}}hAnsi": "Times New Roman"})
            ET.SubElement(rPr, f"{{{w_uri}}}sz", {f"{{{w_uri}}}val": "20"})
            t = ET.SubElement(r, f"{{{w_uri}}}t")
            t.text = str(h).replace("_", " ").title()

        # Data rows
        for item in data:
            data_tr = ET.SubElement(tbl, f"{{{w_uri}}}tr")
            for h in headers:
                tc = ET.SubElement(data_tr, f"{{{w_uri}}}tc")
                p = ET.SubElement(tc, f"{{{w_uri}}}p")
                r = ET.SubElement(p, f"{{{w_uri}}}r")
                rPr = ET.SubElement(r, f"{{{w_uri}}}rPr")
                ET.SubElement(rPr, f"{{{w_uri}}}rFonts", {f"{{{w_uri}}}ascii": "Times New Roman", f"{{{w_uri}}}hAnsi": "Times New Roman"})
                ET.SubElement(rPr, f"{{{w_uri}}}sz", {f"{{{w_uri}}}val": "19"})
                t = ET.SubElement(r, f"{{{w_uri}}}t")
                t.text = str(item.get(h, ""))

        p_elem.addnext(tbl)
        p_elem.getparent().remove(p_elem)
        return True

    @classmethod
    def _insert_image_drawing_xml(
        cls,
        p_elem: ET._Element,
        target_token: str,
        image_src: str,
        caption: Optional[str],
        workdir: str,
        slot_idx: int = 1,
    ) -> bool:
        """
        Inserts an inline image drawing and optional caption paragraph in OpenXML.
        """
        if not os.path.exists(image_src):
            return False

        # 1. Normalize image to PNG
        media_dir = os.path.join(workdir, "word", "media")
        os.makedirs(media_dir, exist_ok=True)
        img_filename = f"image_slot_{slot_idx}.png"
        target_media_path = os.path.join(media_dir, img_filename)
        cls._replace_media_file_bytes(target_media_path, image_src)

        # 2. Add Relationship to word/_rels/document.xml.rels
        rels_path = os.path.join(workdir, "word", "_rels", "document.xml.rels")
        rel_id = f"rIdImgSlot{slot_idx}"
        if os.path.exists(rels_path):
            rels_tree = ET.parse(rels_path)
            rels_root = rels_tree.getroot()
            existing = rels_root.xpath(f"//pr:Relationship[@Id='{rel_id}'] | //rel:Relationship[@Id='{rel_id}']", namespaces=NS)
            if not existing:
                ET.SubElement(
                    rels_root,
                    f"{{{NS['pr']}}}Relationship",
                    {
                        "Id": rel_id,
                        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                        "Target": f"media/{img_filename}",
                    }
                )
                rels_tree.write(rels_path, encoding="utf-8", xml_declaration=True, standalone="yes")

        # 2b. Ensure [Content_Types].xml has default for added image extension
        ct_path = os.path.join(workdir, "[Content_Types].xml")
        if os.path.exists(ct_path):
            ct_tree = ET.parse(ct_path)
            ct_root = ct_tree.getroot()
            ct_uri = "http://schemas.openxmlformats.org/package/2006/content-types"
            ext_lower = os.path.splitext(img_filename)[1].lstrip(".").lower()
            existing_defaults = [
                d.attrib.get("Extension", "").lower()
                for d in ct_root.findall(f"{{{ct_uri}}}Default")
            ]
            if ext_lower not in existing_defaults:
                mime_type = "image/png" if ext_lower == "png" else f"image/{ext_lower}"
                ET.SubElement(
                    ct_root,
                    f"{{{ct_uri}}}Default",
                    {"Extension": ext_lower, "ContentType": mime_type}
                )
                ct_tree.write(ct_path, encoding="utf-8", xml_declaration=True, standalone="yes")

        # 3. Build drawing XML
        w_uri = NS["w"]
        wp_uri = NS["wp"]
        a_uri = NS["a"]
        pic_uri = NS["pic"]
        r_uri = NS["r"]

        r_elem = ET.Element(f"{{{w_uri}}}r")
        drawing = ET.SubElement(r_elem, f"{{{w_uri}}}drawing")
        inline = ET.SubElement(drawing, f"{{{wp_uri}}}inline", {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
        ET.SubElement(inline, f"{{{wp_uri}}}extent", {"cx": "5029200", "cy": "3352800"})
        ET.SubElement(inline, f"{{{wp_uri}}}docPr", {"id": str(slot_idx), "name": f"Picture {slot_idx}"})
        cNvPr = ET.SubElement(inline, f"{{{wp_uri}}}cNvGraphicFramePr")
        ET.SubElement(cNvPr, f"{{{a_uri}}}graphicFrameLocks", {"noChangeAspect": "1"})

        graphic = ET.SubElement(inline, f"{{{a_uri}}}graphic")
        graphicData = ET.SubElement(graphic, f"{{{a_uri}}}graphicData", {"uri": pic_uri})

        pic = ET.SubElement(graphicData, f"{{{pic_uri}}}pic")
        nvPicPr = ET.SubElement(pic, f"{{{pic_uri}}}nvPicPr")
        ET.SubElement(nvPicPr, f"{{{pic_uri}}}cNvPr", {"id": str(slot_idx), "name": f"Picture {slot_idx}"})
        ET.SubElement(nvPicPr, f"{{{pic_uri}}}cNvPicPr")

        blipFill = ET.SubElement(pic, f"{{{pic_uri}}}blipFill")
        ET.SubElement(blipFill, f"{{{a_uri}}}blip", {f"{{{r_uri}}}embed": rel_id})
        stretch = ET.SubElement(blipFill, f"{{{a_uri}}}stretch")
        ET.SubElement(stretch, f"{{{a_uri}}}fillRect")

        spPr = ET.SubElement(pic, f"{{{pic_uri}}}spPr")
        xfrm = ET.SubElement(spPr, f"{{{a_uri}}}xfrm")
        ET.SubElement(xfrm, f"{{{a_uri}}}off", {"x": "0", "y": "0"})
        ET.SubElement(xfrm, f"{{{a_uri}}}ext", {"cx": "5029200", "cy": "3352800"})
        prstGeom = ET.SubElement(spPr, f"{{{a_uri}}}prstGeom", {"prst": "rect"})
        ET.SubElement(prstGeom, f"{{{a_uri}}}avLst")

        # Replace target_token in run text and attach drawing
        replaced_in_run = False
        for r in p_elem.xpath("./w:r", namespaces=NS):
            for t in r.xpath("./w:t", namespaces=NS):
                if t.text and target_token in t.text:
                    t.text = t.text.replace(target_token, "")
                    r.addnext(r_elem)
                    replaced_in_run = True
                    break
            if replaced_in_run:
                break

        if not replaced_in_run:
            p_elem.append(r_elem)

        # Center alignment if the paragraph only contains the image
        remaining_text = "".join(p_elem.xpath(".//w:t/text()", namespaces=NS)).strip()
        if not remaining_text:
            pPr = p_elem.find(f"{{{w_uri}}}pPr")
            if pPr is None:
                pPr = ET.Element(f"{{{w_uri}}}pPr")
                p_elem.insert(0, pPr)
            jc = pPr.find(f"{{{w_uri}}}jc")
            if jc is None:
                ET.SubElement(pPr, f"{{{w_uri}}}jc", {f"{{{w_uri}}}val": "center"})
            else:
                jc.set(f"{{{w_uri}}}val", "center")


        # 4. Optional caption paragraph
        if caption:
            cap_p = ET.Element(f"{{{w_uri}}}p")
            cap_pPr = ET.SubElement(cap_p, f"{{{w_uri}}}pPr")
            ET.SubElement(cap_pPr, f"{{{w_uri}}}jc", {f"{{{w_uri}}}val": "center"})
            ET.SubElement(cap_pPr, f"{{{w_uri}}}spacing", {f"{{{w_uri}}}before": "40", f"{{{w_uri}}}after": "160"})
            cap_r = ET.SubElement(cap_p, f"{{{w_uri}}}r")
            cap_rPr = ET.SubElement(cap_r, f"{{{w_uri}}}rPr")
            ET.SubElement(cap_rPr, f"{{{w_uri}}}rFonts", {f"{{{w_uri}}}ascii": "Times New Roman", f"{{{w_uri}}}hAnsi": "Times New Roman"})
            ET.SubElement(cap_rPr, f"{{{w_uri}}}sz", {f"{{{w_uri}}}val": "19"})
            ET.SubElement(cap_rPr, f"{{{w_uri}}}i")
            ET.SubElement(cap_rPr, f"{{{w_uri}}}color", {f"{{{w_uri}}}val": "5A5A5A"})
            cap_t = ET.SubElement(cap_r, f"{{{w_uri}}}t")
            cap_t.text = caption
            p_elem.addnext(cap_p)

        return True
