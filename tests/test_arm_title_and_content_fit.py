"""
ARM Comprehensive Test Suite: Title Accuracy, Page-Fit & Single Source of Truth
Validates all 7 required test cases:
- TEST 1: Exact first-page main title replacement on Electrify template
- TEST 2: Detection of unlabeled prominent first-page title
- TEST 3: AI-generated alternative title is strictly ignored (student title is single source of truth)
- TEST 4: Long project title wrapping with exact preservation
- TEST 5: Small content area generates concise space-fitting matter
- TEST 6: Large content area generates detailed matter without overflow
- TEST 7: Adaptation to different page sizes & orientations (20x11.25 landscape vs 8.5x11 portrait)
"""

import os
import re
import pytest
import docx
from apps.api.services.custom_template_service import CustomTemplateService
from apps.api.services.content_fitting_service import ContentFittingService
from apps.api.services.replacement_engine_service import ReplacementEngineService
from packages.replacement_engine.package_engine import PackageLevelDocxEngine

ELECTRIFY_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/b6acbdd4-c09d-4346-9981-b9c3db1d36a1/Electrify Future Safe Electricity Schools (1).docx"
)
JAGADEESH_TPL = os.path.abspath(
    r".storage/templates/users/1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd/templates/0484aecb-dbc1-4671-a388-0f820124ca0e/JAGADEESH PPT.docx"
)
MASTER_TPL = os.path.abspath(
    r".storage/templates/master_college_template.docx"
)


def test_case_1_exact_first_page_title_replacement():
    """
    TEST 1:
    Student Project Title: 'AI Based Attendance Management System'
    Template: 'Electrify Future Safe Electricity Schools (1).docx'
    Expected: First-page main title becomes exactly 'AI Based Attendance Management System'.
    """
    print("\n--- TEST 1: Exact First-Page Main Title Replacement ---")
    service = ReplacementEngineService()
    result = service.execute_replacement(
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        project_data={
            "title": "AI Based Attendance Management System",
            "problem_statement": "Develop an automated student attendance tracking system.",
        },
        user_instructions="Synthesize report for attendance tracking",
    )

    assert result.get("state") == "COMPLETED"
    out_path = result.get("docx_path")
    assert out_path and os.path.exists(out_path)

    doc = docx.Document(out_path)
    p0 = doc.paragraphs[0]
    assert p0.text.strip() == "AI Based Attendance Management System"
    assert "ELECTRIFY THE FUTURE" not in p0.text
    print("PASS: TEST 1 - P0 text is exactly 'AI Based Attendance Management System'.")


def test_case_2_unlabeled_first_page_title_detection():
    """
    TEST 2:
    Template has no 'Project Title' label.
    Expected: System still identifies the prominent first-page title.
    """
    print("\n--- TEST 2: Unlabeled First-Page Title Detection ---")
    res = CustomTemplateService.analyze_template_docx(ELECTRIFY_TPL)
    fields = res.get("detected_text_fields", [])
    title_field = next((f for f in fields if f.get("arm_field") == "project_title"), None)

    assert title_field is not None, "Project title was not detected!"
    assert title_field.get("action") == "replace"
    assert "ELECTRIFY THE FUTURE" in (title_field.get("original_text") or "")
    print(f"PASS: TEST 2 - Identified unlabeled title: '{title_field.get('original_text')}'")


def test_case_3_gemini_alternative_title_ignored():
    """
    TEST 3:
    Gemini/Search generates an alternative title like 'Intelligent Student Monitoring Platform'.
    Expected: Gemini title is strictly ignored as the report title.
    Student's Project Title remains authoritative.
    """
    print("\n--- TEST 3: Gemini Alternative Title Ignored ---")
    student_title = "AI Based Attendance Management System"
    gemini_alternative_title = "Intelligent Student Monitoring Platform"

    # Simulate AI output containing alternative title
    generated_content = {
        "title": gemini_alternative_title,
        "project_title": gemini_alternative_title,
        "introduction": "This project introduces automated attendance.",
        "objectives": ["Automate tracking", "Enhance security"],
    }

    section_budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[
            {"arm_field": "project_title", "original_text": "ELECTRIFY THE FUTURE"},
            {"arm_field": "introduction", "original_text": "Old intro text"},
        ],
        project_title=student_title,
    )

    fitted, _ = ContentFittingService.fit_and_adjust_content(
        generated_content=generated_content,
        section_budgets=section_budgets,
        project_title=student_title,
    )

    assert fitted["project_title"] == student_title
    assert fitted["project_title"] != gemini_alternative_title
    print(f"PASS: TEST 3 - Student title '{fitted['project_title']}' preserved; AI alternative '{gemini_alternative_title}' discarded.")


