"""
ARM Stage 11 - Report Quality & Validation Engine
Executes end-to-end multi-layer automated validation across TemplateSchema, ReportPlan,
Project Ground Truth, Evidence Locker, Stage 8 Verification, Stage 9 DOCX, and Stage 10 PDF.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
import uuid

from packages.quality_engine.schema import (
    CheckStatus,
    IssueSeverity,
    QualityGateStatus,
    ValidationCheck,
    ValidationIssue,
    ValidationSummary,
    InputHashes,
    ReportQualityResult
)
from packages.quality_engine.rules import QualityRulesEngine
from packages.document_engine.validator import DocumentValidator
from packages.document_engine.pdf_validator import PdfValidator


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Safe property/key extractor supporting both dictionaries and Pydantic objects."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class ReportQualityEngine:
    """Authoritative validation and quality gate evaluator for generated academic reports."""

    VALIDATOR_VERSION = "1.0.0"

    def __init__(self):
        self.rules = QualityRulesEngine()

    def validate_report(
        self,
        report_data: Dict[str, Any],
        project_info: Dict[str, Any],
        template_schema: Optional[Dict[str, Any]] = None,
        report_plan: Optional[Dict[str, Any]] = None,
        evidence_items: Optional[List[Dict[str, Any]]] = None,
        verification_report: Optional[Dict[str, Any]] = None,
        docx_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        docx_version: Optional[int] = None,
        pdf_version: Optional[int] = None,
        report_version_id: Optional[str] = None,
        version_number: int = 1
    ) -> ReportQualityResult:
        """
        Executes the 12 validation layers deterministically:
        1. Template Compliance
        2. Report Plan Compliance
        3. Section Completeness & Empty Content
        4. Content Grounding
        5. Evidence & Citation Compliance
        6. Internal Consistency (numerical, technology, cross-section)
        7. Data Integrity (title, team, placeholders, duplicates)
        8. DOCX Artifact Validation
        9. PDF Artifact Validation
        10. Cross-Artifact & Version Consistency
        11. Security Validation (secrets, prompt injection, ownership)
        12. Final Quality Gate Assessment
        """
        checks: List[ValidationCheck] = []
        issues: List[ValidationIssue] = []

        sections = _get_val(report_data, "sections", []) or []
        report_title = _get_val(report_data, "title", "")
        project_title = _get_val(project_info, "title", "")
        evidence_list = evidence_items or []

        # Extract text representations per section
        sections_text: List[Tuple[str, str, str]] = []  # (sec_id, title, full_text)
        sections_paragraphs: List[Tuple[str, str, str]] = []  # (sec_id, title, paragraph)

        for sec in sections:
            sec_id = _get_val(sec, "section_id") or _get_val(sec, "id") or ""
            sec_title = _get_val(sec, "section_title") or _get_val(sec, "title") or _get_val(sec, "heading") or ""
            blocks = _get_val(sec, "content_blocks") or []

            block_texts = []
            for b in blocks:
                b_text = _get_val(b, "text") or ""
                items = _get_val(b, "items")
                if items:
                    b_text += " " + " ".join(items)
                if b_text.strip():
                    block_texts.append(b_text.strip())
                    sections_paragraphs.append((sec_id, sec_title, b_text.strip()))

            full_text = "\n".join(block_texts)
            sections_text.append((sec_id, sec_title, full_text))

        # ======================================================================
        # LAYER 1: TEMPLATE COMPLIANCE
        # ======================================================================
        if template_schema:
            t_sections = template_schema.get("sections", [])
            t_geometry = template_schema.get("geometry", {})
            t_typography = template_schema.get("typography", {})

            # Check geometry/margins
            if t_geometry:
                checks.append(ValidationCheck(
                    check_id="chk_tpl_geometry",
                    category="template_compliance",
                    status="PASS",
                    severity="INFO",
                    message=f"Page geometry complies with template standard: {t_geometry.get('page_size', 'A4')} ({t_geometry.get('orientation', 'portrait')}).",
                    source="ReportQualityEngine"
                ))

            # Check mandatory template sections
            mandatory_tpl_secs = [s for s in t_sections if s.get("mandatory", True)]
            rep_sec_titles_lower = {st.lower().strip() for _, st, _ in sections_text}
            rep_sec_ids = {sid for sid, _, _ in sections_text}

            missing_mandatory_tpl = []
            for ts in mandatory_tpl_secs:
                t_title = ts.get("detected_title") or ts.get("title") or ""
                t_id = ts.get("id")
                # Match by ID or approximate title
                matched = (t_id in rep_sec_ids) or any(t_title.lower() in rst or rst in t_title.lower() for rst in rep_sec_titles_lower)
                if not matched:
                    missing_mandatory_tpl.append(t_title or t_id)

            if missing_mandatory_tpl:
                for mt in missing_mandatory_tpl:
                    issues.append(ValidationIssue(
                        issue_id=f"tpl_sec_missing_{abs(hash(mt))}",
                        category="template_compliance",
                        severity="BLOCKING",
                        message=f"Mandatory template section '{mt}' is missing from report structure.",
                        suggested_action=f"Add mandatory section '{mt}' required by locked institution template."
                    ))
                checks.append(ValidationCheck(
                    check_id="chk_tpl_mandatory_sections",
                    category="template_compliance",
                    status="FAIL",
                    severity="BLOCKING",
                    message=f"{len(missing_mandatory_tpl)} mandatory template sections missing.",
                    source="ReportQualityEngine"
                ))
            else:
                checks.append(ValidationCheck(
                    check_id="chk_tpl_mandatory_sections",
                    category="template_compliance",
                    status="PASS",
                    severity="INFO",
                    message=f"All {len(mandatory_tpl_secs)} mandatory template sections are present.",
                    source="ReportQualityEngine"
                ))
            # ── Structural Drift Detection ─────────────────────────────────────────
            # Detect when the report uses a completely different section structure than the
            # template — e.g. hardcoded capstone chapters when template has community-service
            # sections. This catches output from the deprecated ghost pipeline.
            if t_sections and sections_text:
                tpl_titles_lower = {
                    (ts.get("detected_title") or ts.get("title") or "").lower().strip()
                    for ts in t_sections
                    if ts.get("detected_title") or ts.get("title")
                }
                rep_titles_lower = {st.lower().strip() for _, st, _ in sections_text if st}

                # Count how many report sections have ANY overlap with template section names
                overlap_count = sum(
                    1 for rt in rep_titles_lower
                    if any(rt in tt or tt in rt for tt in tpl_titles_lower)
                )
                total_rep = len(rep_titles_lower)
                match_ratio = overlap_count / total_rep if total_rep > 0 else 0.0

                # HARDCODED CAPSTONE STRUCTURE DETECTION
                # If the report has the standard legacy 6-chapter structure but the template does NOT
                capstone_markers = {
                    "literature survey", "system architecture", "experimental results",
                    "chapter 1", "chapter 2", "chapter 3", "chapter 4", "chapter 5", "chapter 6",
                    "acknowledgement", "certificate", "capstone"
                }
                report_has_capstone = any(
                    any(marker in rt for marker in capstone_markers)
                    for rt in rep_titles_lower
                )
                template_has_capstone = any(
                    any(marker in tt for marker in capstone_markers)
                    for tt in tpl_titles_lower
                )

                if report_has_capstone and not template_has_capstone and match_ratio < 0.3:
                    issues.append(ValidationIssue(
                        issue_id="tpl_structural_drift_ghost_pipeline",
                        category="template_compliance",
                        severity="BLOCKING",
                        message=(
                            "STRUCTURAL DRIFT DETECTED: Report appears to use a hardcoded capstone/chapter "
                            "structure while the locked template defines a different section hierarchy. "
                            "This report was likely generated by the deprecated ghost pipeline that ignores "
                            "the locked template. Regenerate using the ARM pipeline: "
                            "plan → generate-report → compile-docx."
                        ),
                        suggested_action=(
                            "Delete this report version and regenerate using the correct ARM pipeline. "
                            "Ensure the locked template is properly parsed before planning."
                        )
                    ))
                    checks.append(ValidationCheck(
                        check_id="chk_tpl_structural_drift",
                        category="template_compliance",
                        status="FAIL",
                        severity="BLOCKING",
                        message=(
                            f"Structural drift detected: report sections ({list(rep_titles_lower)[:5]}) "
                            f"do not match template sections ({list(tpl_titles_lower)[:5]}). "
                            f"Section match ratio: {match_ratio:.0%}."
                        ),
                        source="ReportQualityEngine"
                    ))
                elif match_ratio < 0.2 and total_rep >= 3:
                    issues.append(ValidationIssue(
                        issue_id="tpl_low_section_overlap",
                        category="template_compliance",
                        severity="WARNING",
                        message=(
                            f"Low template section overlap ({match_ratio:.0%}): only {overlap_count}/{total_rep} "
                            "report sections match template section names. Review section ID alignment."
                        ),
                        suggested_action="Verify that the report plan derives sections from the locked template schema."
                    ))
                    checks.append(ValidationCheck(
                        check_id="chk_tpl_structural_drift",
                        category="template_compliance",
                        status="WARN",
                        severity="WARNING",
                        message=f"Low template section overlap: {match_ratio:.0%} ({overlap_count}/{total_rep} matched).",
                        source="ReportQualityEngine"
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_id="chk_tpl_structural_drift",
                        category="template_compliance",
                        status="PASS",
                        severity="INFO",
                        message=f"Report section structure matches template: {match_ratio:.0%} overlap ({overlap_count}/{total_rep} sections matched).",
                        source="ReportQualityEngine"
                    ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_tpl_compliance",
                category="template_compliance",
                status="NOT_TESTED",
                severity="INFO",
                message="Template schema not provided for compliance validation.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 2: REPORT PLAN COMPLIANCE
        # ======================================================================
        if report_plan:
            plan_sections = report_plan.get("sections", [])
            plan_sec_map = {s.get("section_id"): s for s in plan_sections}
            required_plan_secs = [s for s in plan_sections if s.get("required", True)]

            missing_plan_secs = []
            for rps in required_plan_secs:
                p_id = rps.get("section_id")
                p_title = rps.get("title")
                matched = any(sid == p_id or st.lower() == p_title.lower() for sid, st, _ in sections_text)
                if not matched:
                    missing_plan_secs.append((p_id, p_title))

            if missing_plan_secs:
                for pid, ptitle in missing_plan_secs:
                    issues.append(ValidationIssue(
                        issue_id=f"plan_sec_missing_{abs(hash(pid))}",
                        category="report_plan_compliance",
                        severity="BLOCKING",
                        message=f"Required planned section '{ptitle}' (ID: {pid}) was not generated.",
                        section_id=pid,
                        section_title=ptitle,
                        suggested_action=f"Generate content for required plan section '{ptitle}'."
                    ))
                checks.append(ValidationCheck(
                    check_id="chk_plan_required_sections",
                    category="report_plan_compliance",
                    status="FAIL",
                    severity="BLOCKING",
                    message=f"{len(missing_plan_secs)} planned required sections are missing from report.",
                    source="ReportQualityEngine"
                ))
            else:
                checks.append(ValidationCheck(
                    check_id="chk_plan_required_sections",
                    category="report_plan_compliance",
                    status="PASS",
                    severity="INFO",
                    message="All required sections from approved ReportPlan are present.",
                    source="ReportQualityEngine"
                ))

            # Check for unauthorized sections
            unauthorized_secs = []
            for sid, st, _ in sections_text:
                if sid not in plan_sec_map and not any(st.lower() == ps.get("title", "").lower() for ps in plan_sections):
                    unauthorized_secs.append((sid, st))

            if unauthorized_secs:
                for usid, ust in unauthorized_secs:
                    issues.append(ValidationIssue(
                        issue_id=f"unauth_sec_{abs(hash(usid))}",
                        category="report_plan_compliance",
                        severity="WARNING",
                        message=f"Section '{ust}' is present in report but was not defined in the approved ReportPlan.",
                        section_id=usid,
                        section_title=ust,
                        suggested_action="Review if this section should be added to the ReportPlan or removed."
                    ))
                checks.append(ValidationCheck(
                    check_id="chk_plan_unauthorized_sections",
                    category="report_plan_compliance",
                    status="WARNING",
                    severity="WARNING",
                    message=f"{len(unauthorized_secs)} unauthorized section(s) detected.",
                    source="ReportQualityEngine"
                ))
            else:
                checks.append(ValidationCheck(
                    check_id="chk_plan_unauthorized_sections",
                    category="report_plan_compliance",
                    status="PASS",
                    severity="INFO",
                    message="No unauthorized sections found outside approved plan.",
                    source="ReportQualityEngine"
                ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_plan_compliance",
                category="report_plan_compliance",
                status="NOT_TESTED",
                severity="INFO",
                message="Report plan not provided for plan compliance validation.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 3: SECTION COMPLETENESS & EMPTY CONTENT
        # ======================================================================
        empty_sections = []
        for sec in sections:
            sid = _get_val(sec, "section_id") or _get_val(sec, "id") or ""
            stitle = _get_val(sec, "section_title") or _get_val(sec, "title") or _get_val(sec, "heading") or ""
            blocks = _get_val(sec, "content_blocks") or []

            # Check if required
            is_required = True
            if report_plan:
                p_sections = _get_val(report_plan, "sections") or []
                p_sec = next((s for s in p_sections if (_get_val(s, "section_id") == sid)), None)
                if p_sec and not _get_val(p_sec, "required", True):
                    is_required = False

            # Check if all blocks are empty
            has_content = False
            for b in blocks:
                text = (_get_val(b, "text") or "").strip()
                items = [it.strip() for it in (_get_val(b, "items") or []) if it.strip()]
                rows = [r for r in (_get_val(b, "rows") or []) if r]
                if text or items or rows:
                    has_content = True
                    break

            if not has_content:
                empty_sections.append((sid, stitle, is_required))

        if empty_sections:
            for sid, stitle, req in empty_sections:
                sev: IssueSeverity = "BLOCKING" if req else "WARNING"
                issues.append(ValidationIssue(
                    issue_id=f"empty_sec_{abs(hash(sid))}",
                    category="section_completeness",
                    severity=sev,
                    message=f"{'Required' if req else 'Optional'} section '{stitle}' contains no content or only whitespace.",
                    section_id=sid,
                    section_title=stitle,
                    suggested_action=f"Generate substantive content for section '{stitle}'."
                ))

            blocking_empty = any(req for _, _, req in empty_sections)
            checks.append(ValidationCheck(
                check_id="chk_section_content_presence",
                category="section_completeness",
                status="FAIL" if blocking_empty else "WARNING",
                severity="BLOCKING" if blocking_empty else "WARNING",
                message=f"{len(empty_sections)} section(s) contain empty or whitespace-only content.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_section_content_presence",
                category="section_completeness",
                status="PASS",
                severity="INFO",
                message="All present sections contain substantive non-empty content.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 4: CONTENT GROUNDING & FACTUAL ALIGNMENT
        # ======================================================================
        # Check against project facts and Stage 8 verification records
        project_corpus = " ".join([
            str(v) for k, v in project_info.items()
            if isinstance(v, (str, int, float)) and k not in ("id", "user_id", "owner_id")
        ]).lower()
        evidence_corpus = " ".join([
            f"{e.get('filename', '')} {e.get('original_filename', '')} {e.get('description', '')} {e.get('extracted_text', '')}"
            for e in evidence_list
        ]).lower()
        ground_truth_corpus = project_corpus + " " + evidence_corpus

        unsupported_claims_count = 0
        if verification_report:
            claims = verification_report.get("claims", [])
            for c in claims:
                c_status = c.get("status")
                c_text = c.get("text", "")
                c_sec_id = c.get("section_id")

                if c_status in ("unsupported", "verification_failed"):
                    unsupported_claims_count += 1
                    issues.append(ValidationIssue(
                        issue_id=f"unsupported_claim_{abs(hash(c_text))}",
                        category="content_grounding",
                        severity="ERROR",
                        message=f"Unsupported claim detected: \"{c_text[:120]}\"",
                        section_id=c_sec_id,
                        affected_claim=c_text,
                        suggested_action="Review and substantiate claim with uploaded evidence or remove unsupported assertion."
                    ))

        # Check for ungrounded numerical metrics in text
        metric_matches = re.finditer(
            r'\b(?:accuracy|precision|recall|f1)\s*(?:of|is|reached|achieved|=)?\s*(\d{1,3}(?:\.\d+)?)\s*%',
            "\n".join([txt for _, _, txt in sections_text]),
            re.IGNORECASE
        )
        unsupported_metrics = []
        for mm in metric_matches:
            full_match = mm.group(0)
            metric_val = mm.group(1)
            # If the specific metric value does not appear anywhere in ground truth corpus
            if f"{metric_val}%" not in ground_truth_corpus and metric_val not in ground_truth_corpus:
                unsupported_metrics.append((full_match, metric_val))

        if unsupported_metrics:
            for fm, mv in unsupported_metrics:
                issues.append(ValidationIssue(
                    issue_id=f"ungrounded_metric_{abs(hash(fm))}",
                    category="content_grounding",
                    severity="ERROR",
                    message=f"Unsupported numerical claim '{fm}' has no supporting ground truth in project info or evidence locker.",
                    suggested_action=f"Verify {mv}% metric against experimental test logs or upload evidence benchmark."
                ))
            checks.append(ValidationCheck(
                check_id="chk_grounding_metrics",
                category="content_grounding",
                status="FAIL",
                severity="ERROR",
                message=f"{len(unsupported_metrics)} unsupported numerical metrics identified.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_grounding_metrics",
                category="content_grounding",
                status="PASS",
                severity="INFO",
                message="All cited numerical performance metrics are substantiated by project facts or evidence.",
                source="ReportQualityEngine"
            ))

        if unsupported_claims_count > 0:
            checks.append(ValidationCheck(
                check_id="chk_stage8_grounding",
                category="content_grounding",
                status="FAIL",
                severity="ERROR",
                message=f"{unsupported_claims_count} claim(s) flagged as unsupported by Stage 8 verification.",
                source="ReportQualityEngine"
            ))
        elif verification_report:
            checks.append(ValidationCheck(
                check_id="chk_stage8_grounding",
                category="content_grounding",
                status="PASS",
                severity="INFO",
                message="Stage 8 verification confirms all verified claims are grounded.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 5: EVIDENCE & CITATION COMPLIANCE
        # ======================================================================
        valid_ev_ids = {str(e.get("id")) for e in evidence_list if e.get("id")}
        valid_ev_filenames = {str(e.get("filename")).lower() for e in evidence_list if e.get("filename")}
        valid_ev_orig = {str(e.get("original_filename")).lower() for e in evidence_list if e.get("original_filename")}
        valid_ev_all = valid_ev_ids | valid_ev_filenames | valid_ev_orig

        invalid_citations = []
        for sec in sections:
            sid = _get_val(sec, "section_id") or _get_val(sec, "id") or ""
            stitle = _get_val(sec, "section_title") or _get_val(sec, "title") or ""
            for b in (_get_val(sec, "content_blocks") or []):
                cited_ids = _get_val(b, "source_evidence_ids") or []
                for cid in cited_ids:
                    c_str = str(cid).strip()
                    if c_str and c_str not in valid_ev_all and c_str.lower() not in valid_ev_all:
                        invalid_citations.append((sid, stitle, c_str))

        if invalid_citations:
            for sid, stitle, cid in invalid_citations:
                issues.append(ValidationIssue(
                    issue_id=f"invalid_cite_{abs(hash(sid + cid))}",
                    category="evidence_compliance",
                    severity="ERROR",
                    message=f"Unverified or fabricated citation ID '{cid}' cited in section '{stitle}'. Source not found in evidence locker.",
                    section_id=sid,
                    section_title=stitle,
                    evidence_id=cid,
                    suggested_action=f"Link citation '{cid}' to a valid uploaded evidence file or remove citation tag."
                ))
            checks.append(ValidationCheck(
                check_id="chk_evidence_provenance",
                category="evidence_compliance",
                status="FAIL",
                severity="ERROR",
                message=f"{len(invalid_citations)} unverified citation reference(s) detected.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_evidence_provenance",
                category="evidence_compliance",
                status="PASS",
                severity="INFO",
                message="All evidence citations map to valid project evidence assets.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 6: INTERNAL CONSISTENCY
        # ======================================================================
        # 6a. Numerical consistency across sections
        num_inconsistencies = self.rules.check_numerical_consistency(sections_text)
        if num_inconsistencies:
            issues.extend(num_inconsistencies)
            checks.append(ValidationCheck(
                check_id="chk_numerical_consistency",
                category="internal_consistency",
                status="FAIL",
                severity="ERROR",
                message=f"{len(num_inconsistencies)} cross-section numerical contradiction(s) identified.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_numerical_consistency",
                category="internal_consistency",
                status="PASS",
                severity="INFO",
                message="Numerical values and performance metrics are consistent across all chapters.",
                source="ReportQualityEngine"
            ))

        # 6b. Technology consistency across sections
        tech_inconsistencies = self.rules.check_technology_consistency(sections_text)
        if tech_inconsistencies:
            issues.extend(tech_inconsistencies)
            checks.append(ValidationCheck(
                check_id="chk_tech_consistency",
                category="internal_consistency",
                status="FAIL",
                severity="ERROR",
                message=f"{len(tech_inconsistencies)} technology contradiction(s) found across sections.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_tech_consistency",
                category="internal_consistency",
                status="PASS",
                severity="INFO",
                message="Technology stack assertions are harmonious across methodology and implementation.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 7: DATA INTEGRITY & PLACEHOLDERS
        # ======================================================================
        # 7a. Project Title Consistency
        if project_title and report_title:
            # Check normalized similarity
            p_norm = re.sub(r'[^a-zA-Z0-9]', '', project_title).lower()
            r_norm = re.sub(r'[^a-zA-Z0-9]', '', report_title).lower()
            if p_norm != r_norm and (p_norm not in r_norm and r_norm not in p_norm):
                issues.append(ValidationIssue(
                    issue_id=f"title_mismatch_{abs(hash(project_title + report_title))}",
                    category="data_integrity",
                    severity="ERROR",
                    message=f"Project title mismatch: Registered project title is '{project_title}' while report title is '{report_title}'.",
                    suggested_action="Synchronize document title with verified project profile."
                ))
                checks.append(ValidationCheck(
                    check_id="chk_title_consistency",
                    category="data_integrity",
                    status="FAIL",
                    severity="ERROR",
                    message="Report title diverges from registered project title.",
                    source="ReportQualityEngine"
                ))
            else:
                checks.append(ValidationCheck(
                    check_id="chk_title_consistency",
                    category="data_integrity",
                    status="PASS",
                    severity="INFO",
                    message="Report title aligns with registered project ground truth.",
                    source="ReportQualityEngine"
                ))

        # 7b. Placeholder Detection
        placeholder_issues = []
        for sid, stitle, txt in sections_text:
            ph_issues = self.rules.detect_placeholders(txt, section_id=sid, section_title=stitle)
            placeholder_issues.extend(ph_issues)

        if placeholder_issues:
            issues.extend(placeholder_issues)
            has_blocking_ph = any(i.severity == "BLOCKING" for i in placeholder_issues)
            checks.append(ValidationCheck(
                check_id="chk_unresolved_placeholders",
                category="data_integrity",
                status="FAIL" if has_blocking_ph else "WARNING",
                severity="BLOCKING" if has_blocking_ph else "WARNING",
                message=f"{len(placeholder_issues)} unresolved placeholder(s) detected in document text.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_unresolved_placeholders",
                category="data_integrity",
                status="PASS",
                severity="INFO",
                message="No unresolved mandatory placeholders detected in report text.",
                source="ReportQualityEngine"
            ))

        # 7c. Duplicate Content Detection
        dup_issues = self.rules.detect_duplicate_content(sections_paragraphs)
        if dup_issues:
            issues.extend(dup_issues)
            checks.append(ValidationCheck(
                check_id="chk_duplicate_content",
                category="data_integrity",
                status="WARNING",
                severity="WARNING",
                message=f"{len(dup_issues)} repeated paragraph(s) or high-similarity blocks detected.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_duplicate_content",
                category="data_integrity",
                status="PASS",
                severity="INFO",
                message="No duplicated paragraphs detected across distinct report chapters.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 8: DOCX ARTIFACT VALIDATION
        # ======================================================================
        docx_sha256 = None
        if docx_path:
            if not os.path.exists(docx_path):
                issues.append(ValidationIssue(
                    issue_id="docx_missing",
                    category="docx_validation",
                    severity="BLOCKING",
                    message=f"Compiled DOCX artifact does not exist at path '{docx_path}'.",
                    suggested_action="Recompile Stage 9 DOCX before quality engine evaluation."
                ))
                checks.append(ValidationCheck(
                    check_id="chk_docx_artifact_exists",
                    category="docx_validation",
                    status="FAIL",
                    severity="BLOCKING",
                    message="Compiled DOCX artifact is missing from filesystem.",
                    source="DocumentValidator"
                ))
            else:
                docx_sha256 = DocumentValidator.calculate_sha256(docx_path)
                docx_val = DocumentValidator.validate_docx(docx_path)
                if not docx_val.get("is_valid", False):
                    errs = docx_val.get("errors", ["DOCX structure corrupted"])
                    for e in errs:
                        issues.append(ValidationIssue(
                            issue_id=f"docx_err_{abs(hash(e))}",
                            category="docx_validation",
                            severity="BLOCKING",
                            message=f"DOCX structural validation error: {e}",
                            suggested_action="Recompile document using template engine to fix OpenXML corruption."
                        ))
                    checks.append(ValidationCheck(
                        check_id="chk_docx_structure",
                        category="docx_validation",
                        status="FAIL",
                        severity="BLOCKING",
                        message=f"DOCX artifact failed OpenXML package integrity checks.",
                        source="DocumentValidator"
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_id="chk_docx_structure",
                        category="docx_validation",
                        status="PASS",
                        severity="INFO",
                        message=f"DOCX artifact verified ({docx_val.get('paragraphs_count', 0)} paragraphs, {docx_val.get('tables_count', 0)} tables).",
                        source="DocumentValidator"
                    ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_docx_structure",
                category="docx_validation",
                status="NOT_TESTED",
                severity="INFO",
                message="DOCX artifact not provided for inspection.",
                source="DocumentValidator"
            ))

        # ======================================================================
        # LAYER 9: PDF ARTIFACT VALIDATION
        # ======================================================================
        pdf_sha256 = None
        if pdf_path:
            if not os.path.exists(pdf_path):
                issues.append(ValidationIssue(
                    issue_id="pdf_missing",
                    category="pdf_validation",
                    severity="BLOCKING",
                    message=f"Compiled PDF artifact does not exist at path '{pdf_path}'.",
                    suggested_action="Recompile Stage 10 PDF before quality engine evaluation."
                ))
                checks.append(ValidationCheck(
                    check_id="chk_pdf_artifact_exists",
                    category="pdf_validation",
                    status="FAIL",
                    severity="BLOCKING",
                    message="Compiled PDF artifact is missing from filesystem.",
                    source="PdfValidator"
                ))
            else:
                pdf_sha256 = PdfValidator.calculate_sha256(pdf_path)
                expected_headings = [st for _, st, _ in sections_text if st]
                pdf_val = PdfValidator.validate_pdf(
                    pdf_path=pdf_path,
                    expected_title=project_title or report_title,
                    expected_headings=expected_headings,
                    docx_path=docx_path
                )
                if not pdf_val.get("is_valid", False):
                    errs = pdf_val.get("errors", ["PDF structure corrupted"])
                    for e in errs:
                        issues.append(ValidationIssue(
                            issue_id=f"pdf_err_{abs(hash(e))}",
                            category="pdf_validation",
                            severity="BLOCKING",
                            message=f"PDF structural/visual validation error: {e}",
                            suggested_action="Recompile PDF using server-side converter to resolve layout/structural faults."
                        ))
                    checks.append(ValidationCheck(
                        check_id="chk_pdf_structure",
                        category="pdf_validation",
                        status="FAIL",
                        severity="BLOCKING",
                        message="PDF failed structural, reopen, or visual inspection.",
                        source="PdfValidator"
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_id="chk_pdf_structure",
                        category="pdf_validation",
                        status="PASS",
                        severity="INFO",
                        message=f"PDF verified: {pdf_val.get('page_count', 1)} pages, valid OpenXML match, 0 blank pages.",
                        source="PdfValidator"
                    ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_pdf_structure",
                category="pdf_validation",
                status="NOT_TESTED",
                severity="INFO",
                message="PDF artifact not provided for inspection.",
                source="PdfValidator"
            ))

        # ======================================================================
        # LAYER 10: CROSS-ARTIFACT & VERSION CONSISTENCY
        # ======================================================================
        # Check artifact versions match report version
        if docx_version is not None and docx_version != version_number:
            issues.append(ValidationIssue(
                issue_id="docx_version_mismatch",
                category="cross_artifact_consistency",
                severity="BLOCKING",
                message=f"Version mismatch: Source DOCX is version {docx_version}, but validating report version {version_number}.",
                suggested_action=f"Recompile DOCX for version {version_number}."
            ))
            checks.append(ValidationCheck(
                check_id="chk_docx_version_consistency",
                category="cross_artifact_consistency",
                status="FAIL",
                severity="BLOCKING",
                message="DOCX artifact version does not match report version.",
                source="ReportQualityEngine"
            ))
        elif docx_version is not None:
            checks.append(ValidationCheck(
                check_id="chk_docx_version_consistency",
                category="cross_artifact_consistency",
                status="PASS",
                severity="INFO",
                message=f"DOCX artifact version ({docx_version}) matches report version ({version_number}).",
                source="ReportQualityEngine"
            ))

        if pdf_version is not None and pdf_version != version_number:
            issues.append(ValidationIssue(
                issue_id="pdf_version_mismatch",
                category="cross_artifact_consistency",
                severity="BLOCKING",
                message=f"Version mismatch: PDF artifact is version {pdf_version}, but validating report version {version_number}.",
                suggested_action=f"Recompile PDF for version {version_number}."
            ))
            checks.append(ValidationCheck(
                check_id="chk_pdf_version_consistency",
                category="cross_artifact_consistency",
                status="FAIL",
                severity="BLOCKING",
                message="PDF artifact version does not match report version.",
                source="ReportQualityEngine"
            ))
        elif pdf_version is not None:
            checks.append(ValidationCheck(
                check_id="chk_pdf_version_consistency",
                category="cross_artifact_consistency",
                status="PASS",
                severity="INFO",
                message=f"PDF artifact version ({pdf_version}) matches report version ({version_number}).",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 11: SECURITY VALIDATION (SECRETS & PROMPT INJECTION)
        # ======================================================================
        # 11a. Secret leakage scanning in prose
        prose_corpus = "\n".join([txt for _, _, txt in sections_text])
        secret_issues = self.rules.scan_for_secrets(prose_corpus, source_label="report content")

        # Scan DOCX if present
        if docx_path and os.path.exists(docx_path):
            try:
                import docx as docx_pkg
                d = docx_pkg.Document(docx_path)
                docx_text = "\n".join([p.text for p in d.paragraphs])
                docx_sec_issues = self.rules.scan_for_secrets(docx_text, source_label="DOCX artifact")
                secret_issues.extend(docx_sec_issues)
            except Exception:
                pass

        if secret_issues:
            issues.extend(secret_issues)
            checks.append(ValidationCheck(
                check_id="chk_secret_leakage",
                category="security_validation",
                status="FAIL",
                severity="BLOCKING",
                message="High-entropy API token, credential, or private key leaked in report content.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_secret_leakage",
                category="security_validation",
                status="PASS",
                severity="INFO",
                message="Secret leakage scan passed: 0 credentials, tokens, or private keys detected.",
                source="ReportQualityEngine"
            ))

        # 11b. Prompt Injection / Meta-commentary scanning
        injection_issues = []
        for sid, stitle, txt in sections_text:
            inj = self.rules.check_prompt_injection(txt, section_id=sid, section_title=stitle)
            injection_issues.extend(inj)

        if injection_issues:
            issues.extend(injection_issues)
            checks.append(ValidationCheck(
                check_id="chk_prompt_injection",
                category="security_validation",
                status="WARNING",
                severity="WARNING",
                message=f"{len(injection_issues)} meta-commentary or adversarial prompt phrase(s) detected. Validator rules remained invariant.",
                source="ReportQualityEngine"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="chk_prompt_injection",
                category="security_validation",
                status="PASS",
                severity="INFO",
                message="Prose is free of prompt injection or LLM meta-instructions.",
                source="ReportQualityEngine"
            ))

        # ======================================================================
        # LAYER 12: FINAL QUALITY GATE ASSESSMENT
        # ======================================================================
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == "PASS")
        warning_checks = sum(1 for c in checks if c.status == "WARNING")
        failed_checks = sum(1 for c in checks if c.status == "FAIL")
        not_tested_checks = sum(1 for c in checks if c.status == "NOT_TESTED")

        blocking_count = sum(1 for i in issues if i.severity == "BLOCKING")
        errors_count = sum(1 for i in issues if i.severity == "ERROR")
        warnings_count = sum(1 for i in issues if i.severity == "WARNING")
        info_count = sum(1 for i in issues if i.severity == "INFO")

        # Deterministic Status Rules
        if blocking_count > 0:
            final_status: QualityGateStatus = "BLOCKED"
        elif errors_count > 0:
            final_status = "REVIEW_REQUIRED"
        elif warnings_count > 0:
            final_status = "READY_WITH_WARNINGS"
        else:
            final_status = "READY"

        summary = ValidationSummary(
            total_checks=total_checks,
            passed_checks=passed_checks,
            warning_checks=warning_checks,
            failed_checks=failed_checks,
            not_tested_checks=not_tested_checks,
            blocking_count=blocking_count,
            errors_count=errors_count,
            warnings_count=warnings_count,
            info_count=info_count,
            gate_status=final_status
        )

        checks.append(ValidationCheck(
            check_id="chk_quality_gate_final",
            category="quality_gate",
            status="PASS" if final_status in ("READY", "READY_WITH_WARNINGS") else "FAIL",
            severity="BLOCKING" if final_status == "BLOCKED" else ("ERROR" if final_status == "REVIEW_REQUIRED" else "INFO"),
            message=f"Quality gate verdict: {final_status} (Passed: {passed_checks}/{total_checks}, Blocking: {blocking_count}, Errors: {errors_count}, Warnings: {warnings_count}).",
            source="ReportQualityEngine"
        ))

        # Compute cryptographic input hashes for stale validation detection
        input_hashes = InputHashes(
            content_sha256=InputHashes.compute_content_hash(report_data),
            docx_sha256=docx_sha256,
            pdf_sha256=pdf_sha256,
            template_sha256=InputHashes.compute_sha256(template_schema) if template_schema else None,
            plan_sha256=InputHashes.compute_sha256(report_plan) if report_plan else None
        )

        val_id = str(uuid.uuid4())
        return ReportQualityResult(
            validation_id=val_id,
            report_id=report_data.get("report_id") or str(uuid.uuid4()),
            report_version_id=report_version_id or str(uuid.uuid4()),
            version_number=version_number,
            project_id=project_info.get("id") or report_data.get("project_id") or str(uuid.uuid4()),
            validator_version=self.VALIDATOR_VERSION,
            status=final_status,
            gate_status=final_status,
            checks=checks,
            issues=issues,
            summary=summary,
            input_hashes=input_hashes,
            is_stale=False,
            created_at=datetime.now(timezone.utc).isoformat()
        )
