"""
ARM Intelligent Image Replacement Engine
Stage: Intelligent Image Replacement in Existing DOCX Templates

Analyzes every embedded image in uploaded DOCX templates, classifies them into
fixed (college logos, official seals, fixed design assets) vs replaceable
(topic-specific illustrations, section diagrams, full-slide screenshots),
synthesizes high-fidelity domain-grounded replacement images tailored to the student's
project title and problem statement, and executes precision package-level replacement.
"""

import os
import io
import re
import math
import zipfile
import shutil
import tempfile
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set
import lxml.etree as ET
from PIL import Image as PILImage, ImageDraw, ImageFont
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from apps.api.core.logging import get_logger

logger = get_logger("intelligent_image.service")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


class IntelligentImageService:
    """
    Core service for intelligent DOCX image analysis, classification,
    domain-aware visual generation, and OOXML package surgery.
    """

    @classmethod
    def analyze_docx_images(cls, template_path: str) -> List[Dict[str, Any]]:
        """
        Extracts and analyzes every embedded image in the DOCX package.
        Identifies location, dimensions, aspect ratio, surrounding text,
        and classifies into:
        - college_logo: Institutional logo/crest (strictly preserved)
        - fixed_asset: Decorative border, divider, bullet icon (strictly preserved)
        - full_slide_screenshot: Full-slide cover or slide screenshot (recreated for new topic)
        - topic_specific: Technical section diagram/photo/card (replaced with new visual)
        - general_illustration: Generic reusable visual
        """
        if not os.path.exists(template_path):
            return []

        analyzed_images: List[Dict[str, Any]] = []

        try:
            with zipfile.ZipFile(template_path, "r") as zf:
                namelist = zf.namelist()
                media_files = {name: zf.read(name) for name in namelist if "media/" in name}

                # 1. Parse document relationships
                rels_xml = zf.read("word/_rels/document.xml.rels") if "word/_rels/document.xml.rels" in namelist else None
                doc_xml = zf.read("word/document.xml") if "word/document.xml" in namelist else None

                if not rels_xml or not doc_xml:
                    return []

                rels_root = ET.fromstring(rels_xml)
                rel_to_target: Dict[str, str] = {}
                for rel in rels_root.xpath("//pr:Relationship | //rel:Relationship", namespaces=NS):
                    r_id = rel.get("Id")
                    target = rel.get("Target")
                    if r_id and target:
                        rel_to_target[r_id] = target

                # Also inspect header/footer relationships
                for name in namelist:
                    if (name.startswith("word/_rels/header") or name.startswith("word/_rels/footer")) and name.endswith(".rels"):
                        h_rels = ET.fromstring(zf.read(name))
                        for rel in h_rels.xpath("//pr:Relationship | //rel:Relationship", namespaces=NS):
                            r_id = rel.get("Id")
                            target = rel.get("Target")
                            if r_id and target:
                                rel_to_target[r_id] = target

                doc_root = ET.fromstring(doc_xml)
                paras = doc_root.xpath("//w:p", namespaces=NS)

                # Track image index per distinct appearance
                img_appearance_idx = 0
                seen_rel_ids: Set[str] = set()

                for p_idx, p in enumerate(paras):
                    blips = p.xpath(".//a:blip", namespaces=NS)
                    for b in blips:
                        r_id = b.attrib.get(f"{{{NS['r']}}}embed")
                        if not r_id or r_id in seen_rel_ids:
                            continue
                        seen_rel_ids.add(r_id)

                        target = rel_to_target.get(r_id, "")
                        target_fname = os.path.basename(target)
                        media_key = f"word/{target}" if not target.startswith("word/") else target
                        if media_key not in media_files and target in media_files:
                            media_key = target

                        media_bytes = media_files.get(media_key)
                        if not media_bytes:
                            continue

                        img_appearance_idx += 1

                        # Get drawing extent dimensions
                        drawing = b.xpath("ancestor::w:drawing", namespaces=NS)
                        extent = drawing[0].xpath(".//wp:extent", namespaces=NS) if drawing else []
                        cx = int(extent[0].get("cx")) if extent and extent[0].get("cx") else 0
                        cy = int(extent[0].get("cy")) if extent and extent[0].get("cy") else 0
                        width_in = round(cx / 914400.0, 2) if cx else 0.0
                        height_in = round(cy / 914400.0, 2) if cy else 0.0

                        # Get pixel dimensions and format using PIL
                        pil_im = None
                        try:
                            pil_im = PILImage.open(io.BytesIO(media_bytes))
                            px_w, px_h = pil_im.size
                            img_format = pil_im.format or os.path.splitext(target_fname)[1].lstrip(".").upper()
                        except Exception:
                            px_w, px_h = (0, 0)
                            img_format = os.path.splitext(target_fname)[1].lstrip(".").upper()

                        aspect_ratio = round(px_w / max(1, px_h), 2) if px_w and px_h else 1.0

                        # Opacity and alpha-channel analysis (detect transparent border overlays)
                        opaque_pct = 100.0
                        if pil_im is not None:
                            try:
                                if pil_im.mode in ("RGBA", "LA") or (pil_im.mode == "P" and "transparency" in pil_im.info):
                                    alpha_arr = np.array(pil_im.convert("RGBA"))[:, :, 3]
                                    opaque_pct = float((alpha_arr > 20).mean() * 100)
                            except Exception:
                                opaque_pct = 100.0

                        # Surrounding text and nearest section heading
                        surr_paras = paras[max(0, p_idx - 2):min(len(paras), p_idx + 3)]
                        surr_text = " ".join(
                            "".join(sp.xpath(".//w:t/text()", namespaces=NS)).strip()
                            for sp in surr_paras if "".join(sp.xpath(".//w:t/text()", namespaces=NS)).strip()
                        )

                        heading = ""
                        for prev_p in reversed(paras[max(0, p_idx - 10):p_idx + 1]):
                            p_style = prev_p.find(".//w:pStyle", namespaces=NS)
                            st_val = p_style.get(f"{{{NS['w']}}}val") if p_style is not None else ""
                            t_val = "".join(prev_p.xpath(".//w:t/text()", namespaces=NS)).strip()
                            if "heading" in st_val.lower() or (t_val.isupper() and 3 < len(t_val) < 60):
                                heading = t_val
                                break

                        # Structural and contextual indicators
                        area_sq_in = width_in * height_in
                        is_cover_zone = (p_idx <= 12)
                        is_tiny_icon = (px_w > 0 and px_h > 0 and px_w <= 48 and px_h <= 48)
                        is_transparent_frame = (opaque_pct < 15.0)
                        is_extreme_aspect = (aspect_ratio > 7.0 or aspect_ratio < 0.15)
                        is_header_banner = (height_in <= 1.2 and width_in >= 5.0) or (aspect_ratio > 4.5 and height_in <= 1.5)
                        is_corner_or_inline_logo = (
                            (px_h <= 120 and px_w <= 400 and area_sq_in <= 4.0)
                            or (px_h <= 150 and px_w <= 400 and (aspect_ratio >= 2.0 or aspect_ratio <= 0.8))
                            or (area_sq_in <= 4.5 and width_in <= 4.0 and height_in <= 2.5 and (p_idx <= 15 or any(k in surr_text.lower() for k in ("college", "svce", "institute", "university", "department", "education"))))
                        )
                        is_full_slide_or_page = (cx >= 15000000) or (px_w >= 1800 and px_h >= 1000 and aspect_ratio > 1.3) or (cx >= 10000000 and cy >= 8000000)

                        # Classification
                        if is_tiny_icon:
                            classification = "fixed_asset"
                            action = "fixed"
                            reason = "Small bullet icon / template indicator (strictly preserved)"
                        elif is_transparent_frame:
                            classification = "fixed_asset"
                            action = "fixed"
                            reason = "Transparent layout frame / border overlay (strictly preserved)"
                        elif is_extreme_aspect or is_header_banner:
                            classification = "fixed_asset"
                            action = "fixed"
                            reason = "Decorative header/footer border or separator bar (strictly preserved)"
                        elif is_corner_or_inline_logo:
                            classification = "college_logo"
                            action = "fixed"
                            reason = "Institutional college emblem / official logo (strictly preserved)"
                        elif any(k in surr_text.lower() for k in ("department of", "guided by", "submitted by", "roll no")) and (px_w <= 350 and px_h <= 350):
                            classification = "college_logo"
                            action = "fixed"
                            reason = "Institutional emblem adjacent to student/college credentials (strictly preserved)"
                        elif is_cover_zone and not is_full_slide_or_page and (px_w <= 400 and px_h <= 400):
                            classification = "college_logo"
                            action = "fixed"
                            reason = "Institutional college emblem on cover slide (strictly preserved)"
                        elif is_full_slide_or_page and opaque_pct >= 60.0:
                            classification = "full_slide_screenshot"
                            action = "replace"
                            reason = "Full-slide visual containing topical theme (regenerated for new topic)"
                        else:
                            classification = "topic_specific"
                            action = "replace"
                            heading_label = f" for '{heading}'" if heading else ""
                            reason = f"Topic-specific section illustration{heading_label} (regenerated for new project topic)"

                        analyzed_images.append({
                            "id": f"img_{img_appearance_idx}",
                            "arm_image_field": f"image_{img_appearance_idx}",
                            "filename": target_fname,
                            "media_path": media_key,
                            "rel_id": r_id,
                            "format": img_format,
                            "pixel_width": px_w,
                            "pixel_height": px_h,
                            "aspect_ratio": aspect_ratio,
                            "opaque_pct": round(opaque_pct, 1),
                            "cx": cx,
                            "cy": cy,
                            "width_in": width_in,
                            "height_in": height_in,
                            "paragraph_idx": p_idx,
                            "heading": heading,
                            "surrounding_text": surr_text[:160],
                            "classification": classification,
                            "action": action,
                            "is_replaceable": (action == "replace"),
                            "reason": reason,
                        })

        except Exception as e:
            logger.error(f"Error analyzing images in template '{template_path}': {e}")

        return analyzed_images

    @classmethod
    def generate_replacement_images(
        cls,
        project_title: str,
        problem_statement: str,
        analyzed_images: List[Dict[str, Any]],
        output_dir: str,
        report_id: str = "report",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Synthesizes replacement images strictly via Gemini Image Generation.
        STEP 1: All fallbacks (matplotlib, charts, diagrams, cached images) are disabled.
        If Gemini succeeds -> use generated image.
        If Gemini fails -> DO NOT insert any image, log failure.
        """
        os.makedirs(output_dir, exist_ok=True)
        replacements: Dict[str, Dict[str, Any]] = {}
        clean_title = str(project_title).strip()
        clean_prob = str(problem_statement).strip()

        from apps.api.services.gemini_visual_pipeline_service import gemini_visual_pipeline_service

        used_hashes: Set[str] = set()

        for img_idx, img in enumerate(analyzed_images, start=1):
            if img.get("action") != "replace":
                continue

            fname = img.get("filename") or f"{img.get('arm_image_field', f'image_{img_idx}')}.png"
            ar = img.get("aspect_ratio", 1.0)
            target_fmt = "PNG"

            slide_idx = img.get("slide_num") or img.get("slide_index") or img.get("page_number") or img_idx
            cls_type = img.get("classification")
            heading_raw = img.get("new_heading") or img.get("heading") or f"System Visual {img_idx}"
            heading = " ".join(str(x) for x in heading_raw) if isinstance(heading_raw, (list, tuple, set)) else str(heading_raw or f"System Visual {img_idx}").strip()
            subheading = str(img.get("subheading") or "").strip()

            surr_text = img.get("surrounding_text") or ""
            slide_matter_raw = img.get("slide_matter") or surr_text or clean_prob
            slide_matter = " ".join(str(x) for x in slide_matter_raw) if isinstance(slide_matter_raw, (list, tuple, set)) else str(slide_matter_raw or "").strip()

            arm_field = img.get("arm_image_field") or f"image_{img_idx}"
            slot_id = f"slot_{img_idx}_{arm_field}"

            # Central ARM Visual Engine Decision & Generation Boundary
            from apps.api.services.visual_engine import visual_engine

            domain, domain_label, conf = gemini_visual_pipeline_service.detect_project_domain_and_context(
                project_title=clean_title,
                project_description=clean_prob,
            )

            target_w = 1600
            target_h = max(600, min(1600, int(round(target_w / max(0.4, ar)))))
            vis_out_path = os.path.join(output_dir, f"{report_id}_slide_{slide_idx}_{fname}")

            vis_res = visual_engine.generate_visual(
                project_title=clean_title,
                project_description=clean_prob,
                detected_domain=domain,
                domain_confidence=conf,
                slide_number=slide_idx or 1,
                slide_heading=heading,
                slide_matter=slide_matter,
                report_id=report_id,
                target_width=target_w,
                target_height=target_h,
                output_path=vis_out_path,
                slot_id=slot_id,
            )

            # Check if visual was genuinely generated
            if vis_res.success and vis_res.asset_path and os.path.exists(vis_res.asset_path):
                with open(vis_res.asset_path, "rb") as f_sha:
                    img_sha = hashlib.sha256(f_sha.read()).hexdigest()

                # Deduplication check: If hash collision with an earlier slot, generate distinct alternative
                if img_sha in used_hashes:
                    logger.warning(
                        f"[ARM VISUAL ENGINE] Image collision detected for slot {slot_id} ('{heading}'). Regenerating distinct visual..."
                    )
                    alt_heading = f"{heading} - Component Architecture {img_idx}"
                    alt_slot = f"{slot_id}_alt_{uuid.uuid4().hex[:6]}"
                    vis_res = visual_engine.generate_visual(
                        project_title=clean_title,
                        project_description=clean_prob,
                        detected_domain=domain,
                        domain_confidence=conf,
                        slide_number=slide_idx or 1,
                        slide_heading=alt_heading,
                        slide_matter=f"{slide_matter} Subsystem {img_idx} operational topology",
                        report_id=report_id,
                        target_width=target_w,
                        target_height=target_h,
                        output_path=vis_out_path,
                        slot_id=alt_slot,
                    )
                    if vis_res.success and vis_res.asset_path and os.path.exists(vis_res.asset_path):
                        with open(vis_res.asset_path, "rb") as f_sha_alt:
                            img_sha = hashlib.sha256(f_sha_alt.read()).hexdigest()

                used_hashes.add(img_sha)

                item_info = {
                    "file_path": vis_res.asset_path,
                    "arm_image_field": arm_field,
                    "rel_id": img.get("rel_id"),
                    "filename": fname,
                    "classification": cls_type,
                    "visual_type": vis_res.visual_type,
                    "decision_reason": f"{vis_res.visual_type} -> {vis_res.source} ({vis_res.reason})",
                    "sha256": img_sha,
                }
                replacements[fname] = item_info
                replacements[os.path.basename(fname)] = item_info
                replacements[arm_field] = item_info
                replacements[f"image_{img_idx}"] = item_info
                if img.get("rel_id"):
                    replacements[img["rel_id"]] = item_info
                replacements[slot_id] = item_info
            else:
                logger.warning(
                    f"[ARM VISUAL ENGINE] Visual synthesis failed or not returned for slide {slide_idx} "
                    f"('{heading}'). Reason: {vis_res.error or 'Visual generation unavailable'}."
                )

        return replacements

    @classmethod
    def _render_cover_visual(
        cls,
        project_title: str,
        problem_statement: str,
        out_path: str,
        aspect_ratio: float,
        target_fmt: str,
    ) -> None:
        """
        Renders a modern, high-tech AI perception cover visual with facial
        recognition viewport, neural mesh keypoints, and telemetry statistics.
        """
        fig_w = 12.0
        fig_h = max(6.0, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 12)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Deep Slate Tech Backdrop
        fig.patch.set_facecolor("#0b1329")
        ax.set_facecolor("#0b1329")

        # Subtle Technical Background Grid
        for gx in range(0, 13):
            ax.axvline(gx, color="#1e293b", linewidth=0.5, alpha=0.5)
        for gy in range(0, int(fig_h) + 1):
            ax.axhline(gy, color="#1e293b", linewidth=0.5, alpha=0.5)

        # Header Badge
        ax.text(
            6.0, fig_h - 0.7,
            "AUTONOMOUS VISION ARCHITECTURE • REAL-TIME PERCEPTION PIPELINE",
            ha="center", va="center",
            fontsize=8.5, fontweight="bold", fontfamily="sans-serif",
            color="#38bdf8",
        )

        # Main Title Banner
        disp_title = project_title.upper()
        if len(disp_title) > 50:
            disp_title = disp_title[:47] + "..."
        ax.text(
            6.0, fig_h - 1.3,
            disp_title,
            ha="center", va="center",
            fontsize=13, fontweight="bold", fontfamily="sans-serif",
            color="#ffffff",
        )

        # Central Facial Recognition Camera Viewport Simulation
        center_y = fig_h * 0.48
        vp_w, vp_h = 4.2, 3.2
        vp_rect = patches.FancyBboxPatch(
            (6.0 - vp_w / 2, center_y - vp_h / 2), vp_w, vp_h,
            boxstyle="round,pad=0.15",
            linewidth=1.8,
            edgecolor="#38bdf8",
            facecolor="#0f172a",
        )
        ax.add_patch(vp_rect)

        # Camera Viewport Corner Target Marks
        c_x1, c_x2 = 6.0 - vp_w / 2 + 0.3, 6.0 + vp_w / 2 - 0.3
        c_y1, c_y2 = center_y - vp_h / 2 + 0.3, center_y + vp_h / 2 - 0.3
        ax.plot([c_x1, c_x1 + 0.4], [c_y1, c_y1], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x1, c_x1], [c_y1, c_y1 + 0.4], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x2, c_x2 - 0.4], [c_y1, c_y1], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x2, c_x2], [c_y1, c_y1 + 0.4], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x1, c_x1 + 0.4], [c_y2, c_y2], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x1, c_x1], [c_y2, c_y2 - 0.4], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x2, c_x2 - 0.4], [c_y2, c_y2], color="#38bdf8", linewidth=2.5)
        ax.plot([c_x2, c_x2], [c_y2, c_y2 - 0.4], color="#38bdf8", linewidth=2.5)

        # Simulated Face Landmark Keypoint Coordinates
        keypoints = [
            (5.5, center_y + 0.4), (6.5, center_y + 0.4),  # Eyes
            (6.0, center_y + 0.0),                          # Nose
            (5.6, center_y - 0.5), (6.4, center_y - 0.5),  # Mouth edges
            (6.0, center_y - 0.6),                          # Lower lip
            (6.0, center_y + 0.9),                          # Forehead
            (5.1, center_y - 0.1), (6.9, center_y - 0.1),  # Cheeks
            (6.0, center_y - 1.1),                          # Chin
        ]
        for kx, ky in keypoints:
            ax.plot(kx, ky, "o", color="#34d399", markersize=6)
        # Landmark mesh lines
        mesh_lines = [
            ((5.5, center_y + 0.4), (6.0, center_y + 0.0)),
            ((6.5, center_y + 0.4), (6.0, center_y + 0.0)),
            ((6.0, center_y + 0.0), (6.0, center_y - 0.5)),
            ((5.6, center_y - 0.5), (6.4, center_y - 0.5)),
            ((6.0, center_y + 0.9), (5.5, center_y + 0.4)),
            ((6.0, center_y + 0.9), (6.5, center_y + 0.4)),
            ((5.6, center_y - 0.5), (6.0, center_y - 1.1)),
            ((6.4, center_y - 0.5), (6.0, center_y - 1.1)),
        ]
        for p1, p2 in mesh_lines:
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#38bdf8", linewidth=1.0, alpha=0.7)

        # Bounding box label
        ax.text(
            6.0, center_y + vp_h / 2 + 0.25,
            "[ STUDENT ID: #2026-AI-VERIFIED • CONFIDENCE: 99.4% ]",
            ha="center", va="center",
            fontsize=7.5, fontweight="bold", fontfamily="sans-serif",
            color="#34d399",
        )

        # Bottom Telemetry Badges
        metrics = [
            ("FRAME INGESTION", "1080p @ 30 FPS", 2.2),
            ("INFERENCE LATENCY", "14.2 ms / frame", 6.0),
            ("ROSTER SYNC", "Automated DB Commit", 9.8),
        ]
        for m_title, m_val, mx in metrics:
            m_box = patches.FancyBboxPatch(
                (mx - 1.6, 0.4), 3.2, 0.7,
                boxstyle="round,pad=0.08",
                linewidth=1.0,
                edgecolor="#334155",
                facecolor="#1e293b",
            )
            ax.add_patch(m_box)
            ax.text(
                mx, 0.85,
                m_title,
                ha="center", va="center",
                fontsize=6.5, fontweight="bold", fontfamily="sans-serif",
                color="#94a3b8",
            )
            ax.text(
                mx, 0.55,
                m_val,
                ha="center", va="center",
                fontsize=7.5, fontweight="bold", fontfamily="sans-serif",
                color="#38bdf8",
            )

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_vertical_panel(
        cls,
        project_title: str,
        panel_num: int,
        out_path: str,
        target_fmt: str,
    ) -> None:
        """
        Renders a tall vertical multi-tier operational pipeline matching 2:3 ratio (832x1248).
        """
        fig, ax = plt.subplots(figsize=(6.0, 9.0), dpi=200)
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 9)
        ax.axis("off")

        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        # Top Badge
        ax.text(
            3.0, 8.5,
            f"AI ATTENDANCE PIPELINE • STAGE 0{panel_num}",
            ha="center", va="center",
            fontsize=8.0, fontweight="bold", fontfamily="sans-serif",
            color="#38bdf8",
        )

        steps = [
            ("1. VIDEO INGESTION", "Edge Camera RTSP Stream\n1080p Resolution", "#1e293b", "#38bdf8"),
            ("2. FACE DETECTION", "RetinaFace Boundary Box\nLandmark Localization", "#1e293b", "#818cf8"),
            ("3. FEATURE EXTRACTION", "512-D Normalized Embeddings\nMobileFaceNet Model", "#1e293b", "#a78bfa"),
            ("4. VECTOR MATCHING", "Cosine Distance Calculation\nThreshold: 0.82 Confidence", "#1e293b", "#34d399"),
            ("5. ROSTER PERSISTENCE", "Automated DB Commit\nParent SMS Notification", "#1e293b", "#fbbf24"),
        ]

        y_curr = 7.3
        for title, desc, bg_c, border_c in steps:
            box = patches.FancyBboxPatch(
                (0.6, y_curr - 0.9), 4.8, 0.95,
                boxstyle="round,pad=0.1",
                linewidth=1.2,
                edgecolor=border_c,
                facecolor=bg_c,
            )
            ax.add_patch(box)
            ax.text(
                3.0, y_curr - 0.25,
                title,
                ha="center", va="center",
                fontsize=7.5, fontweight="bold", fontfamily="sans-serif",
                color="#ffffff",
            )
            ax.text(
                3.0, y_curr - 0.65,
                desc,
                ha="center", va="center",
                fontsize=6.8, fontfamily="sans-serif",
                color="#cbd5e1",
            )
            # Arrow
            if y_curr > 3.0:
                ax.annotate(
                    "",
                    xy=(3.0, y_curr - 1.25), xytext=(3.0, y_curr - 0.95),
                    arrowprops=dict(facecolor="#38bdf8", edgecolor="#38bdf8", width=1.5, headwidth=5, shrink=0.05),
                )
            y_curr -= 1.35

        # Footer
        ax.text(
            3.0, 0.45,
            "REAL-TIME VERIFICATION ENGINE • 99.4% ACCURACY",
            ha="center", va="center",
            fontsize=6.5, fontweight="semibold", fontfamily="sans-serif",
            color="#64748b",
        )

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_wide_feature_card(
        cls,
        project_title: str,
        card_title: str,
        card_subtitle: str,
        bg_color: str,
        accent_color: str,
        out_path: str,
        target_fmt: str,
    ) -> None:
        """
        Renders a wide 2:1 ratio (1344x675) technical feature card.
        """
        fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=200)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 4)
        ax.axis("off")

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        # Subtle card border
        card_rect = patches.FancyBboxPatch(
            (0.2, 0.2), 7.6, 3.6,
            boxstyle="round,pad=0.15",
            linewidth=1.5,
            edgecolor=accent_color,
            facecolor="none",
        )
        ax.add_patch(card_rect)

        # Top Category Tag
        ax.text(
            0.6, 3.3,
            "AI ATTENDANCE SYSTEM ARCHITECTURE",
            ha="left", va="center",
            fontsize=7.0, fontweight="bold", fontfamily="sans-serif",
            color=accent_color,
        )

        # Main Card Title
        ax.text(
            0.6, 2.7,
            card_title,
            ha="left", va="center",
            fontsize=11.0, fontweight="bold", fontfamily="sans-serif",
            color="#ffffff",
        )

        # Subtitle description
        ax.text(
            0.6, 2.0,
            card_subtitle,
            ha="left", va="center",
            fontsize=7.5, fontfamily="sans-serif",
            color="#cbd5e1",
        )

        # Visual Diagram Elements on Right Side
        # Mini schematic box
        sc_box = patches.FancyBboxPatch(
            (5.4, 0.8), 2.1, 2.4,
            boxstyle="round,pad=0.08",
            linewidth=1.2,
            edgecolor=accent_color,
            facecolor="#0f172a",
        )
        ax.add_patch(sc_box)
        ax.text(
            6.45, 2.7,
            "MODULE METRICS",
            ha="center", va="center",
            fontsize=6.5, fontweight="bold", fontfamily="sans-serif",
            color=accent_color,
        )
        ax.text(
            6.45, 2.1,
            "STATUS: ACTIVE\nLATENCY: 14ms\nCONF: 99.2%",
            ha="center", va="center",
            fontsize=6.8, fontfamily="monospace",
            color="#ffffff",
        )
        ax.plot([5.8, 7.1], [1.3, 1.3], color=accent_color, linewidth=2.0)
        ax.text(
            6.45, 1.0,
            "VERIFIED READY",
            ha="center", va="center",
            fontsize=6.0, fontweight="bold", fontfamily="sans-serif",
            color="#34d399",
        )

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_technical_diagram(
        cls,
        project_title: str,
        heading: str,
        aspect_ratio: float,
        out_path: str,
        target_fmt: str,
    ) -> None:
        """
        Renders a publication-grade technical evaluation diagram (3:2 or 4:3).
        """
        fig_w = 8.0
        fig_h = max(4.5, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        # Heading
        ax.text(
            4.0, fig_h - 0.5,
            f"PERFORMANCE EVALUATION: {project_title.upper()[:40]}",
            ha="center", va="center",
            fontsize=10.0, fontweight="bold", fontfamily="sans-serif",
            color="#0f172a",
        )

        # Comparison Bar Chart: Manual vs AI Attendance
        categories = ["Time Required", "Error Rate", "Proxy Vulnerability", "Audit Latency"]
        manual_vals = [90, 85, 95, 80]
        ai_vals = [5, 4, 2, 8]

        bar_y = [fig_h * 0.70, fig_h * 0.52, fig_h * 0.34, fig_h * 0.16]
        for idx, (cat, m_val, a_val) in enumerate(zip(categories, manual_vals, ai_vals)):
            y = bar_y[idx]
            ax.text(0.5, y + 0.15, cat, ha="left", va="center", fontsize=7.5, fontweight="bold", color="#334155")
            # Manual bar (red)
            ax.barh(y - 0.08, m_val * 0.035, left=2.5, height=0.18, color="#ef4444", label="Manual Roll Call" if idx == 0 else "")
            # AI bar (green)
            ax.barh(y - 0.30, a_val * 0.035, left=2.5, height=0.18, color="#10b981", label="AI Attendance System" if idx == 0 else "")
            ax.text(2.6 + m_val * 0.035, y - 0.08, f"Manual: {m_val}%", va="center", fontsize=6.5, color="#b91c1c")
            ax.text(2.6 + a_val * 0.035, y - 0.30, f"AI: {a_val}%", va="center", fontsize=6.5, color="#047857")

        ax.legend(loc="upper right", fontsize=7.0, framealpha=0.9)

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_irrigation_infographic(
        cls,
        project_title: str,
        out_path: str,
        target_fmt: str,
        aspect_ratio: float = 1.76,
    ) -> None:
        """
        Renders a publication-grade smart irrigation infographic (16:9 or wide format)
        with 4 core technical pillars and agronomic telemetry.
        """
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#064e3b")
        ax.set_facecolor("#064e3b")

        disp_title = f"{project_title.upper()}: AUTOMATED WATER CONSERVATION"
        if len(disp_title) > 55:
            disp_title = f"{project_title.upper()[:52]}..."
        ax.text(
            5.0, fig_h - 0.55,
            disp_title,
            ha="center", va="center",
            fontsize=11.5, fontweight="bold", fontfamily="sans-serif",
            color="#34d399",
        )
        ax.text(
            5.0, fig_h - 1.0,
            "Empowering farmers & optimizing agricultural water use through IoT sensors and predictive AI.",
            ha="center", va="center",
            fontsize=8.0, fontfamily="sans-serif",
            color="#ecfdf5",
        )

        card_h = max(1.8, (fig_h - 1.8) / 2.0)
        cards = [
            ("1", "SOIL MOISTURE SENSORS", "Capacitive in-situ probes measure\nroot-zone volumetric water content\nwith continuous LoRaWAN sync.", "#047857", "#10b981", 0.5, fig_h - 1.3 - card_h),
            ("2", "PREDICTIVE WEATHER AI", "Machine learning algorithms forecast\nevapotranspiration & rainfall to prevent\nredundant watering cycles.", "#0369a1", "#38bdf8", 5.1, fig_h - 1.3 - card_h),
            ("3", "AUTOMATED DRIP VALVES", "Autonomous solenoid valves deliver\nprecise drop-by-drop root hydration,\neliminating 40% surface runoff.", "#b45309", "#fbbf24", 0.5, 0.4),
            ("4", "CLOUD FARM DASHBOARD", "Real-time crop hydration analytics,\nsoil health telemetry, and automated\nmobile alerts for farm management.", "#4338ca", "#818cf8", 5.1, 0.4),
        ]

        for num, title, desc, bg_c, acc_c, cx, cy in cards:
            rect = patches.FancyBboxPatch(
                (cx, cy), 4.4, card_h - 0.15,
                boxstyle="round,pad=0.1",
                linewidth=1.4,
                edgecolor=acc_c,
                facecolor="#0f172a",
            )
            ax.add_patch(rect)
            circ = patches.Circle((cx + 0.35, cy + card_h - 0.45), 0.20, facecolor=acc_c, edgecolor="#ffffff", linewidth=1.0)
            ax.add_patch(circ)
            ax.text(cx + 0.35, cy + card_h - 0.45, num, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0f172a")
            ax.text(cx + 0.75, cy + card_h - 0.45, title, ha="left", va="center", fontsize=8.0, fontweight="bold", color="#ffffff")
            ax.text(cx + 0.35, cy + (card_h - 0.15) * 0.4, desc, ha="left", va="center", fontsize=7.0, color="#cbd5e1", linespacing=1.3)

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_irrigation_field_collage(
        cls,
        project_title: str,
        out_path: str,
        target_fmt: str,
        aspect_ratio: float = 0.78,
    ) -> None:
        """
        Renders a vertical 4-panel field deployment graphic with trial benchmarks
        for smart agricultural systems.
        """
        fig_w = 6.0
        fig_h = max(7.0, round(fig_w / max(0.4, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 6)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        ax.text(
            3.0, fig_h - 0.45,
            "SMART IRRIGATION FIELD DEPLOYMENT",
            ha="center", va="center",
            fontsize=10.0, fontweight="bold", fontfamily="sans-serif",
            color="#34d399",
        )
        ax.text(
            3.0, fig_h - 0.85,
            "IoT Telemetry Nodes, Precision Drip Manifolds & Soil Sensing",
            ha="center", va="center",
            fontsize=7.2, fontfamily="sans-serif",
            color="#94a3b8",
        )

        panels = [
            ("FIELD SENSOR NODE", "Solar-powered LoRa telemetry\nprobe at 30cm depth measuring\nelectrical conductivity & moisture", "#064e3b", "#10b981", 0.3, fig_h - 3.2, 2.55, 2.1),
            ("AUTOMATED DRIP VALVES", "Low-power solenoid manifold\nregulating zoned water pressure\nwith zero surface runoff", "#075985", "#38bdf8", 3.15, fig_h - 3.2, 2.55, 2.1),
            ("MOBILE MONITORING", "Agronomist tablet interface\ntracking soil moisture deficit\nand automated valve schedules", "#78350f", "#fbbf24", 0.3, fig_h - 5.5, 2.55, 2.1),
            ("AI DECISION PIPELINE", "Sensor Data -> Weather Sync ->\nML Soil Water Deficit Model ->\nTargeted Irrigation Dispatch", "#312e81", "#818cf8", 3.15, fig_h - 5.5, 2.55, 2.1),
        ]

        for title, desc, bg_c, acc_c, px, py, pw, ph in panels:
            box = patches.FancyBboxPatch(
                (px, py), pw, ph,
                boxstyle="round,pad=0.08",
                linewidth=1.2,
                edgecolor=acc_c,
                facecolor=bg_c,
            )
            ax.add_patch(box)
            ax.text(px + pw / 2, py + ph - 0.32, title, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#ffffff")
            ax.text(px + pw / 2, py + ph / 2 - 0.2, desc, ha="center", va="center", fontsize=6.6, color="#e2e8f0", linespacing=1.3)

        tag_box = patches.FancyBboxPatch(
            (0.3, 0.4), 5.4, 1.45,
            boxstyle="round,pad=0.08",
            linewidth=1.0,
            edgecolor="#334155",
            facecolor="#1e293b",
        )
        ax.add_patch(tag_box)
        ax.text(3.0, 1.5, "FIELD TRIAL VERIFICATION BENCHMARK", ha="center", va="center", fontsize=7.8, fontweight="bold", color="#38bdf8")
        metrics = [
            ("WATER CONSERVED", "41.8%", 1.2),
            ("SOIL MOISTURE", "68% (OPTIMAL)", 3.0),
            ("CROP YIELD GAIN", "+18.4%", 4.8),
        ]
        for m_label, m_val, mx in metrics:
            ax.text(mx, 1.05, m_label, ha="center", va="center", fontsize=6.2, color="#94a3b8")
            ax.text(mx, 0.72, m_val, ha="center", va="center", fontsize=8.2, fontweight="bold", color="#34d399")

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_irrigation_architecture(
        cls,
        project_title: str,
        out_path: str,
        target_fmt: str,
        aspect_ratio: float = 1.33,
    ) -> None:
        """
        Renders a multi-tier smart irrigation system architecture diagram.
        """
        fig_w = 8.0
        fig_h = max(5.0, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        ax.text(
            4.0, fig_h - 0.5,
            f"SYSTEM ARCHITECTURE: {project_title.upper()[:40]}",
            ha="center", va="center",
            fontsize=10.0, fontweight="bold", fontfamily="sans-serif",
            color="#064e3b",
        )

        layers = [
            ("PERCEPTION & FIELD SENSORS", "Capacitive Soil Moisture Probes, Ambient Temperature, Humidity Sensors", "#064e3b", "#34d399"),
            ("EDGE TELEMETRY & GATEWAY", "Solar Inverter Controller, ESP32 Gateway Node, LoRaWAN Long-Range Sync", "#075985", "#38bdf8"),
            ("AI DECISION & CLOUD ANALYTICS", "Evapotranspiration Predictor (Penman-Monteith), Deficit Estimator, Scheduling Engine", "#312e81", "#818cf8"),
            ("AUTOMATED ACTUATION & DRIP VALVES", "Autonomous Solenoid Manifolds, Sub-surface Drip Tubing, Mobile Farmer Alerts", "#78350f", "#fbbf24"),
        ]

        y_step = (fig_h - 1.4) / 4.0
        for idx, (ltitle, ldesc, bg_c, acc_c) in enumerate(layers):
            y_pos = fig_h - 1.1 - (idx * y_step)
            box = patches.FancyBboxPatch(
                (0.6, y_pos - y_step + 0.15), 6.8, y_step - 0.22,
                boxstyle="round,pad=0.08",
                linewidth=1.2,
                edgecolor=acc_c,
                facecolor=bg_c,
            )
            ax.add_patch(box)
            ax.text(1.0, y_pos - 0.22, ltitle, ha="left", va="center", fontsize=7.8, fontweight="bold", color="#ffffff")
            ax.text(1.0, y_pos - y_step * 0.55, ldesc, ha="left", va="center", fontsize=6.8, color="#e2e8f0")

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_generic_topic_infographic(
        cls,
        project_title: str,
        heading: str,
        out_path: str,
        target_fmt: str,
        aspect_ratio: float = 1.76,
    ) -> None:
        """
        Renders a wide modern technical overview card for any engineering topic.
        """
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0b1329")
        ax.set_facecolor("#0b1329")

        disp_title = f"{project_title.upper()}: SYSTEM OVERVIEW"
        if len(disp_title) > 55:
            disp_title = f"{project_title.upper()[:52]}..."
        ax.text(
            5.0, fig_h - 0.55,
            disp_title,
            ha="center", va="center",
            fontsize=11.0, fontweight="bold", fontfamily="sans-serif",
            color="#38bdf8",
        )
        ax.text(
            5.0, fig_h - 0.95,
            f"Technical Architecture & Functional Subsystems for {heading.title() or 'Core Pipeline'}",
            ha="center", va="center",
            fontsize=7.8, fontfamily="sans-serif",
            color="#94a3b8",
        )

        card_h = max(1.8, (fig_h - 1.8) / 2.0)
        cards = [
            ("1", "DATA INGESTION & SENSING", "Continuous multi-modal telemetry\ningestion and input stream normalization.", "#0369a1", "#38bdf8", 0.5, fig_h - 1.3 - card_h),
            ("2", "AI / ML PROCESSING PIPELINE", "Feature vector extraction, model\ninference, and probabilistic scoring.", "#4338ca", "#818cf8", 5.1, fig_h - 1.3 - card_h),
            ("3", "DECISION & ACTUATION CORE", "Real-time decision rules, feedback\nloops, and automated control triggers.", "#047857", "#34d399", 0.5, 0.4),
            ("4", "TELEMETRY & USER INTERFACE", "Interactive analytics dashboard, audit\nlogging, and transactional cloud sync.", "#b45309", "#fbbf24", 5.1, 0.4),
        ]

        for num, title, desc, bg_c, acc_c, cx, cy in cards:
            rect = patches.FancyBboxPatch(
                (cx, cy), 4.4, card_h - 0.15,
                boxstyle="round,pad=0.1",
                linewidth=1.4,
                edgecolor=acc_c,
                facecolor="#0f172a",
            )
            ax.add_patch(rect)
            circ = patches.Circle((cx + 0.35, cy + card_h - 0.45), 0.20, facecolor=acc_c, edgecolor="#ffffff", linewidth=1.0)
            ax.add_patch(circ)
            ax.text(cx + 0.35, cy + card_h - 0.45, num, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0f172a")
            ax.text(cx + 0.75, cy + card_h - 0.45, title, ha="left", va="center", fontsize=8.0, fontweight="bold", color="#ffffff")
            ax.text(cx + 0.35, cy + (card_h - 0.15) * 0.4, desc, ha="left", va="center", fontsize=7.0, color="#cbd5e1", linespacing=1.3)

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_generic_topic_pipeline(
        cls,
        project_title: str,
        heading: str,
        panel_num: int,
        out_path: str,
        target_fmt: str,
        aspect_ratio: float = 0.78,
    ) -> None:
        """
        Renders a vertical 5-stage pipeline for any engineering topic.
        """
        fig_w = 6.0
        fig_h = max(7.0, round(fig_w / max(0.4, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 6)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        ax.text(
            3.0, fig_h - 0.5,
            f"{project_title.upper()[:36]} • PIPELINE",
            ha="center", va="center",
            fontsize=8.5, fontweight="bold", fontfamily="sans-serif",
            color="#38bdf8",
        )

        steps = [
            ("1. INPUT DATA STREAM", "Raw signal ingestion, parsing\nand schema verification", "#1e293b", "#38bdf8"),
            ("2. PREPROCESSING & CLEANING", "Noise filtration, normalization\nand feature transformation", "#1e293b", "#818cf8"),
            ("3. MODEL INFERENCE ENGINE", "Pre-trained deep neural network\nand feature vector alignment", "#1e293b", "#a78bfa"),
            ("4. DECISION VALIDATION", "Confidence threshold evaluation\nand safety boundary checks", "#1e293b", "#34d399"),
            ("5. OUTPUT PERSISTENCE", "Automated database logging\nand event notification delivery", "#1e293b", "#fbbf24"),
        ]

        y_step = (fig_h - 1.8) / 5.0
        for idx, (stitle, sdesc, bg_c, border_c) in enumerate(steps):
            y_curr = fig_h - 1.2 - (idx * y_step)
            box = patches.FancyBboxPatch(
                (0.6, y_curr - y_step + 0.15), 4.8, y_step - 0.22,
                boxstyle="round,pad=0.1",
                linewidth=1.2,
                edgecolor=border_c,
                facecolor=bg_c,
            )
            ax.add_patch(box)
            ax.text(3.0, y_curr - 0.25, stitle, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#ffffff")
            ax.text(3.0, y_curr - y_step * 0.55, sdesc, ha="center", va="center", fontsize=6.5, color="#cbd5e1")
            if idx < 4:
                ax.annotate(
                    "",
                    xy=(3.0, y_curr - y_step + 0.05), xytext=(3.0, y_curr - y_step + 0.25),
                    arrowprops=dict(facecolor="#38bdf8", edgecolor="#38bdf8", width=1.2, headwidth=4.5, shrink=0.05),
                )

        ax.text(
            3.0, 0.35,
            "REAL-TIME EXECUTION ENGINE • 99.2% OPERATIONAL RELIABILITY",
            ha="center", va="center",
            fontsize=6.2, fontweight="semibold", fontfamily="sans-serif",
            color="#64748b",
        )

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

    @classmethod
    def _render_generic_evaluation_diagram(
        cls,
        project_title: str,
        heading: str,
        aspect_ratio: float,
        out_path: str,
        target_fmt: str,
    ) -> None:
        """
        Renders a generic publication-grade performance evaluation diagram.
        """
        fig_w = 8.0
        fig_h = max(4.5, round(fig_w / max(0.5, aspect_ratio), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        ax.text(
            4.0, fig_h - 0.5,
            f"PERFORMANCE EVALUATION: {project_title.upper()[:40]}",
            ha="center", va="center",
            fontsize=10.0, fontweight="bold", fontfamily="sans-serif",
            color="#0f172a",
        )

        categories = ["Latency Overhead", "Error Frequency", "Manual Overhead", "System Bottleneck"]
        baseline_vals = [88, 82, 94, 78]
        proposed_vals = [12, 6, 8, 14]

        bar_y = [fig_h * 0.70, fig_h * 0.52, fig_h * 0.34, fig_h * 0.16]
        for idx, (cat, b_val, p_val) in enumerate(zip(categories, baseline_vals, proposed_vals)):
            y = bar_y[idx]
            ax.text(0.5, y + 0.15, cat, ha="left", va="center", fontsize=7.5, fontweight="bold", color="#334155")
            ax.barh(y - 0.08, b_val * 0.035, left=2.5, height=0.18, color="#ef4444", label="Legacy / Baseline" if idx == 0 else "")
            ax.barh(y - 0.30, p_val * 0.035, left=2.5, height=0.18, color="#10b981", label=f"Proposed System" if idx == 0 else "")
            ax.text(2.6 + b_val * 0.035, y - 0.08, f"Baseline: {b_val}%", va="center", fontsize=6.5, color="#b91c1c")
            ax.text(2.6 + p_val * 0.035, y - 0.30, f"Proposed: {p_val}%", va="center", fontsize=6.5, color="#047857")

        ax.legend(loc="upper right", fontsize=7.0, framealpha=0.9)

        plt.tight_layout()
        save_fmt = "PNG" if target_fmt == "PNG" else "JPEG"
        plt.savefig(out_path, format=save_fmt.lower(), dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)


intelligent_image_service = IntelligentImageService()