def test_case_4_long_project_title_wrapping():
    """
    TEST 4:
    Long project title.
    Expected: Exact student title remains, wrapped naturally inside existing title area.
    """
    print("\n--- TEST 4: Long Project Title Wrapping ---")
    long_title = "Comprehensive Deep Learning and Computer Vision System for Automated Multi-Camera Student Attendance Tracking in University Campuses"
    service = ReplacementEngineService()
    result = service.execute_replacement(
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        project_data={
            "title": long_title,
            "problem_statement": "Real-time attendance in lecture halls.",
        },
        user_instructions="Synthesize report with long title",
    )

    assert result.get("state") == "COMPLETED"
    doc = docx.Document(result["docx_path"])
    p0 = doc.paragraphs[0]
    assert p0.text.strip() == long_title
    print(f"PASS: TEST 4 - Long title preserved exactly with {len(long_title.split())} words.")


def test_case_5_small_content_area():
    """
    TEST 5:
    Small content area (e.g. presentation slide bullet or compact text area).
    Expected: Short matter that fits the available space.
    """
    print("\n--- TEST 5: Small Content Area Fitting ---")
    budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[
            {"arm_field": "bullet_1", "content_type": "bullet", "original_text": "Short item 1"},
            {"arm_field": "bullet_2", "content_type": "bullet", "original_text": "Short item 2"},
        ],
        page_settings={"width_in": 20.0, "height_in": 11.25},
        is_presentation=True,
    )

    assert budgets["bullet"]["area_category"] == "small"
    assert budgets["bullet"]["max_words_per_item"] <= 15

    # Test overflowing bullet gets condensed
    overflow_bullets = {
        "bullet": [
            "This is an excessively long bullet point that goes on and on with way too many unnecessary words designed to trigger the overflow detector in ARM.",
            "Another extraordinarily verbose bullet point that exceeds slide layout capacity.",
        ]
    }
    fitted, audit = ContentFittingService.fit_and_adjust_content(
        generated_content=overflow_bullets,
        section_budgets=budgets,
        project_title="AI Based Attendance Management System",
        is_presentation=True,
    )

    for item in fitted["bullet"]:
        assert len(item.split()) <= budgets["bullet"]["max_words_per_item"]
    print("PASS: TEST 5 - Small content area bullets strictly sized <= 15 words.")


def test_case_6_large_content_area():
    """
    TEST 6:
    Large content area (e.g. full academic chapter introduction).
    Expected: More detailed matter that naturally fills the available area without overflow.
    """
    print("\n--- TEST 6: Large Content Area Fitting ---")
    budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[
            {"arm_field": "introduction", "content_type": "paragraph", "original_text": "A" * 1200},
        ],
        page_settings={"width_in": 8.5, "height_in": 11.0},
        is_presentation=False,
    )

    assert budgets["introduction"]["area_category"] == "large"
    assert budgets["introduction"]["max_words"] >= 150
    assert budgets["introduction"]["max_chars"] >= 1000
    print(f"PASS: TEST 6 - Large area budget accommodates up to {budgets['introduction']['max_words']} words.")


def test_case_7_different_page_sizes_and_orientations():
    """
    TEST 7:
    Different page sizes/orientations (Landscape 20x11.25 vs Portrait 8.5x11).
    Expected: Content length adapts to actual template dimensions.
    """
    print("\n--- TEST 7: Page Sizes & Orientation Adaptation ---")
    landscape_budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[{"arm_field": "overview", "content_type": "paragraph", "original_text": "Slide text"}],
        page_settings={"width_in": 20.0, "height_in": 11.25, "orientation": "landscape"},
        is_presentation=True,
    )

    portrait_budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[{"arm_field": "overview", "content_type": "paragraph", "original_text": "Document report text"}],
        page_settings={"width_in": 8.5, "height_in": 11.0, "orientation": "portrait"},
        is_presentation=False,
    )

    assert landscape_budgets["overview"]["is_presentation"] is True
    assert portrait_budgets["overview"]["is_presentation"] is False
    # Portrait document section allows significantly longer text than landscape presentation slide text box
    assert portrait_budgets["overview"]["max_chars"] > landscape_budgets["overview"]["max_chars"]
    print(
        f"PASS: TEST 7 - Portrait max_chars ({portrait_budgets['overview']['max_chars']}) > "
        f"Landscape max_chars ({landscape_budgets['overview']['max_chars']}). Adaptively sized."
    )


