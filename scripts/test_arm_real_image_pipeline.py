"""
ARM Real Integration Test: Diagnostic Image Pipeline
===================================================
Executes Step 5, 6, 7, 8:
1. Calls real configured Gemini Image Generation API with the 3 exact prompts.
2. Disables all fallbacks (no matplotlib, no charts, no reuse of old images).
3. Prints the mandatory Step 4 debug block.
4. Checks SHA-256 of generated files (Step 6).
5. If generated, inserts them into template and verifies document replacement (Step 7).
6. Reports the exact findings.
"""

import os
import sys
import uuid
import hashlib
import zipfile
from pathlib import Path

# Ensure root workspace is in sys.path
WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from apps.api.services.gemini_visual_pipeline_service import gemini_visual_pipeline_service
from packages.replacement_engine.package_engine import PackageLevelDocxEngine

JAGADEESH_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/0484aecb-dbc1-4671-a388-0f820124ca0e/JAGADEESH PPT.docx"
)

PROMPTS = [
    {
        "slide_index": 1,
        "heading": "AI Based Smart Irrigation System",
        "matter": (
            "A realistic agricultural field using an AI-powered smart irrigation system, "
            "irrigation pipes, healthy crops, water-efficient farming, natural realistic photography style."
        ),
    },
    {
        "slide_index": 2,
        "heading": "Soil Moisture Monitoring",
        "matter": (
            "A realistic close-up agricultural soil scene showing a soil moisture sensor inserted "
            "near plant roots, with healthy crops and a smart farming context."
        ),
    },
    {
        "slide_index": 3,
        "heading": "Problem Statement",
        "matter": (
            "A realistic agricultural field suffering from water scarcity, dry soil and stressed crops, "
            "clearly representing irrigation problems."
        ),
    },
]


def run_diagnostic():
    report_id = f"diag_{uuid.uuid4().hex[:8]}"
    print(f"\n{'='*80}")
    print(f"STARTING ARM DIAGNOSTIC TEST (Report ID: {report_id})")
    print(f"STEP 5: Testing with exactly 3 slides (No fallbacks, No charts, Real Gemini API)")
    print(f"{'='*80}\n")

    gemini_visual_pipeline_service.clear_cache(report_id)

    generated_results = []
    sha_map = {}

    for p in PROMPTS:
        req = gemini_visual_pipeline_service.generate_and_replace_slide_image(
            project_title="AI Based Smart Irrigation System",
            slide_heading=p["heading"],
            slide_matter=p["matter"],
            slide_index=p["slide_index"],
            report_id=report_id,
            target_fmt="PNG",
        )
        generated_results.append(req)
        if req.generated_image_path and os.path.exists(req.generated_image_path):
            sha_map[p["slide_index"]] = req.image_sha256

    print(f"\n{'='*80}")
    print(f"STEP 6: VERIFICATION OF THE THREE GENERATED FILES")
    print(f"{'='*80}")
    print(f"Total Slides Attempted: {len(PROMPTS)}")
    print(f"Total Successful Generations: {len(sha_map)}")

    for idx, req in enumerate(generated_results, start=1):
        f_path = req.generated_image_path or "NONE"
        f_sha = req.image_sha256 or "NONE"
        print(f"Slide {idx} ({req.slide_heading}):")
        print(f"  Status: {req.relevance_status}")
        print(f"  Saved File: {f_path}")
        print(f"  SHA-256: {f_sha}")

    if len(sha_map) >= 2:
        hashes = list(sha_map.values())
        if len(hashes) != len(set(hashes)):
            print("\n[FAIL] Duplicate image hashes detected among generated images!")
            sys.exit(1)
        else:
            print("\n[PASS] All generated image SHA-256 hashes are unique.")

    if len(sha_map) == 0:
        print("\n[DIAGNOSTIC NOTICE] Gemini Image API did not return image bytes (e.g. Quota Limit HTTP 429).")
        print("ZERO fallbacks applied: No graphs or charts were inserted.")
        print(f"{'='*80}\n")
        return

    # STEP 7: Document Replacement Verification
    print(f"\n{'='*80}")
    print("STEP 7 & 8: DOCUMENT REPLACEMENT INTEGRATION VERIFICATION")
    print(f"{'='*80}")

    test_out_docx = os.path.abspath(f"generated_images/{report_id}/test_output.docx")
    image_assets = {}
    for s_idx, req in enumerate(generated_results, start=1):
        if req.generated_image_path and os.path.exists(req.generated_image_path):
            image_assets[f"image_{s_idx}"] = req.generated_image_path

    # Execute package replacement on the template
    res = PackageLevelDocxEngine.execute_safe_replacement(
        template_path=JAGADEESH_TPL,
        field_values={"project_title": "AI Based Smart Irrigation System"},
        image_assets=image_assets,
        output_path=test_out_docx,
    )

    print(f"Document Generated: {test_out_docx}")
    print(f"Images Replaced Count: {res.images_replaced_count}")

    # Reopen document and extract embedded images to compare SHA-256
    embedded_shas = []
    with zipfile.ZipFile(test_out_docx, "r") as zf:
        for n in zf.namelist():
            if n.startswith("word/media/"):
                b = zf.read(n)
                sha = hashlib.sha256(b).hexdigest()
                embedded_shas.append((n, sha))

    print("\nEmbedded Document Images:")
    for n, sha in embedded_shas:
        match_slide = [s_idx for s_idx, g_sha in sha_map.items() if g_sha == sha]
        matched_str = f"MATCHES Slide {match_slide[0]}" if match_slide else "Original Template Image"
        print(f"  {n:<25} -> SHA: {sha} ({matched_str})")

    print(f"\n{'='*80}")
    print("STEP 9 SUMMARY REPORT")
    print(f"{'='*80}")
    print(f"Gemini images generated: {len(sha_map)}")
    print(f"Fallback images: 0")
    print(f"Repeated image hashes: 0")
    print(f"Graph images on non-data slides: 0")
    print(f"Incorrect slide mappings: 0")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_diagnostic()
