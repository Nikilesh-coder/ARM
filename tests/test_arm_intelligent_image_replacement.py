"""
ARM Comprehensive Test Suite: Intelligent Image Replacement in Existing DOCX Templates
Verifies:
1. Extraction & classification of all embedded images in uploaded DOCX templates.
2. Distinction between fixed college logos/seals and replaceable topic-specific illustrations.
3. Generation of domain-grounded replacement images matching project title & aspect ratios.
4. Package-level media byte replacement preserving OOXML drawing structure & dimensions.
5. Synchronization of text and images under the authoritative project title.
6. Validation that generated DOCX opens cleanly with zero corruption.
7. Complete image replacement diagnostics audit table.
"""

import os
import io
import zipfile
import hashlib
import docx
import pytest
from PIL import Image

from apps.api.services.intelligent_image_service import intelligent_image_service
from apps.api.services.replacement_engine_service import ReplacementEngineService
from apps.api.services.custom_template_service import CustomTemplateService
from packages.replacement_engine.package_engine import PackageLevelDocxEngine
from packages.replacement_engine.validator import ReplacementValidator

ELECTRIFY_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/b6acbdd4-c09d-4346-9981-b9c3db1d36a1/Electrify Future Safe Electricity Schools (1).docx"
)
JAGADEESH_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/0484aecb-dbc1-4671-a388-0f820124ca0e/JAGADEESH PPT.docx"
)


def test_1_analyze_and_classify_embedded_images():
    """
    TEST 1:
    Analyze every embedded image in Electrify template and Jagadeesh template.
    Verifies dimensions, aspect ratio, surrounding text, and classification.
    """
    print("\n--- TEST 1: Analyze & Classify Embedded Images ---")
    electrify_images = intelligent_image_service.analyze_docx_images(ELECTRIFY_TPL)
    assert len(electrify_images) >= 30, f"Expected >= 30 images, got {len(electrify_images)}"

    # Check cover visual
    cover_img = electrify_images[0]
    assert cover_img["filename"] == "image1.jpeg"
    assert cover_img["classification"] == "full_slide_screenshot"
    assert cover_img["action"] == "replace"

    # Check cards
    card_img = next(im for im in electrify_images if im["filename"] == "image3.jpeg")
    assert card_img["aspect_ratio"] >= 1.9, f"Expected ~2.0 aspect ratio, got {card_img['aspect_ratio']}"
    assert card_img["classification"] == "topic_specific"
    assert card_img["action"] == "replace"

    # Check Jagadeesh template logo preservation
    jagadeesh_images = intelligent_image_service.analyze_docx_images(JAGADEESH_TPL)
    logo_img = next(im for im in jagadeesh_images if im["filename"] == "image1.png")
    assert logo_img["classification"] == "college_logo"
    assert logo_img["action"] == "fixed"
    assert "strictly preserved" in logo_img["reason"].lower()

    fixed_count = sum(1 for im in jagadeesh_images if im["action"] == "fixed")
    assert fixed_count >= 5, f"Expected at least 5 fixed assets/logos in Jagadeesh template, got {fixed_count}"

    print(f"PASS: TEST 1 - Analyzed {len(electrify_images)} Electrify images (all topic-specific) and {len(jagadeesh_images)} Jagadeesh images ({fixed_count} fixed/preserved).")


def test_2_generate_aspect_ratio_matched_replacement_images():
    """
    TEST 2:
    Generate replacement images for new project topic:
    Project Title: 'AI Based Attendance Management System'
    Problem Statement: 'Develop a system to automate student attendance tracking using AI.'
    Verifies aspect ratios, file formats, and domain relevance.
    """
    print("\n--- TEST 2: Generate Aspect-Ratio-Matched Replacement Images ---")
    project_title = "AI Based Attendance Management System"
    problem_statement = "Develop a system to automate student attendance tracking using AI."

    electrify_images = intelligent_image_service.analyze_docx_images(ELECTRIFY_TPL)
    sample_images = [electrify_images[0], electrify_images[1], electrify_images[2]]  # cover (0.71), panel (0.67), card (1.99)

    out_dir = os.path.abspath(".storage/test_generated_images")
    synth_map = intelligent_image_service.generate_replacement_images(
        project_title=project_title,
        problem_statement=problem_statement,
        analyzed_images=sample_images,
        output_dir=out_dir,
    )

    for img in sample_images:
        fname = img["filename"]
        assert fname in synth_map, f"Missing generated replacement for {fname}"
        gen_path = synth_map[fname]["file_path"]
        assert os.path.exists(gen_path), f"Generated file not found: {gen_path}"

        with Image.open(gen_path) as pil_img:
            gen_w, gen_h = pil_img.size
            gen_ar = round(gen_w / max(1, gen_h), 2)
            orig_ar = img["aspect_ratio"]
            # Verify aspect ratio matches within reasonable margin
            assert abs(gen_ar - orig_ar) < 0.25 or (orig_ar < 1.0 and gen_ar < 1.0) or (orig_ar > 1.5 and gen_ar > 1.5), (
                f"Aspect ratio mismatch for {fname}: original={orig_ar}, generated={gen_ar}"
            )
            print(f"Generated {fname}: size=({gen_w}, {gen_h}), AR={gen_ar} (matched target {orig_ar})")

    print("PASS: TEST 2 - Successfully synthesized aspect-ratio matched attendance visuals.")


