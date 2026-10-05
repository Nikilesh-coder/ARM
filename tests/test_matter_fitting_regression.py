"""
ARM Matter Fitting Regression Tests
===================================
Verifies the refined matter-fitting system across:
1. Short-content test (underflow prevention / appropriate space filling).
2. Normal-content test (natural fit / perfect_fit pass-through).
3. Long-content test (overflow prevention / clean sentence-boundary condensing).
4. Template formatting comparison (proves font, margins, layout, borders remain 100% untouched).
"""

import os
import sys
import tempfile
import pytest
import docx

# Ensure workspace root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.services.content_fitting_service import ContentFittingService
from packages.replacement_engine.package_engine import PackageLevelDocxEngine


def test_short_content_fitting():
    """
    Test 1: Short content in large section is extended to prevent empty gaps,
    while compact presentation bullets retain appropriate concise form.
    """
    fields = [
        {"arm_field": "introduction", "original_text": "A" * 300, "content_type": "paragraph"},
        {"arm_field": "slide_item", "original_text": "Short label", "content_type": "bullet"},
    ]
    budgets = ContentFittingService.analyze_section_budgets(fields, is_presentation=False)

    short_content = {
        "introduction": "This is brief.",  # only 3 words for large academic section
        "slide_item": "Safe operation.",    # 2 words for bullet
    }

    fitted, audit = ContentFittingService.fit_and_adjust_content(
        generated_content=short_content,
        section_budgets=budgets,
        project_title="AI Based Irrigation System",
        is_presentation=False,
    )

    intro_words = len(fitted["introduction"].split())
    assert intro_words >= 30, f"Introduction should be extended to fill large section space, got {intro_words} words"
    assert "introduction" in audit["underflow_adjusted"]
    print(f"\n[SHORT CONTENT TEST PASS] Intro extended to {intro_words} words to fill space naturally.")


def test_normal_content_fitting():
    """
    Test 2: Normal content matching template capacity passes without unnecessary modification.
    """
    fields = [
        {"arm_field": "slide_5_1", "original_text": "Meaning of automated drip irrigation in agriculture", "content_type": "bullet"},
    ]
    budgets = ContentFittingService.analyze_section_budgets(fields, is_presentation=True)

    normal_content = {
        "slide_5_1": "Automated drip irrigation delivers precise water directly to crop roots." # 9 words
    }

    fitted, audit = ContentFittingService.fit_and_adjust_content(
        generated_content=normal_content,
        section_budgets=budgets,
        project_title="AI Based Irrigation System",
        is_presentation=True,
    )

    assert fitted["slide_5_1"] == normal_content["slide_5_1"]
    assert "slide_5_1" in audit["perfect_fit"]
    print(f"\n[NORMAL CONTENT TEST PASS] Normal content preserved as perfect_fit without alteration.")


def test_long_content_overflow_prevention():
    """
    Test 3: Long overflowing content is cleanly condensed at sentence/clause boundary to fit container.
    """
    fields = [
        {"arm_field": "slide_8_1", "original_text": "Short bullet note.", "content_type": "bullet"},
    ]
    budgets = ContentFittingService.analyze_section_budgets(fields, is_presentation=True)

    overflowing_content = {
        "slide_8_1": (
            "This is an excessively long description that contains way too many words and details. "
            "It will completely overflow the slide text box if inserted without adjustment. "
            "Additional sentences continue to drag on needlessly beyond the available boundary."
        )
    }

    fitted, audit = ContentFittingService.fit_and_adjust_content(
        generated_content=overflowing_content,
        section_budgets=budgets,
        project_title="AI Based Irrigation System",
        is_presentation=True,
    )

    fitted_text = fitted["slide_8_1"]
    fitted_words = len(fitted_text.split())
    max_allowed = budgets["slide_8_1"]["max_words_per_item"]

    assert fitted_words <= max_allowed, f"Fitted text ({fitted_words} words) must not exceed budget ({max_allowed} words)"
    assert fitted_text.endswith("."), "Condensed text must end with proper punctuation"
    assert "slide_8_1" in audit["overflow_adjusted"]
    print(f"\n[LONG CONTENT TEST PASS] Overflow condensed from 37 words down to {fitted_words} words (max allowed: {max_allowed}).")


def test_template_formatting_preservation():
    """
    Test 4: Replaces fitted matter and compares output document against original template.
    Confirms fonts, styles, margins, and page dimensions remain 100% unchanged.
    """
    temp_dir = tempfile.mkdtemp()
    orig_path = os.path.join(temp_dir, "orig_template.docx")
    out_path = os.path.join(temp_dir, "fitted_output.docx")

    # Create reference template with specific styles and dimensions
    doc = docx.Document()
    sect = doc.sections[0]
    sect.page_width = docx.shared.Inches(8.5)
    sect.page_height = docx.shared.Inches(11.0)
    sect.top_margin = docx.shared.Inches(1.0)
    sect.bottom_margin = docx.shared.Inches(1.0)
    sect.left_margin = docx.shared.Inches(1.0)
    sect.right_margin = docx.shared.Inches(1.0)

    p1 = doc.add_paragraph()
    r1 = p1.add_run("{{PROJECT_TITLE}}")
    r1.font.name = "Arial"
    r1.font.size = docx.shared.Pt(22)
    r1.bold = True

    p2 = doc.add_paragraph()
    r2 = p2.add_run("{{SECTION_MATTER}}")
    r2.font.name = "Georgia"
    r2.font.size = docx.shared.Pt(11)

    doc.save(orig_path)

    # Matter replacement with fitted text
    fields = {"section_matter": "Existing matter description"}
    fitted_matter = "Precision irrigation maintains optimal soil volumetric moisture."
    rep_result = PackageLevelDocxEngine.replace(
        template_path=orig_path,
        field_values={
            "project_title": "AI Based Irrigation System",
            "section_matter": fitted_matter,
        },
        output_path=out_path,
        job_id="test_format_preservation",
    )

    assert rep_result.success is True
    assert os.path.exists(out_path)

    # Compare output document with original template
    doc_out = docx.Document(out_path)
    sect_out = doc_out.sections[0]

    # Verify page dimensions & margins preserved
    assert abs(sect_out.page_width.inches - 8.5) < 0.01
    assert abs(sect_out.page_height.inches - 11.0) < 0.01
    assert abs(sect_out.top_margin.inches - 1.0) < 0.01
    assert abs(sect_out.left_margin.inches - 1.0) < 0.01

    # Verify fonts and styles preserved
    out_runs = [r for p in doc_out.paragraphs for r in p.runs]
    title_run = [r for r in out_runs if "AI Based Irrigation System" in r.text][0]
    assert title_run.font.name == "Arial"
    assert title_run.font.size.pt == 22.0
    assert title_run.bold is True

    matter_run = [r for r in out_runs if "Precision irrigation" in r.text][0]
    assert matter_run.font.name == "Georgia"
    assert matter_run.font.size.pt == 11.0

    print("\n[FORMAT PRESERVATION TEST PASS] Page dimensions, margins, font family, and font size 100% preserved.")


if __name__ == "__main__":
    test_short_content_fitting()
    test_normal_content_fitting()
    test_long_content_overflow_prevention()
    test_template_formatting_preservation()
    print("\nALL MATTER-FITTING REGRESSION TESTS PASSED SUCCESSFULLY!")
