"""
ARM Dynamic Project-Domain Image Generation Regression Test Suite
==================================================================
Verifies:
1. Dynamic Domain Detection across canonical and custom engineering domains.
2. Complete removal of agriculture as universal fallback:
   - Hospital Management System -> Healthcare / Hospital
   - AI Based Cybersecurity Threat Detection -> Cybersecurity / Network Security
   - Online E-Commerce Management System -> E-Commerce / Online Shopping
   - Smart Traffic Management System -> Smart Transportation / Traffic
   - AI Based Attendance Management System -> Education / Attendance
   - AI Based Smart Irrigation System -> Agriculture / Irrigation
3. Hospital Management System NEVER generates agricultural/farming imagery.
4. Slide-Aware prompt compilation combining Domain + Title + Slide Purpose + Slide Heading + Matter.
5. Rejection of inappropriate agricultural clichés in non-agricultural projects.
6. Context isolation across consecutive report jobs (no stale domain bleed).
"""

import pytest
from apps.api.services.gemini_visual_pipeline_service import (
    GeminiVisualPipelineService,
    SlideVisualPurpose,
)

AGRICULTURE_TERMS = [
    "agriculture", "agricultural", "farming", "farmland", "crop", "crops",
    "soil moisture", "drip irrigation", "harvest", "parched soil", "crop rows",
    "irrigation tubing", "furrow"
]


def test_1_dynamic_domain_detection_all_canonical_domains():
    """TEST 1: Domain classifier correctly identifies canonical engineering domains."""
    test_cases = [
        ("AI Based Smart Irrigation System", "irrigation", "Agriculture / Irrigation"),
        ("AI Based Attendance Management System", "attendance", "Education / Attendance"),
        ("Hospital Management System", "healthcare", "Healthcare / Hospital"),
        ("AI Based Cybersecurity Threat Detection System", "cybersecurity", "Cybersecurity / Network Security"),
        ("Online E-Commerce Management System", "ecommerce", "E-Commerce / Online Shopping"),
        ("Smart Traffic Management System", "traffic", "Smart Transportation / Traffic"),
    ]

    for title, expected_domain, expected_label in test_cases:
        domain, label, conf = GeminiVisualPipelineService.detect_project_domain_and_context(
            project_title=title
        )
        assert domain == expected_domain, f"Failed for '{title}': expected {expected_domain}, got {domain}"
        assert label == expected_label, f"Failed label for '{title}': expected {expected_label}, got {label}"
        assert conf >= 0.7, f"Low confidence for '{title}': {conf}"


def test_2_unknown_domain_does_not_fallback_to_agriculture():
    """TEST 2: Completely unknown project domain uses dynamic contextual anchors, NEVER agriculture."""
    unknown_title = "Quantum Annealing Optimization for Satellite Communications"
    domain, label, conf = GeminiVisualPipelineService.detect_project_domain_and_context(
        project_title=unknown_title
    )
    assert domain == "dynamic_general"
    assert "agriculture" not in domain.lower()
    assert "irrigation" not in domain.lower()

    req = GeminiVisualPipelineService.compile_visual_requirement(
        project_title=unknown_title,
        slide_heading="System Architecture",
        slide_matter="Quantum processor connects with ground station telemetry receivers.",
        slide_index=7,
    )

    prompt_lower = req.gemini_prompt.lower()
    for term in AGRICULTURE_TERMS:
        assert term not in prompt_lower, f"Forbidden agriculture term '{term}' found in unknown domain prompt: {prompt_lower}"