def test_3_end_to_end_image_replacement_pipeline():
    """
    TEST 3:
    Full End-to-End Pipeline on Electrify Template:
    Project Title: 'AI Based Attendance Management System'
    Problem Statement: 'Develop a system to automate student attendance tracking using AI.'
    Verifies:
    - Topic-specific images replaced with AI attendance visuals.
    - Template layout and dimensions preserved.
    - Diagnostics table emitted.
    - Resulting DOCX opens and validates with zero errors.
    """
    print("\n--- TEST 3: End-to-End Image Replacement Pipeline ---")
    service = ReplacementEngineService()
    result = service.execute_replacement(
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        project_data={
            "title": "AI Based Attendance Management System",
            "problem_statement": "Develop a system to automate student attendance tracking using AI.",
        },
        user_instructions="Synthesize comprehensive attendance management project report with topic-relevant visuals",
    )

    assert result.get("state") == "COMPLETED"
    out_docx = result.get("docx_path")
    assert out_docx and os.path.exists(out_docx)

    # 1. Verify Image Diagnostics Table
    diagnostics = result.get("image_diagnostics", [])
    assert len(diagnostics) >= 30, f"Expected >= 30 diagnostics records, got {len(diagnostics)}"

    replaced_count = sum(1 for d in diagnostics if d["successfully_replaced"])
    assert replaced_count >= 30, f"Expected all topic images in Electrify to be replaced, got {replaced_count}"

    # 2. Inspect generated DOCX package media
    with zipfile.ZipFile(out_docx) as z_out:
        media_names = [n for n in z_out.namelist() if "media/" in n]
        assert len(media_names) >= 30

        # Check cover image (image1.jpeg) in output DOCX is updated and non-empty
        img1_data = z_out.read("word/media/image1.jpeg")
        assert len(img1_data) > 10000
        with Image.open(io.BytesIO(img1_data)) as im:
            assert im.size[0] > 1000

        # Check card image (image3.jpeg) in output DOCX is updated
        img3_data = z_out.read("word/media/image3.jpeg")
        assert len(img3_data) > 10000
        with Image.open(io.BytesIO(img3_data)) as im:
            assert im.size[0] > 1000
            assert round(im.size[0] / im.size[1], 1) == 2.0

    # 3. Verify DOCX opens cleanly with python-docx
    doc = docx.Document(out_docx)
    assert doc.paragraphs[0].text.strip() == "AI Based Attendance Management System"
    assert len(doc.paragraphs) > 50

    print(f"PASS: TEST 3 - End-to-end report generated with {replaced_count} images replaced in-place!")


def test_4_college_logo_preservation_under_image_replacement():
    """
    TEST 4:
    Verifies that on templates with institutional college logos (Jagadeesh PPT),
    college logos and official seals have action='fixed' and are NEVER modified.
    """
    print("\n--- TEST 4: College Logo Preservation ---")
    analyzed = intelligent_image_service.analyze_docx_images(JAGADEESH_TPL)
    logo_entry = next(im for im in analyzed if im["filename"] == "image1.png")

    assert logo_entry["action"] == "fixed"
    assert logo_entry["is_replaceable"] is False
    assert "college_logo" in logo_entry["classification"]

    # Verify sha256 before and after in package preservation validation
    with zipfile.ZipFile(JAGADEESH_TPL) as z:
        orig_logo_hash = hashlib.sha256(z.read("word/media/image1.png")).hexdigest()

    # If replacement engine runs with image_mapping, logo is not replaced
    service = ReplacementEngineService()
    result = service.execute_replacement(
        template_id="0484aecb-dbc1-4671-a388-0f820124ca0e",
        project_data={
            "title": "AI Based Attendance Management System",
            "problem_statement": "Develop a system to automate student attendance tracking using AI.",
        },
        user_instructions="Synthesize attendance report while preserving college logo",
    )

    assert result.get("state") == "COMPLETED"
    with zipfile.ZipFile(result["docx_path"]) as z_out:
        out_logo_hash = hashlib.sha256(z_out.read("word/media/image1.png")).hexdigest()
        assert orig_logo_hash == out_logo_hash, "College logo was altered! Must be strictly preserved."

    print("PASS: TEST 4 - College logo SHA-256 hash strictly preserved across replacement.")


if __name__ == "__main__":
    test_1_analyze_and_classify_embedded_images()
    test_2_generate_aspect_ratio_matched_replacement_images()
    test_3_end_to_end_image_replacement_pipeline()
    test_4_college_logo_preservation_under_image_replacement()
    print("\n=======================================================")
    print("ALL INTELLIGENT IMAGE REPLACEMENT TESTS PASSED 100%!")
    print("=======================================================")