def test_case_8_search_query_cannot_override_saved_project_title_case_1():
    """
    REGRESSION TEST CASE 1:
    Project Name: 'AI Based Attendance Management System'
    Search Query: 'Smart classroom attendance using face recognition'
    Expected Final Report Title in DOCX: 'AI Based Attendance Management System'
    (NOT 'Smart classroom attendance using face recognition')
    """
    print("\n--- TEST 8: Saved Project Name vs Search Query (Case 1) ---")
    from apps.api.routers.projects import _PROJECTS_STORE
    project_id = "proj_test_reg_attendance"
    _PROJECTS_STORE[project_id] = {
        "id": project_id,
        "title": "AI Based Attendance Management System",
        "project_name": "AI Based Attendance Management System",
        "report_title": "AI Based Attendance Management System",
        "description": "An AI-based system for managing student attendance.",
    }

    service = ReplacementEngineService()
    result = service.execute_replacement(
        project_id=project_id,
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        search_query="Smart classroom attendance using face recognition",
        user_instructions="Research smart classroom facial recognition for attendance",
    )

    assert result.get("state") == "COMPLETED"
    out_path = result.get("docx_path")
    assert out_path and os.path.exists(out_path)

    doc = docx.Document(out_path)
    p0_text = doc.paragraphs[0].text.strip()
    assert p0_text == "AI Based Attendance Management System", f"Expected 'AI Based Attendance Management System', got '{p0_text}'"
    assert "Smart classroom attendance using face recognition" not in p0_text
    assert result.get("title") == "AI Based Attendance Management System"
    print("PASS: TEST 8 - DOCX title is strictly 'AI Based Attendance Management System', search query ignored as title.")


def test_case_9_search_query_cannot_override_saved_project_title_case_2():
    """
    REGRESSION TEST CASE 2:
    Project Name: 'Smart Waste Management System'
    Search Query: 'AI waste segregation technologies'
    Expected Final Report Title in DOCX: 'Smart Waste Management System'
    (NOT 'AI waste segregation technologies')
    """
    print("\n--- TEST 9: Saved Project Name vs Search Query (Case 2) ---")
    from apps.api.routers.projects import _PROJECTS_STORE
    project_id = "proj_test_reg_waste"
    _PROJECTS_STORE[project_id] = {
        "id": project_id,
        "title": "Smart Waste Management System",
        "project_name": "Smart Waste Management System",
        "report_title": "Smart Waste Management System",
        "description": "An IoT and AI system for municipal waste segregation.",
    }

    service = ReplacementEngineService()
    result = service.execute_replacement(
        project_id=project_id,
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        search_query="AI waste segregation technologies",
        user_instructions="Explore sensors and automated mechanical sorters",
    )

    assert result.get("state") == "COMPLETED"
    out_path = result.get("docx_path")
    assert out_path and os.path.exists(out_path)

    doc = docx.Document(out_path)
    p0_text = doc.paragraphs[0].text.strip()
    assert p0_text == "Smart Waste Management System", f"Expected 'Smart Waste Management System', got '{p0_text}'"
    assert "AI waste segregation technologies" not in p0_text
    assert result.get("title") == "Smart Waste Management System"
    print("PASS: TEST 9 - DOCX title is strictly 'Smart Waste Management System', search query ignored as title.")


def test_case_10_backend_safety_check_prevents_override():
    """
    REGRESSION TEST CASE 3:
    Backend Safety Check:
    Even if caller passes project_data with title = search_query,
    backend detects saved project name differs, PREVENTS the override,
    and enforces saved project name as the final report title.
    """
    print("\n--- TEST 10: Backend Safety Check Prevents Search Query Override ---")
    from apps.api.routers.projects import _PROJECTS_STORE
    project_id = "proj_test_reg_safety"
    _PROJECTS_STORE[project_id] = {
        "id": project_id,
        "title": "AI Based Attendance Management System",
        "project_name": "AI Based Attendance Management System",
        "description": "An AI-based system for managing student attendance.",
    }

    service = ReplacementEngineService()
    # Malformed/corrupted caller attempts to pass search query as project_data title
    result = service.execute_replacement(
        project_id=project_id,
        template_id="b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
        project_data={
            "title": "Smart classroom attendance using face recognition",
            "search_query": "Smart classroom attendance using face recognition",
        },
    )

    assert result.get("state") == "COMPLETED"
    out_path = result.get("docx_path")
    doc = docx.Document(out_path)
    p0_text = doc.paragraphs[0].text.strip()
    assert p0_text == "AI Based Attendance Management System"
    assert "Smart classroom attendance using face recognition" not in p0_text
    print("PASS: TEST 10 - Safety check successfully PREVENTED search query from corrupting title.")