def test_3_hospital_management_system_zero_agriculture_across_all_slides():
    """TEST 3: Hospital Management System must NEVER produce agriculture visuals on ANY slide."""
    hospital_title = "Hospital Management System"
    slides = [
        ("Introduction", "Hospital Management System optimizes clinical care and outpatient flow.", SlideVisualPurpose.INTRODUCTION),
        ("Problem Statement", "Paper medical records cause prolonged patient wait times and triage delays.", SlideVisualPurpose.PROBLEM_STATEMENT),
        ("Existing System", "Traditional consultation desks rely on handwritten prescription slips.", SlideVisualPurpose.EXISTING_SYSTEM),
        ("Proposed System", "An integrated cloud electronic health record (EHR) workstation.", SlideVisualPurpose.PROPOSED_SYSTEM),
        ("Vitals & Sensor Monitoring", "Biomedical sensors track heart rate, SPO2, and patient temperature.", SlideVisualPurpose.SOIL_MOISTURE_MONITORING),
        ("AI Clinical Decision Making", "Predictive algorithms evaluate diagnostic risks and triage priority.", SlideVisualPurpose.AI_DECISION_MAKING),
        ("System Architecture", "Multi-tier hospital IT infrastructure connecting wards, pharmacy, and central database.", SlideVisualPurpose.SYSTEM_ARCHITECTURE),
        ("Working Process", "End-to-end clinical workflow: registration, triage, consultation, pharmacy commit.", SlideVisualPurpose.WORKING_PROCESS),
        ("Field Deployment Photos", "Operating hospital ward with clinical staff using mobile EHR tablets.", SlideVisualPurpose.FIELD_DEPLOYMENT),
        ("Results", "Quantitative evaluation showing a 40% reduction in patient wait times.", SlideVisualPurpose.RESULTS),
        ("Future Scope", "Telemedicine integration and autonomous robotic pharmacy dispensing.", SlideVisualPurpose.FUTURE_SCOPE),
        ("Conclusion", "Modern digital hospital workflow empowering medical staff and patient care.", SlideVisualPurpose.CONCLUSION),
    ]

    for idx, (heading, matter, purpose) in enumerate(slides, start=1):
        req = GeminiVisualPipelineService.compile_visual_requirement(
            project_title=hospital_title,
            slide_heading=heading,
            slide_matter=matter,
            slide_index=idx,
        )

        assert req.detected_domain == "healthcare"
        assert req.domain_label == "Healthcare / Hospital"
        assert req.slide_purpose == purpose

        prompt_lower = req.gemini_prompt.lower()
        # Verify strictly NO agriculture terms
        for term in AGRICULTURE_TERMS:
            assert term not in prompt_lower, (
                f"Agriculture term '{term}' leaked into Hospital slide {idx} ('{heading}'):\n{req.gemini_prompt}"
            )

        # Verify healthcare presence
        assert any(h_term in prompt_lower for h_term in ["hospital", "medical", "clinical", "patient", "health"]), (
            f"Expected healthcare context missing from slide {idx} ('{heading}'):\n{req.gemini_prompt}"
        )

        # Automated relevance validation must PASS
        is_valid, reason = GeminiVisualPipelineService.validate_image_relevance(req)
        assert is_valid is True, f"Relevance validation failed for Hospital slide {idx}: {reason}"


def test_4_cybersecurity_system_zero_agriculture_and_soc_context():
    """TEST 4: Cybersecurity Threat Detection produces SOC / network security visuals, NEVER agriculture."""
    cyber_title = "AI Based Cybersecurity Threat Detection System"
    slides = [
        ("Introduction", "Security operations centers monitor network telemetry against intrusions.", SlideVisualPurpose.INTRODUCTION),
        ("Problem Statement", "Sophisticated malware exploits zero-day vulnerabilities in enterprise networks.", SlideVisualPurpose.PROBLEM_STATEMENT),
        ("System Architecture", "Intrusion prevention appliances connect to SIEM analytics server.", SlideVisualPurpose.SYSTEM_ARCHITECTURE),
        ("Field Deployment", "Enterprise datacenter server racks monitored by cyber defense engineers.", SlideVisualPurpose.FIELD_DEPLOYMENT),
    ]

    for idx, (heading, matter, purpose) in enumerate(slides, start=1):
        req = GeminiVisualPipelineService.compile_visual_requirement(
            project_title=cyber_title,
            slide_heading=heading,
            slide_matter=matter,
            slide_index=idx,
        )

        assert req.detected_domain == "cybersecurity"
        prompt_lower = req.gemini_prompt.lower()
        for term in AGRICULTURE_TERMS:
            assert term not in prompt_lower, f"Agriculture term '{term}' leaked into Cybersecurity slide {idx}."

        assert any(c_term in prompt_lower for c_term in ["security", "cyber", "threat", "soc", "network", "datacenter"])


