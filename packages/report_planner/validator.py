"""
ARM Stage 6 - Deterministic Report Plan Validator
Authoritative validation engine enforcing template constraints, hierarchy integrity,
project grounding, and evidence mapping bounds.
"""

from typing import Dict, Any, List, Tuple, Set, Optional
from packages.report_planner.schema import ReportPlan, SectionPlanItem, PlanSummaryMetrics


class ReportPlanValidator:
    """Authoritative deterministic validator for Report Plans."""

    @staticmethod
    def validate_plan(
        plan: ReportPlan,
        locked_template_schema: Dict[str, Any],
        project_data: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
    ) -> Tuple[ReportPlan, List[str], List[str]]:
        """
        Validates the planned report structure against locked template constraints,
        project facts, and evidence inventory.

        Returns: (validated_plan, blocking_errors, warnings)
        """
        blocking_errors: List[str] = []
        warnings: List[str] = []

        # 1. Verify Project and Template IDs
        if str(plan.project_id) != str(project_data.get("id")):
            blocking_errors.append(
                f"Plan project_id '{plan.project_id}' does not match target project '{project_data.get('id')}'."
            )

        # 2. Extract Template Sections from Locked Schema
        template_sections = locked_template_schema.get("sections") or []
        if not template_sections:
            blocking_errors.append("Locked template schema contains no sections.")
            return plan, blocking_errors, warnings

        # Build template section lookup
        template_map: Dict[str, Dict[str, Any]] = {}
        for idx, sec in enumerate(template_sections):
            sec_id = sec.get("section_id") or sec.get("id") or sec.get("section_key") or f"sec_{idx+1}"
            template_map[str(sec_id)] = {
                **sec,
                "_order": sec.get("order") or sec.get("sequence_order") or (idx + 1),
                "_level": sec.get("level") or 1,
                "_required": sec.get("mandatory", sec.get("required", True)),
                "_title": sec.get("detected_title") or sec.get("title") or sec.get("name") or f"Section {idx+1}",
            }

        # 3. Verify Section Correspondence & Detection of Invented Sections
        plan_section_ids = [s.section_id for s in plan.sections]
        seen_plan_ids: Set[str] = set()

        for s in plan.sections:
            if s.section_id in seen_plan_ids:
                blocking_errors.append(f"Duplicate section_id '{s.section_id}' in plan.")
            seen_plan_ids.add(s.section_id)

            if s.section_id not in template_map:
                # Check if matching by title exists
                matched_by_title = None
                for tid, tsec in template_map.items():
                    if tsec["_title"].strip().lower() == s.title.strip().lower():
                        matched_by_title = tid
                        break
                if matched_by_title:
                    s.section_id = matched_by_title
                else:
                    blocking_errors.append(
                        f"Invented section detected: '{s.title}' (id: '{s.section_id}') is not in the locked college template."
                    )

        # 4. Verify Presence of Mandatory Template Sections
        for tid, tsec in template_map.items():
            if tsec["_required"] and tid not in seen_plan_ids:
                # Check if present by title
                present = any(s.title.strip().lower() == tsec["_title"].strip().lower() for s in plan.sections)
                if not present:
                    blocking_errors.append(
                        f"Mandatory template section missing: '{tsec['_title']}' (id: '{tid}')."
                    )

        # 5. Verify Section Hierarchy & Ordering
        # Order should be monotonic
        last_order = 0
        for s in plan.sections:
            if s.order <= last_order:
                warnings.append(
                    f"Section '{s.title}' order ({s.order}) is not strictly sequential after {last_order}."
                )
            last_order = s.order

        # 6. Verify Evidence References Belong to this Project
        valid_evidence_names = {e.get("file_name") for e in evidence_items if e.get("file_name")}
        valid_evidence_ids = {str(e.get("id")) for e in evidence_items if e.get("id")}
        all_valid_evidence = valid_evidence_names | valid_evidence_ids

        for s in plan.sections:
            sanitized_evidence: List[str] = []
            for ev_ref in s.evidence_references:
                if ev_ref in all_valid_evidence or any(v in ev_ref for v in valid_evidence_names):
                    sanitized_evidence.append(ev_ref)
                else:
                    warnings.append(
                        f"Section '{s.title}' references unverified/foreign evidence '{ev_ref}'."
                    )
            s.evidence_references = sanitized_evidence

        # 7. Check Ground Truth & Deterministic Missing Information Detection
        project_facts_available = {
            "title": bool(project_data.get("title")),
            "description": bool(project_data.get("description")),
            "problem_statement": bool(project_data.get("problem_statement")),
            "objectives": bool(project_data.get("objectives")),
            "scope": bool(project_data.get("scope")),
            "methodology": bool(project_data.get("methodology")),
            "tech_stack": bool(project_data.get("tech_stack")),
            "expected_outcome": bool(project_data.get("expected_outcome")),
            "actual_outcome": bool(project_data.get("actual_outcome")),
            "department": bool(project_data.get("department")),
            "institution": bool(project_data.get("institution")),
            "guide_name": bool(project_data.get("guide_name")),
        }

        # Record missing core project facts in unresolved_items
        for k in ("problem_statement", "objectives", "methodology", "actual_outcome"):
            if not project_facts_available[k]:
                msg = f"Missing core project fact: {k}"
                if msg not in plan.unresolved_items:
                    plan.unresolved_items.append(msg)

        # Deterministic missing facts enrichment
        for s in plan.sections:
            role = (s.semantic_role or "").lower()
            title_lower = s.title.lower()

            # Introduction & Abstract
            if "intro" in title_lower or role == "introduction" or "abstract" in title_lower or role == "abstract":
                if not project_facts_available["problem_statement"]:
                    msg = "Problem statement not defined in project information"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)
                if not project_facts_available["objectives"]:
                    msg = "Project objectives not defined in project information"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)

            # Methodology & Architecture
            if "method" in title_lower or "architecture" in title_lower or role == "methodology":
                if not project_facts_available["methodology"]:
                    msg = "Technical methodology details missing from project information"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)
                if not project_facts_available["tech_stack"]:
                    msg = "Technology stack not specified in project information"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)

            # Results & Analysis
            if "result" in title_lower or "evaluat" in title_lower or role == "results":
                if not project_facts_available["actual_outcome"]:
                    msg = "Actual empirical outcomes not yet recorded in project information"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)
                # Check for evidence in results
                has_result_evidence = any(
                    e.get("category") in ("dataset", "system_output", "results", "screenshots")
                    for e in evidence_items
                )
                if not has_result_evidence:
                    msg = "No supporting benchmark or output evidence deposited in Evidence Locker"
                    if msg not in s.missing_information:
                        s.missing_information.append(msg)

            # Literature Survey / Related Work
            if "literat" in title_lower or "survey" in title_lower or "related" in title_lower or role == "literature_review":
                s.research_required = True
                if not s.research_notes:
                    s.research_notes = "Requires academic literature survey, conference proceedings, and verified citations."

            # Update verification status & confidence based on missing information & research
            if s.missing_information:
                s.verification_status = "MISSING_INFORMATION"
                s.confidence = "LOW" if len(s.missing_information) > 1 else "MEDIUM"
            elif s.research_required:
                s.verification_status = "RESEARCH_REQUIRED"
                s.confidence = "MEDIUM"
            elif s.evidence_references:
                s.verification_status = "READY"
                s.confidence = "HIGH"
            else:
                s.verification_status = "READY"
                s.confidence = "HIGH"

        # 8. Compute Summary Metrics
        ready_count = sum(1 for s in plan.sections if s.verification_status == "READY")
        partial_count = sum(1 for s in plan.sections if s.verification_status == "PARTIALLY_VERIFIED")
        missing_count = sum(1 for s in plan.sections if s.verification_status == "MISSING_INFORMATION")
        research_count = sum(1 for s in plan.sections if s.verification_status == "RESEARCH_REQUIRED")
        total_missing_items = sum(len(s.missing_information) for s in plan.sections)
        total_ev_mappings = sum(len(s.evidence_references) for s in plan.sections)

        overall_conf = "HIGH"
        if missing_count > (len(plan.sections) // 2):
            overall_conf = "LOW"
        elif missing_count > 0 or research_count > 0:
            overall_conf = "MEDIUM"

        plan.summary_metrics = PlanSummaryMetrics(
            total_sections=len(plan.sections),
            ready_sections=ready_count,
            partially_verified_sections=partial_count,
            missing_info_sections=missing_count,
            research_required_sections=research_count,
            total_missing_items=total_missing_items,
            total_evidence_mappings=total_ev_mappings,
            overall_confidence=overall_conf
        )

        return plan, blocking_errors, warnings
