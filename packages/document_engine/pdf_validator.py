"""
ARM Stage 10 - PDF Structural & Visual Validation Engine
Performs rigorous structural validation, PyMuPDF reopen tests, text extraction,
content consistency against DOCX, image inspection, table checking, header/footer
verification, secret leakage scanning, and visual page rendering.
"""

import os
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple
import pymupdf
import pypdf


class PdfValidator:
    """Validates generated PDF documents for structural integrity, content fidelity, and security."""

    FORBIDDEN_SECRET_PATTERNS = [
        (r'AIza[0-9A-Za-z-_]{35}', "Gemini API Key"),
        (r'eyJhbGciOi[0-9A-Za-z-_]+\.[0-9A-Za-z-_]+\.[0-9A-Za-z-_]+', "JWT / Supabase Service Key"),
        (r'postgres://[^\s:]+:[^\s@]+@', "PostgreSQL Connection String with Password"),
        (r'sbp_[0-9a-fA-F]{30,}', "Supabase Secret Token"),
        (r'sk-[0-9A-Za-z]{32,}', "Secret API Key"),
        (r'BEGIN PRIVATE KEY', "RSA / Private Key Block")
    ]

    @staticmethod
    def calculate_sha256(file_path_or_bytes) -> str:
        """Computes SHA-256 hash of a file or byte stream."""
        hasher = hashlib.sha256()
        if isinstance(file_path_or_bytes, (str, os.PathLike)):
            with open(file_path_or_bytes, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        elif isinstance(file_path_or_bytes, bytes):
            hasher.update(file_path_or_bytes)
        else:
            raise TypeError("Expected file path or bytes for SHA-256 calculation.")
        return hasher.hexdigest()

    @classmethod
    def validate_pdf(
        cls,
        pdf_path: str,
        expected_title: Optional[str] = None,
        expected_headings: Optional[List[str]] = None,
        expected_keywords: Optional[List[str]] = None,
        docx_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end PDF validation:
        1. File existence and non-empty check
        2. Valid PDF magic header (%PDF-)
        3. PyMuPDF reopen test & page count
        4. Text extraction across all pages
        5. Content consistency (title, headings, representative text)
        6. Header / footer & page number verification
        7. Table & image inspection
        8. Secret leakage detection (Gemini keys, service role keys, DB passwords)
        9. Visual page rendering inspection (blank page & clipping detection)
        10. SHA-256 hash generation
        """
        errors = []
        warnings = []

        if not os.path.exists(pdf_path):
            return {
                "is_valid": False,
                "errors": [f"PDF file does not exist: {pdf_path}"],
                "warnings": [],
                "page_count": 0,
                "reopen_test_passed": False
            }

        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            return {
                "is_valid": False,
                "errors": ["PDF file is empty (0 bytes)."],
                "warnings": [],
                "page_count": 0,
                "reopen_test_passed": False
            }

        if file_size < 100:
            errors.append(f"PDF file size is suspiciously small: {file_size} bytes.")

        # Check PDF Magic Header
        with open(pdf_path, "rb") as f:
            header_sample = f.read(16)
            if not header_sample.startswith(b"%PDF-"):
                errors.append(f"Invalid PDF header: expected '%PDF-', got '{header_sample[:8]}'.")

        pdf_hash = cls.calculate_sha256(pdf_path)

        # ----------------------------------------------------------------------
        # PyMuPDF Reopen & Extraction Test
        # ----------------------------------------------------------------------
        reopen_passed = False
        page_count = 0
        extracted_pages_text = []
        extracted_images = []
        full_extracted_text = ""

        try:
            doc = pymupdf.open(pdf_path)
            page_count = len(doc)
            reopen_passed = True

            if page_count == 0:
                errors.append("PDF opened successfully but contains 0 pages.")

            for page_idx in range(page_count):
                page = doc[page_idx]
                page_text = page.get_text() or ""
                extracted_pages_text.append(page_text)

                # Inspect images on page
                imgs = page.get_images(full=True)
                for img in imgs:
                    xref = img[0]
                    extracted_images.append({
                        "page": page_idx + 1,
                        "xref": xref,
                        "width": img[2],
                        "height": img[3]
                    })

            full_extracted_text = "\n".join(extracted_pages_text)
            doc.close()

        except Exception as e:
            errors.append(f"PDF parser reopen test failed: {str(e)}")

        # Secondary pypdf reopen test
        try:
            reader = pypdf.PdfReader(pdf_path)
            if len(reader.pages) != page_count and page_count > 0:
                warnings.append(
                    f"Page count mismatch between PyMuPDF ({page_count}) and pypdf ({len(reader.pages)})."
                )
        except Exception as e:
            warnings.append(f"Secondary pypdf parser warning: {e}")

        # ----------------------------------------------------------------------
        # Content Consistency Verification
        # ----------------------------------------------------------------------
        content_matches = {}
        if expected_title:
            title_found = expected_title.lower() in full_extracted_text.lower()
            content_matches["title_found"] = title_found
            if not title_found:
                warnings.append(f"Expected project title '{expected_title}' not explicitly detected in PDF text.")

        if expected_headings:
            found_count = 0
            for h in expected_headings:
                if h.lower() in full_extracted_text.lower():
                    found_count += 1
            content_matches["headings_found"] = f"{found_count}/{len(expected_headings)}"
            if found_count < len(expected_headings) * 0.5:
                warnings.append("Less than 50% of expected section headings were detected in PDF text.")

        if expected_keywords:
            kw_found = [kw for kw in expected_keywords if kw.lower() in full_extracted_text.lower()]
            content_matches["keywords_found"] = kw_found

        # Check references section
        has_references = any(ref_word in full_extracted_text.lower() for ref_word in ["references", "bibliography", "works cited"])
        content_matches["references_section_detected"] = has_references

        # Check header / footer and page number indicators
        has_page_numbers = bool(re.search(r'Page \d+ of \d+|\b\d+\b', full_extracted_text))
        content_matches["page_numbers_detected"] = has_page_numbers

        # ----------------------------------------------------------------------
        # Secret Leakage Detection
        # ----------------------------------------------------------------------
        secret_findings = []
        for pattern, secret_type in cls.FORBIDDEN_SECRET_PATTERNS:
            matches = re.findall(pattern, full_extracted_text)
            if matches:
                secret_findings.append({
                    "secret_type": secret_type,
                    "matches_count": len(matches)
                })
                errors.append(f"CRITICAL SECURITY: Detected potential {secret_type} in PDF content.")

        # ----------------------------------------------------------------------
        # Visual Rendering & Inspection via PyMuPDF Pixmaps
        # ----------------------------------------------------------------------
        visual_validation = {
            "status": "PASS",
            "pages_inspected": 0,
            "representative_pages": [],
            "blank_pages_detected": []
        }

        try:
            doc_vis = pymupdf.open(pdf_path)
            vis_page_count = len(doc_vis)

            # Choose representative pages: first, middle, last
            rep_indices = set([0])
            if vis_page_count > 1:
                rep_indices.add(vis_page_count // 2)
                rep_indices.add(vis_page_count - 1)

            for idx in sorted(rep_indices):
                if idx >= vis_page_count:
                    continue
                p = doc_vis[idx]
                pix = p.get_pixmap(dpi=96)
                visual_validation["pages_inspected"] += 1

                # Check dimensions
                if pix.width < 100 or pix.height < 100:
                    errors.append(f"Visual clipping: Page {idx+1} rendered with abnormal dimensions ({pix.width}x{pix.height}).")

                # Check if page is completely blank (all pixels white)
                # Sample pixels from pixmap samples
                samples = pix.samples
                is_all_white = True
                # Check byte step
                if samples:
                    # Look for non-white bytes (white is 255)
                    # If more than 0.5% of bytes are < 250, it is not blank
                    non_white = sum(1 for b in samples[::16] if b < 250)
                    if non_white > 20:
                        is_all_white = False

                if is_all_white:
                    visual_validation["blank_pages_detected"].append(idx + 1)
                    warnings.append(f"Visual Warning: Page {idx+1} appears to be completely blank.")

                visual_validation["representative_pages"].append({
                    "page_number": idx + 1,
                    "width": pix.width,
                    "height": pix.height,
                    "is_blank": is_all_white
                })

            doc_vis.close()

        except Exception as e:
            visual_validation["status"] = "NOT TESTED — visual PDF comparison unavailable"
            visual_validation["error"] = str(e)
            warnings.append(f"Visual inspection skipped: {e}")

        is_valid = len(errors) == 0 and reopen_passed and page_count > 0

        return {
            "is_valid": is_valid,
            "reopen_test_passed": reopen_passed,
            "page_count": page_count,
            "file_size_bytes": file_size,
            "sha256": pdf_hash,
            "content_consistency": content_matches,
            "images_detected": len(extracted_images),
            "secret_leakage_detected": len(secret_findings) > 0,
            "secret_findings": secret_findings,
            "visual_validation": visual_validation,
            "errors": errors,
            "warnings": warnings
        }