def test_case_11_iterative_fit_underflow_extension():
    """
    TEST 11:
    Iterative Fit Underflow Extension:
    When generated matter is too short for a large available area,
    ARM detects underflow, iteratively extends the content with substantive,
    topic-relevant technical prose grounded in the student's project title,
    and achieves Fit Status: PASS.
    """
    print("\n--- TEST 11: Iterative Fit Underflow Extension ---")
    student_title = "AI Based Attendance Management System"
    too_short_intro = "This project introduces automated student attendance tracking using computer vision and edge cameras."
    initial_words = len(too_short_intro.split())

    budgets = ContentFittingService.analyze_section_budgets(
        detected_fields=[
            {"arm_field": "introduction", "content_type": "paragraph", "original_text": "A" * 1500},
        ],
        page_settings={"width_in": 8.5, "height_in": 11.0},
        project_title=student_title,
        is_presentation=False,
    )

    intro_budget = budgets["introduction"]
    assert intro_budget["area_category"] == "large"
    assert intro_budget["min_words"] >= 200, f"Expected min_words >= 200, got {intro_budget['min_words']}"
    assert initial_words < intro_budget["min_words"], "Initial content should be under budget to test extension"

    fitted, audit = ContentFittingService.fit_and_adjust_content(
        generated_content={"introduction": too_short_intro},
        section_budgets=budgets,
        project_title=student_title,
        is_presentation=False,
    )

    assert "introduction" in audit["underflow_adjusted"], "Expected introduction to be underflow adjusted"
    extended_intro = fitted["introduction"]
    extended_words = len(extended_intro.split())

    # Verify substantive technical expansion
    assert extended_words >= intro_budget["min_words"], (
        f"Extended words ({extended_words}) should meet min_words ({intro_budget['min_words']})"
    )
    assert student_title.lower() in extended_intro.lower()
    # Confirm presence of domain-specific technical prose (not generic filler)
    assert any(term in extended_intro.lower() for term in ["architecture", "pipeline", "real-time", "accuracy", "deployment", "model"])
    print(f"PASS: TEST 11 - Underflow extended from {initial_words} words to {extended_words} words. Fit Status: PASS.")


def test_case_12_master_template_fit_and_page_audit():
    """
    TEST 12:
    Master College Template Content-Fitting & Page Fit Audit:
    Verifies that Master Template replacement runs through content-fitting
    and generates an audit proving adequate page-fill without redesign.
    """
    print("\n--- TEST 12: Master Template Fit & Page Audit ---")
    from apps.api.routers.projects import _PROJECTS_STORE
    project_id = "proj_test_master_fit"
    _PROJECTS_STORE[project_id] = {
        "id": project_id,
        "title": "AI Based Attendance Management System",
        "project_name": "AI Based Attendance Management System",
        "report_title": "AI Based Attendance Management System",
        "description": "An automated deep learning system for lecture hall attendance verification.",
    }

    service = ReplacementEngineService()
    result = service.execute_replacement(
        project_id=project_id,
        template_id=None,  # Master template
        user_instructions="Synthesize comprehensive attendance management project report",
    )

    assert result.get("state") == "COMPLETED"
    out_path = result.get("docx_path")
    assert out_path and os.path.exists(out_path)

    # Verify page fit audit
    page_audit = result.get("page_fit_audit", {})
    assert page_audit.get("valid") is True, f"Page fit audit failed: {page_audit}"
    assert page_audit.get("title_matched") is True
    assert page_audit.get("total_doc_words", 0) >= 100

    doc = docx.Document(out_path)
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "AI Based Attendance Management System" in full_text
    print(f"PASS: TEST 12 - Master template compiled with {page_audit.get('total_doc_words')} words and valid page-fit.")


if __name__ == "__main__":
    test_case_1_exact_first_page_title_replacement()
    test_case_2_unlabeled_first_page_title_detection()
    test_case_3_gemini_alternative_title_ignored()
    test_case_4_long_project_title_wrapping()
    test_case_5_small_content_area()
    test_case_6_large_content_area()
    test_case_7_different_page_sizes_and_orientations()
    test_case_8_search_query_cannot_override_saved_project_title_case_1()
    test_case_9_search_query_cannot_override_saved_project_title_case_2()
    test_case_10_backend_safety_check_prevents_override()
    test_case_11_iterative_fit_underflow_extension()
    test_case_12_master_template_fit_and_page_audit()
    print("\n==============================================")
    print("ALL 12 TEST CASES PASSED WITH 100% SUCCESS!")
    print("==============================================")

