"""
Tests for ARM Automated PDF -> DOCX -> Final Report Visual and Structural Comparison.
Runs the diagnostic engine on the real JAGADEESH PPT.pdf template and its generated report.
"""

import os
import glob
import pytest
from apps.api.services.pdf_visual_comparison_service import pdf_visual_comparison_service


def find_test_files():
    """Locates the exact test files from recent E2E run or storage."""
    base_storage = os.path.join(os.getcwd(), ".storage")

    # 1. Original PDF
    pdf_candidates = [
        os.path.join(base_storage, "templates", "users", "1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd", "templates", "059dbf96-994a-464d-91a7-a6c9049a785c", "JAGADEESH PPT.pdf"),
    ] + glob.glob(os.path.join(base_storage, "**", "JAGADEESH PPT.pdf"), recursive=True)

    orig_pdf = next((p for p in pdf_candidates if os.path.exists(p)), None)

    # 2. Converted DOCX (latest)
    docx_candidates = sorted(
        glob.glob(os.path.join(base_storage, "**", "*JAGADEESH*working.docx"), recursive=True),
        key=os.path.getmtime,
        reverse=True,
    )
    conv_docx = next((p for p in docx_candidates if os.path.exists(p)), None)

    # 3. Final Report (latest)
    report_candidates = sorted(
        glob.glob(os.path.join(base_storage, "reports", "rep_*.docx")),
        key=os.path.getmtime,
        reverse=True,
    )
    final_report = next((p for p in report_candidates if os.path.exists(p)), None)

    return orig_pdf, conv_docx, final_report


def test_pdf_visual_and_structural_fidelity_comparison():
    """
    Executes visual & structural comparison across:
      A. Original PDF Template
      B. Converted DOCX Template
      C. Final ARM Generated Report DOCX
    """
    orig_pdf, conv_docx, final_report = find_test_files()

    assert orig_pdf is not None, "Original PDF template 'JAGADEESH PPT.pdf' not found"
    assert conv_docx is not None, "Converted DOCX template not found"
    assert final_report is not None, "Final ARM generated report DOCX not found"

    print("\n" + "=" * 80)
    print("ARM PDF VISUAL & STRUCTURAL FIDELITY DIAGNOSTIC")
    print("=" * 80)
    print(f"Original PDF:    {orig_pdf}")
    print(f"Converted DOCX:  {conv_docx}")
    print(f"Final ARM DOCX:  {final_report}")
    print("=" * 80)

    template_id = "7eefbd8b-9529-4f2c-b9c4-ac54dbbabf08"
    result = pdf_visual_comparison_service.run_full_comparison(
        orig_pdf_path=orig_pdf,
        conv_docx_path=conv_docx,
        final_docx_path=final_report,
        template_id=template_id,
        run_id="jagadeesh_ppt_fidelity_audit",
    )

    # Assertions
    assert "overall_result" in result
    assert "first_failure_stage" in result
    assert os.path.exists(result["json_report_path"])
    assert os.path.exists(result["markdown_report_path"])

    pc = result["page_count"]
    print(f"\nPage Counts: Original PDF={pc['original_pdf']} | Converted DOCX={pc['converted_docx']} | Final ARM={pc['final_arm']}")
    print(f"Overall Result:      {result['overall_result']}")
    print(f"FIRST FAILURE STAGE: {result['first_failure_stage']}")
    print(f"JSON Report:         {result['json_report_path']}")
    print(f"Markdown Report:     {result['markdown_report_path']}")
    print(f"Contact Sheets:      {list(result['contact_sheets'].values())}")
    print("=" * 80)

    # Visual contact sheets check
    for sheet_name, sheet_path in result["contact_sheets"].items():
        assert os.path.exists(sheet_path), f"Contact sheet '{sheet_name}' was not generated"

    assert len(result["pages_ab_diffs"]) > 0
    assert len(result["pages_bc_diffs"]) > 0
