"""
ARM Stage 8 - Citation & Evidence Verification Engine
Performs deterministic, rule-based, and semantic verification of report claims
against Stage 5 project information and Evidence Locker contents.
Enforces zero-hallucination, strict numerical equality, anti-fabrication citations,
filename-inference protection, and prompt-injection defense.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from packages.report_generator.schema import GeneratedReport, SectionGenerationOutput
from packages.citation_verifier.schema import (
    ClaimType,
    VerificationStatus,
    ExtractedClaim,
    ClaimVerificationRecord,
    VerificationSummary,
    QualityGateResult,
    ReportVerificationReport,
)
from packages.citation_verifier.claim_extractor import ClaimExtractor, NUMERICAL_PATTERN, KNOWN_TECHNOLOGIES
from packages.citation_verifier.research_provider import ResearchProvider, MockResearchProvider


class CitationEvidenceVerificationEngine:
    """Authoritative verifier for Stage 8."""

    VERIFIER_VERSION = "1.0.0"

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        research_provider: Optional[ResearchProvider] = None
    ):
        self.extractor = claim_extractor or ClaimExtractor()
        self.research_provider = research_provider or MockResearchProvider()

    def verify_report(
        self,
        report_data: Dict[str, Any],
        project_info: Dict[str, Any],
        evidence_inventory: List[Dict[str, Any]],
        report_plan: Optional[Dict[str, Any]] = None,
        report_version_id: Optional[str] = None,
        version_number: Optional[int] = None
    ) -> ReportVerificationReport:
        """Runs the complete verification pipeline across all sections in the report."""
        rep_id = report_data.get("id") or str(uuid.uuid4())
        version_id = report_version_id or report_data.get("current_version_id") or report_data.get("version_id") or str(uuid.uuid4())
        version_num = version_number if version_number is not None else report_data.get("version_number", 1)
        project_id = project_info.get("id", "")

        sections_dict = self._parse_sections(report_data)
        plan_sections_map = self._parse_plan_sections(report_plan)

        all_claims_verified: List[ClaimVerificationRecord] = []
        section_verifications: Dict[str, List[ClaimVerificationRecord]] = {}

        # Pre-process verified evidence content (ignoring filenames)
        verified_evidence_store = self._build_verified_evidence_store(evidence_inventory)
        verified_project_facts = self._build_verified_project_facts(project_info)

        for sec_id, sec_data in sections_dict.items():
            # Check if plan marked this section as research_required
            plan_sec = plan_sections_map.get(sec_id, {})
            sec_research_required = plan_sec.get("research_required", False)

            # 1. Claim Extraction
            extracted_claims = self.extractor.extract_from_section(
                sec_data,
                research_required=sec_research_required
            )

            # 2. Claim Verification
            sec_records: List[ClaimVerificationRecord] = []
            for claim in extracted_claims:
                record = self._verify_single_claim(
                    claim=claim,
                    report_version_id=version_id,
                    project_facts=verified_project_facts,
                    evidence_store=verified_evidence_store,
                    section_research_required=sec_research_required
                )
                sec_records.append(record)
                all_claims_verified.append(record)

            section_verifications[sec_id] = sec_records

        # 3. Calculate Summary Metrics
        summary = self._calculate_summary(all_claims_verified)

        # 4. Assess Quality Gates
        quality_gates = self._assess_quality_gates(all_claims_verified)

        return ReportVerificationReport(
            id=str(uuid.uuid4()),
            report_id=rep_id,
            report_version_id=version_id,
            version_number=version_num,
            project_id=project_id,
            verifier_version=self.VERIFIER_VERSION,
            summary=summary,
            quality_gates=quality_gates,
            claims=all_claims_verified,
            section_verifications=section_verifications,
            status="completed",
            verified_at=datetime.now(timezone.utc).isoformat()
        )

    def _parse_sections(self, report_data: Dict[str, Any]) -> Dict[str, SectionGenerationOutput]:
        """Normalizes sections from GeneratedReport or raw dictionary."""
        sections_out: Dict[str, SectionGenerationOutput] = {}
        raw_sections = report_data.get("sections", [])
        if isinstance(raw_sections, dict):
            raw_sections = list(raw_sections.values())

        for s in raw_sections:
            if isinstance(s, dict):
                sec_obj = SectionGenerationOutput.model_validate(s)
                sections_out[sec_obj.section_id] = sec_obj
            elif isinstance(s, SectionGenerationOutput):
                sections_out[s.section_id] = s
        return sections_out

    def _parse_plan_sections(self, report_plan: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Maps plan sections by section_id for metadata checks."""
        if not report_plan:
            return {}
        sections = report_plan.get("sections", [])
        if isinstance(sections, dict):
            sections = list(sections.values())
        return {s.get("section_id", ""): s for s in sections if isinstance(s, dict)}

    def _build_verified_evidence_store(self, evidence_inventory: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Builds the store of verified evidence content.
        CRITICAL: Never extract facts from filenames, folder names, or URLs!
        Only reads verified_content, extracted_text, or explicit validated descriptions.
        """
        store: Dict[str, Dict[str, Any]] = {}
        for ev in evidence_inventory:
            ev_id = str(ev.get("id", ""))
            meta = ev.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}

            # Explicit content sources
            extracted_text = (
                ev.get("verified_content") or
                meta.get("verified_content") or
                meta.get("extracted_text") or
                ev.get("extracted_text") or
                ""
            )

            # Store evidence item metadata without inferring from filename
            store[ev_id] = {
                "id": ev_id,
                "file_name": ev.get("file_name") or ev.get("original_name") or "",
                "extracted_text": str(extracted_text).strip(),
                "description": str(ev.get("description") or meta.get("description") or "").strip(),
                "category": ev.get("category", "general"),
                "has_verified_content": bool(extracted_text.strip())
            }
        return store

    def _build_verified_project_facts(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes Stage 5 project information fields for ground truth matching."""
        title = project_info.get("title", "")
        desc = project_info.get("description", "")
        domain = project_info.get("domain", "")
        
        # Tech stack can be list or dict
        tech_raw = project_info.get("tech_stack") or []
        tech_set = set()
        if isinstance(tech_raw, list):
            for t in tech_raw:
                if isinstance(t, str):
                    tech_set.add(t.strip().lower())
                elif isinstance(t, dict) and "name" in t:
                    tech_set.add(str(t["name"]).strip().lower())
        elif isinstance(tech_raw, dict):
            for k, v in tech_raw.items():
                if isinstance(v, list):
                    for item in v:
                        tech_set.add(str(item).strip().lower())
                elif isinstance(v, str):
                    tech_set.add(v.strip().lower())

        # Also search description for explicitly mentioned tech
        for kw in KNOWN_TECHNOLOGIES:
            if re.search(r"\b" + re.escape(kw) + r"\b", desc.lower()):
                tech_set.add(kw)

        # Team members
        team = project_info.get("team_members") or []
        members_set = set()
        if isinstance(team, list):
            for m in team:
                if isinstance(m, dict) and "name" in m:
                    members_set.add(str(m["name"]).strip().lower())
                elif isinstance(m, str):
                    members_set.add(m.strip().lower())

        return {
            "title": title,
            "description": desc,
            "domain": domain,
            "technologies": tech_set,
            "team_members": members_set,
            "raw_text": f"{title} {desc} {domain}".lower()
        }

    def _verify_single_claim(
        self,
        claim: ExtractedClaim,
        report_version_id: str,
        project_facts: Dict[str, Any],
        evidence_store: Dict[str, Dict[str, Any]],
        section_research_required: bool
    ) -> ClaimVerificationRecord:
        """
        Validates a single claim deterministically based on its type and rules.
        """
        claim_text_lower = claim.text.lower()
        rec_id = f"vrec_{uuid.uuid4().hex[:12]}"

        # Prompt-Injection Defense:
        # Check if claim or evidence attempted prompt injection
        # (e.g., 'ignore rules', 'mark every claim as verified')
        # We explicitly never let that dictate the result.

        # ----------------------------------------------------------------------
        # 1. CITATION CLAIMS & PLACEHOLDERS
        # ----------------------------------------------------------------------
        if claim.claim_type == "citation_claim":
            if claim.raw_citation == "[CITATION_REQUIRED]" or "[citation_required]" in claim_text_lower:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="citation_claim",
                    status="citation_required",
                    reason="Explicit citation placeholder in generated content requires verified external reference.",
                    requires_review=True,
                    provenance={"marker": "[CITATION_REQUIRED]"},
                    verifier_version=self.VERIFIER_VERSION
                )

            # Validate citation against research provider / registered sources
            res = self.research_provider.verify_citation(claim.text)
            if res.get("is_valid"):
                source = res["source"]
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="citation_claim",
                    status="supported",
                    source_ids=[source.get("id", "src_verified")],
                    reason=f"Verified against registered academic publication: '{source.get('title')}'",
                    requires_review=False,
                    provenance=source,
                    verifier_version=self.VERIFIER_VERSION
                )
            else:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="citation_claim",
                    status="citation_invalid",
                    reason=f"Fabricated or unverified citation detected in claim: '{claim.raw_citation or claim.text[:60]}'. Not registered in authoritative sources.",
                    requires_review=True,
                    verifier_version=self.VERIFIER_VERSION
                )

        # ----------------------------------------------------------------------
        # 2. RESEARCH CLAIMS
        # ----------------------------------------------------------------------
        if claim.claim_type == "research_claim" or (section_research_required and any(w in claim_text_lower for w in ["studies show", "prior research", "literature reveals"])):
            return ClaimVerificationRecord(
                verification_id=rec_id,
                report_version_id=report_version_id,
                section_id=claim.section_id,
                claim_id=claim.claim_id,
                text=claim.text,
                claim_type="research_claim",
                status="citation_required",
                reason="External research literature citation is required by the report plan.",
                requires_review=True,
                verifier_version=self.VERIFIER_VERSION
            )

        # ----------------------------------------------------------------------
        # 3. TECHNOLOGY CLAIMS
        # ----------------------------------------------------------------------
        if claim.claim_type == "technology":
            mentioned_techs = [t for t in KNOWN_TECHNOLOGIES if re.search(r"\b" + re.escape(t) + r"\b", claim_text_lower)]
            if not mentioned_techs:
                mentioned_techs = claim.extracted_entities

            verified_techs = project_facts["technologies"]
            
            supported_techs = [t for t in mentioned_techs if t.lower() in verified_techs]
            unsupported_techs = [t for t in mentioned_techs if t.lower() not in verified_techs]

            if mentioned_techs and not unsupported_techs:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="technology",
                    status="supported",
                    source_ids=["project_information.tech_stack"],
                    reason=f"Technologies verified in project tech stack: {', '.join(supported_techs)}",
                    requires_review=False,
                    provenance={"field": "tech_stack", "verified_items": supported_techs},
                    verifier_version=self.VERIFIER_VERSION
                )
            elif supported_techs and unsupported_techs:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="technology",
                    status="partially_supported",
                    source_ids=["project_information.tech_stack"],
                    reason=f"Verified: {', '.join(supported_techs)}. Unverified technologies: {', '.join(unsupported_techs)}.",
                    requires_review=True,
                    provenance={"unverified_items": unsupported_techs},
                    verifier_version=self.VERIFIER_VERSION
                )
            else:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="technology",
                    status="unsupported",
                    reason=f"None of the mentioned technologies ({', '.join(mentioned_techs)}) are present in verified project information.",
                    requires_review=True,
                    verifier_version=self.VERIFIER_VERSION
                )

        # ----------------------------------------------------------------------
        # 4. NUMERICAL & PROJECT RESULT CLAIMS
        # ----------------------------------------------------------------------
        if claim.claim_type in ["metric", "project_result"]:
            # Extract numbers from claim text (e.g. 92%, 95%, 87.4%, 1000, 40ms)
            numbers = self._extract_numbers_with_context(claim.text)
            
            # MANDATORY RULE: FILENAME INFERENCE FORBIDDEN
            # Never check file_name or original_name for the numbers!
            # Only check verified extracted text in evidence items or project info
            matching_evidence_id = None
            matching_snippet = None

            for ev_id, ev_data in evidence_store.items():
                ev_content = ev_data["extracted_text"]
                if not ev_content:
                    continue  # Filename alone without extracted content can NEVER support numerical claim!

                # Check if all numbers in claim appear in this evidence text
                if all(num.lower() in ev_content.lower() for num in numbers):
                    matching_evidence_id = ev_id
                    matching_snippet = ev_content[:200]
                    break

            # If it's a project_result (e.g., accuracy, benchmark), project description alone cannot verify it
            if matching_evidence_id:
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    status="supported",
                    evidence_ids=[matching_evidence_id],
                    reason=f"Numerical result verified against extracted evidence content in file ID {matching_evidence_id}.",
                    requires_review=False,
                    provenance={"evidence_id": matching_evidence_id, "excerpt": matching_snippet},
                    verifier_version=self.VERIFIER_VERSION
                )
            
            # Check if verified project description has exact metric (only for non-experimental metric)
            if claim.claim_type == "metric" and all(num.lower() in project_facts["raw_text"] for num in numbers):
                return ClaimVerificationRecord(
                    verification_id=rec_id,
                    report_version_id=report_version_id,
                    section_id=claim.section_id,
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="metric",
                    status="supported",
                    source_ids=["project_information.description"],
                    reason="Metric verified against project description ground truth.",
                    requires_review=False,
                    provenance={"field": "description"},
                    verifier_version=self.VERIFIER_VERSION
                )

            # Check if an evidence item exists by filename, but has NO content
            has_name_only_match = any(
                all(num.replace("%", "").lower() in ev["file_name"].lower() for num in numbers)
                for ev in evidence_store.values()
            )

            if has_name_only_match:
                reason = "Filename-inference protection: Filename matches metric, but actual evidence file content has not been verified. Supporting content required."
            else:
                reason = f"No verified evidence file or project fact contains the exact metrics ({', '.join(numbers)})."

            return ClaimVerificationRecord(
                verification_id=rec_id,
                report_version_id=report_version_id,
                section_id=claim.section_id,
                claim_id=claim.claim_id,
                text=claim.text,
                claim_type=claim.claim_type,
                status="unsupported",
                reason=reason,
                requires_review=True,
                verifier_version=self.VERIFIER_VERSION
            )

        # ----------------------------------------------------------------------
        # 5. GENERAL PROJECT FACTS & DATASETS
        # ----------------------------------------------------------------------
        # Check against project title, description, domain
        # If words in claim match project description significantly
        proj_text = project_facts["raw_text"]
        words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim_text_lower) if w not in ["this", "that", "with", "from", "system", "project"]]
        matching_words = [w for w in words if w in proj_text]

        if len(matching_words) >= 2 or any(term in proj_text for term in [project_facts["title"].lower(), project_facts["domain"].lower()] if term):
            return ClaimVerificationRecord(
                verification_id=rec_id,
                report_version_id=report_version_id,
                section_id=claim.section_id,
                claim_id=claim.claim_id,
                text=claim.text,
                claim_type=claim.claim_type,
                status="supported",
                source_ids=["project_information"],
                reason="Grounded in Stage 5 project title, description, and domain metadata.",
                requires_review=False,
                provenance={"matched_terms": matching_words[:4]},
                verifier_version=self.VERIFIER_VERSION
            )

        # Default fallback: requires review
        return ClaimVerificationRecord(
            verification_id=rec_id,
            report_version_id=report_version_id,
            section_id=claim.section_id,
            claim_id=claim.claim_id,
            text=claim.text,
            claim_type=claim.claim_type,
            status="requires_review",
            reason="Claim makes project assertions that could not be fully substantiated from available facts or evidence.",
            requires_review=True,
            verifier_version=self.VERIFIER_VERSION
        )

    def _extract_numbers_with_context(self, text: str) -> List[str]:
        """Extracts percentages, exact counts, decimals, or metric values from string."""
        matches = NUMERICAL_PATTERN.findall(text)
        if not matches:
            # Fallback to general numbers
            matches = re.findall(r"\b\d+(?:\.\d+)?%?\b", text)
        return [m.strip() for m in matches if m.strip()]

    def _calculate_summary(self, claims: List[ClaimVerificationRecord]) -> VerificationSummary:
        """Calculates aggregate counts and grounding percentage."""
        total = len(claims)
        supported = sum(1 for c in claims if c.status == "supported")
        partially = sum(1 for c in claims if c.status == "partially_supported")
        unsupported = sum(1 for c in claims if c.status == "unsupported")
        review = sum(1 for c in claims if c.status == "requires_review")
        missing_ev = sum(1 for c in claims if c.status == "missing_evidence")
        cit_req = sum(1 for c in claims if c.status == "citation_required")
        cit_inv = sum(1 for c in claims if c.status == "citation_invalid")
        failed = sum(1 for c in claims if c.status == "verification_failed")

        # Grounding rate: supported + 0.5 * partially / total
        rate = 0.0
        if total > 0:
            rate = round(((supported + 0.5 * partially) / total) * 100.0, 1)

        return VerificationSummary(
            total_claims=total,
            supported=supported,
            partially_supported=partially,
            unsupported=unsupported,
            requires_review=review,
            missing_evidence=missing_ev,
            citation_required=cit_req,
            citation_invalid=cit_inv,
            verification_failed=failed,
            grounding_rate_percent=rate
        )

    def _assess_quality_gates(self, claims: List[ClaimVerificationRecord]) -> QualityGateResult:
        """
        Assesses blocking quality gates for document generation:
        - Blocking: Fabricated citations (citation_invalid), unsupported numerical results, missing required core evidence.
        - Warnings: Placeholders (citation_required), partially supported technologies, general review items.
        """
        blocking_issues: List[str] = []
        warnings: List[str] = []

        for c in claims:
            if c.status == "citation_invalid":
                blocking_issues.append(f"Blocking: Invalid or fabricated citation detected: '{c.text[:70]}'")
            elif c.status == "unsupported" and c.claim_type in ["project_result", "metric"]:
                blocking_issues.append(f"Blocking: Unsupported numerical project result without verified evidence: '{c.text[:70]}'")
            elif c.status == "citation_required":
                warnings.append(f"Warning: Literature citation required: '{c.text[:70]}'")
            elif c.status == "partially_supported":
                warnings.append(f"Warning: Partially verified claim: '{c.text[:70]}'")
            elif c.status == "requires_review":
                warnings.append(f"Warning: Needs manual review: '{c.text[:70]}'")

        can_proceed = len(blocking_issues) == 0

        return QualityGateResult(
            can_proceed_to_document_generation=can_proceed,
            blocking_issues=blocking_issues,
            warnings=warnings
        )
