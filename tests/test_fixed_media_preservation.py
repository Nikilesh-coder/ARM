"""
Regression tests for ARM Fixed Master Template Media Preservation Validation.
Covers:
1. A DOCX containing a 'word/media/' directory entry validates successfully when all actual media files are preserved.
2. The same document validates when the ZIP archive has no explicit media-directory entry.
3. Removing a genuine fixed template image still fails validation.
4. An explicitly authorized image replacement passes validation.
5. Logical asset IDs (e.g. image_1) are not incorrectly treated as physical media filenames.
6. Unrelated images remain protected during replacement.
7. Existing valid image-replacement tests continue to pass.
8. Validation against the production template 'finaldw.docx', if available.
"""

import os
import io
import shutil
import hashlib
import zipfile
import pytest
from PIL import Image as PILImage
import docx

from packages.replacement_engine.validator import ReplacementValidator
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.package_engine import PackageLevelDocxEngine


@pytest.fixture
def sample_docx_with_media_dir(tmp_path):
    """
    Creates a valid DOCX archive that explicitly includes a 'word/media/' directory entry.
    Contains:
    - word/media/ (directory entry, size 0, is_dir=True)
    - word/media/image1.png (genuine fixed logo)
    - word/media/image2.png (genuine figure)
    """
    base_docx = str(tmp_path / "base_template.docx")
    doc = docx.Document()
    doc.add_paragraph("ORIGINAL PROJECT TITLE: EMBEDDED SENSOR MONITORING")

    img1_path = str(tmp_path / "img1.png")
    PILImage.new("RGB", (60, 60), color="blue").save(img1_path)
    doc.add_picture(img1_path)

    img2_path = str(tmp_path / "img2.png")
    PILImage.new("RGB", (120, 80), color="green").save(img2_path)
    doc.add_picture(img2_path)

    doc.save(base_docx)

    # Re-pack explicitly adding a 'word/media/' directory entry
    docx_with_dir = str(tmp_path / "template_with_media_dir.docx")
    with zipfile.ZipFile(base_docx, "r") as z_in, zipfile.ZipFile(docx_with_dir, "w", zipfile.ZIP_DEFLATED) as z_out:
        # Explicit directory entry
        media_dir_info = zipfile.ZipInfo("word/media/")
        media_dir_info.external_attr = 0o755 << 16 | 0o040000  # directory attribute
        z_out.writestr(media_dir_info, "")

        for item in z_in.infolist():
            z_out.writestr(item, z_in.read(item.filename))

    return docx_with_dir


def test_1_media_directory_entry_preserved_validates(sample_docx_with_media_dir, tmp_path):
    """1. A DOCX containing a word/media/ directory entry validates successfully when all actual media files are preserved."""
    # When saved or copied, gen_docx has the exact images, with or without the folder entry
    gen_docx = str(tmp_path / "gen_doc1.docx")
    shutil.copyfile(sample_docx_with_media_dir, gen_docx)

    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_docx,
    )

    assert val_res["is_valid"] is True, f"Validation failed: {val_res['errors']}"
    assert len(val_res["errors"]) == 0
    # Crucially, ensure no error reported for empty basename ''
    assert not any(e["reason"] == "Fixed master template image '' was removed." for e in val_res["errors"])


def test_2_archive_without_media_dir_entry_validates(sample_docx_with_media_dir, tmp_path):
    """2. The same document validates when the generated ZIP archive has no explicit media-directory entry."""
    gen_no_dir = str(tmp_path / "gen_no_dir.docx")
    with zipfile.ZipFile(sample_docx_with_media_dir, "r") as z_in, zipfile.ZipFile(gen_no_dir, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            # Exclude directory entry
            if item.filename == "word/media/" or item.filename.endswith("/"):
                continue
            z_out.writestr(item, z_in.read(item.filename))

    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_no_dir,
    )

    assert val_res["is_valid"] is True, f"Validation failed: {val_res['errors']}"
    assert len(val_res["errors"]) == 0


def test_3_removing_genuine_fixed_template_image_fails(sample_docx_with_media_dir, tmp_path):
    """3. Removing a genuine fixed template image still fails validation."""
    gen_missing_img = str(tmp_path / "gen_missing_img.docx")
    with zipfile.ZipFile(sample_docx_with_media_dir, "r") as z_in, zipfile.ZipFile(gen_missing_img, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            # Drop image1.png
            if "image1.png" in item.filename:
                continue
            z_out.writestr(item, z_in.read(item.filename))

    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_missing_img,
    )

    assert val_res["is_valid"] is False
    assert any(
        e["field"] == "fixed_media" and "image1.png" in e["reason"]
        for e in val_res["errors"]
    )
    # Ensure it names the actual file, never ''
    assert not any("'' was removed" in e["reason"] for e in val_res["errors"])


def test_4_authorized_image_replacement_passes(sample_docx_with_media_dir, tmp_path):
    """4. An explicitly authorized image replacement passes validation."""
    gen_replaced = str(tmp_path / "gen_replaced.docx")
    new_bytes = b"NEW_IMAGE_BYTES_FOR_REPLACEMENT_123456"

    with zipfile.ZipFile(sample_docx_with_media_dir, "r") as z_in, zipfile.ZipFile(gen_replaced, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if "image2.png" in item.filename:
                z_out.writestr(item.filename, new_bytes)
            else:
                z_out.writestr(item, z_in.read(item.filename))

    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_replaced,
        allowed_replaced_media={"image2.png"},
    )

    assert val_res["is_valid"] is True, f"Validation failed: {val_res['errors']}"
    assert len(val_res["errors"]) == 0