def test_5_ecommerce_system_zero_agriculture_and_retail_context():
    """TEST 5: E-Commerce System produces online shopping / logistics visuals, NEVER agriculture."""
    ecom_title = "Online E-Commerce Management System"
    slides = [
        ("Introduction", "Digital marketplace storefront displaying customer merchandise catalog.", SlideVisualPurpose.INTRODUCTION),
        ("Field Deployment", "Automated order fulfillment center with barcode packaging stations.", SlideVisualPurpose.FIELD_DEPLOYMENT),
    ]

    for idx, (heading, matter, purpose) in enumerate(slides, start=1):
        req = GeminiVisualPipelineService.compile_visual_requirement(
            project_title=ecom_title,
            slide_heading=heading,
            slide_matter=matter,
            slide_index=idx,
        )

        assert req.detected_domain == "ecommerce"
        prompt_lower = req.gemini_prompt.lower()
        for term in AGRICULTURE_TERMS:
            assert term not in prompt_lower, f"Agriculture term '{term}' leaked into E-Commerce slide {idx}."


def test_6_smart_irrigation_and_attendance_preserved():
    """TEST 6: Smart Irrigation and Attendance continue to produce their expected domain visuals."""
    # Irrigation
    req_irr = GeminiVisualPipelineService.compile_visual_requirement(
        project_title="AI Based Smart Irrigation System",
        slide_heading="Field Deployment",
        slide_matter="Pole-mounted solar IoT nodes monitor soil moisture across crop rows.",
        slide_index=9,
    )
    assert req_irr.detected_domain == "irrigation"
    assert "crop" in req_irr.gemini_prompt.lower()
    assert "farm" in req_irr.gemini_prompt.lower()

    # Attendance
    req_att = GeminiVisualPipelineService.compile_visual_requirement(
        project_title="AI Based Attendance Management System",
        slide_heading="Field Deployment",
        slide_matter="Wall-mounted AI camera actively verifies students in university lecture hall.",
        slide_index=9,
    )
    assert req_att.detected_domain == "attendance"
    assert any(w in req_att.gemini_prompt.lower() for w in ["lecture", "classroom", "student", "camera"])
    assert "crop" not in req_att.gemini_prompt.lower()
    assert "farm" not in req_att.gemini_prompt.lower()


def test_7_context_isolation_across_consecutive_runs():
    """TEST 7: Consecutive runs of different projects do not bleed visual context."""
    # Run 1: Irrigation
    req1 = GeminiVisualPipelineService.compile_visual_requirement(
        project_title="AI Based Smart Irrigation System",
        slide_heading="Introduction",
        slide_matter="Agriculture requires smart water conservation in farm crop fields.",
    )
    assert req1.detected_domain == "irrigation"

    # Run 2: Immediately run Hospital
    req2 = GeminiVisualPipelineService.compile_visual_requirement(
        project_title="Hospital Management System",
        slide_heading="Introduction",
        slide_matter="Digital healthcare workflows in hospital wards.",
    )
    assert req2.detected_domain == "healthcare"
    assert "farm" not in req2.gemini_prompt.lower()
    assert "crop" not in req2.gemini_prompt.lower()
    assert "hospital" in req2.gemini_prompt.lower()


def test_8_rejection_of_inappropriate_agriculture_in_healthcare():
    """TEST 8: Rejection safeguard catches and fails if agriculture text is injected into healthcare."""
    req_hosp = GeminiVisualPipelineService.compile_visual_requirement(
        project_title="Hospital Management System",
        slide_heading="System Architecture",
        slide_matter="Hospital server database.",
    )

    # Valid check passes
    valid, _ = GeminiVisualPipelineService.validate_image_relevance(req_hosp)
    assert valid is True

    # Artificially injected agricultural prompt fails validation
    is_valid, reason = GeminiVisualPipelineService.validate_image_relevance(
        req_hosp, generated_prompt_or_text="A sunlit commercial agricultural farm with crop fields"
    )
    assert is_valid is False
    assert "agricultural farm visual" in reason.lower()