def test_5_logical_asset_ids_not_confused_with_media_filenames(sample_docx_with_media_dir, tmp_path):
    """5. Logical asset IDs (e.g. image_1, figure_1) are not incorrectly treated as physical media filenames."""
    gen_replaced = str(tmp_path / "gen_replaced_mismatch.docx")
    new_bytes = b"NEW_MODIFIED_IMAGE_CONTENT"

    with zipfile.ZipFile(sample_docx_with_media_dir, "r") as z_in, zipfile.ZipFile(gen_replaced, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if "image2.png" in item.filename:
                z_out.writestr(item.filename, new_bytes)
            else:
                z_out.writestr(item, z_in.read(item.filename))

    # Passing ONLY a logical asset ID "figure_1" (which does not match image2.png) must NOT authorize image2.png modification
    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_replaced,
        allowed_replaced_media={"figure_1"},
    )

    # image2.png was modified without its physical path/filename being authorized -> must fail
    assert val_res["is_valid"] is False
    assert any("image2.png" in e["reason"] for e in val_res["errors"])


def test_6_unrelated_images_remain_protected_during_replacement(sample_docx_with_media_dir, tmp_path):
    """6. Unrelated images remain protected during replacement."""
    gen_unrelated_mod = str(tmp_path / "gen_unrelated_mod.docx")

    # Authorize replacement of image2.png, but someone maliciously also modified image1.png (the logo)
    with zipfile.ZipFile(sample_docx_with_media_dir, "r") as z_in, zipfile.ZipFile(gen_unrelated_mod, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if "image2.png" in item.filename:
                z_out.writestr(item.filename, b"AUTHORIZED_REPLACEMENT")
            elif "image1.png" in item.filename:
                z_out.writestr(item.filename, b"UNAUTHORIZED_LOGO_TAMPERING")
            else:
                z_out.writestr(item, z_in.read(item.filename))

    val_res = ReplacementValidator.validate_package_preservation(
        original_docx_path=sample_docx_with_media_dir,
        generated_docx_path=gen_unrelated_mod,
        allowed_replaced_media={"image2.png"},
    )

    assert val_res["is_valid"] is False
    assert any(
        e["field"] == "college_logo" and "image1.png" in e["reason"]
        for e in val_res["errors"]
    )


def test_7_docx_engine_e2e_replaces_and_preserves(sample_docx_with_media_dir, tmp_path):
    """7. Existing in-place replacement through DocxTemplateReplacementEngine passes validation."""
    out_docx = str(tmp_path / "engine_replaced_out.docx")
    new_img = str(tmp_path / "new_green_img.png")
    PILImage.new("RGB", (100, 100), color="yellow").save(new_img)

    engine = DocxTemplateReplacementEngine()
    result = engine.replace(
        template_path=sample_docx_with_media_dir,
        field_values={"project_title": "Advanced Robotics Machine"},
        image_assets={"figure_2": new_img},
        output_path=out_docx,
        job_id="test_reg_job",
        field_mapping=None,
        image_mapping=[
            {"action": "fixed", "arm_image_field": "logo", "rel_id": "rId9", "filename": "image1.png", "is_logo": True},
            {"action": "replace", "arm_image_field": "figure_2", "rel_id": "rId10", "filename": "image2.png", "is_logo": False},
        ],
    )

    assert result.success is True, f"Engine replace failed: {[e.model_dump() for e in result.errors]}"
    assert len(result.errors) == 0


def test_8_production_template_finaldw_validates_cleanly(tmp_path):
    """8. Run tests against the production template finaldw.docx, if available in the test environment."""
    candidates = [
        r"c:\Users\A9959\Downloads\finaldw.docx",
        r".storage/templates/finaldw.docx",
    ]
    finaldw_path = None
    for cand in candidates:
        if os.path.exists(cand):
            finaldw_path = cand
            break

    if not finaldw_path:
        pytest.skip("finaldw.docx not present in local test environment")

    # Run in DocxTemplateReplacementEngine
    out_docx1 = str(tmp_path / "finaldw_engine_out.docx")
    engine1 = DocxTemplateReplacementEngine()
    res1 = engine1.replace(
        template_path=finaldw_path,
        field_values={"project_title": "data wranging"},
        image_assets={},
        output_path=out_docx1,
        job_id="test_finaldw_engine",
    )
    assert res1.success is True, f"DocxTemplateReplacementEngine failed on finaldw: {[e.model_dump() for e in res1.errors]}"
    assert len(res1.errors) == 0

    # Run in PackageLevelDocxEngine
    out_docx2 = str(tmp_path / "finaldw_pkg_out.docx")
    engine2 = PackageLevelDocxEngine()
    res2 = engine2.replace(
        template_path=finaldw_path,
        field_values={"project_title": "data wranging"},
        image_assets={},
        output_path=out_docx2,
        job_id="test_finaldw_pkg",
    )
    assert res2.success is True, f"PackageLevelDocxEngine failed on finaldw: {[e.model_dump() for e in res2.errors]}"
    assert len(res2.errors) == 0
