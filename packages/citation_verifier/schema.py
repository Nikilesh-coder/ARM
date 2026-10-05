"""
ARM Stage 8 - Citation + Evidence Verification Schema
Defines structured models, enums, quality gates, and verification records
for validating AI-generated report claims against project facts and evidence.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


ClaimType = Literal[
    "project_fact",
    "project_result",
    "metric",
    "technology",
    "dataset",
    "methodology",
    "external_fact",
    "research_claim",
    "citation_claim",
    "inferred_claim",
]

VerificationStatus = Literal[
    "pending",
    "supported",
    "partially_supported",
    "unsupported",
    "requires_review",
    "missing_evidence",
    "citation_required",
    "citation_invalid",
    "verification_failed",
]

EvidenceSourceType = Literal[
    "project_information",
    "uploaded_evidence",
    "verified_external_source",
    "existing_reference",
    "user_provided_citation",
]


class ExtractedClaim(BaseModel):
    """A claim extracted from a generated report section for verification."""
    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(..., description="Unique deterministic or generated identifier for the claim")
    section_id: str = Field(..., description="ID of the report section where this claim appears")
    text: str = Field(..., description="Text of the assertion being verified")
    claim_type: ClaimType = Field(default="project_fact", description="Category of the claim")
    extracted_entities: List[str] = Field(default_factory=list, description="Extracted numbers, technologies, metrics, or citations")
    raw_citation: Optional[str] = Field(default=None, description="Explicit citation marker if present in text")
    source_evidence_ids: List[str] = Field(default_factory=list, description="Claimed source evidence IDs from content block")


class ClaimVerificationRecord(BaseModel):
    """The authoritative verification outcome for a single claim."""
    model_config = ConfigDict(extra="ignore")

    verification_id: str = Field(..., description="Unique ID for this verification record")
    report_version_id: str = Field(..., description="ID of the specific report version verified")
    section_id: str = Field(..., description="ID of the report section")
    claim_id: str = Field(..., description="ID of the claim")
    text: str = Field(..., description="Text of the claim")
    claim_type: ClaimType = Field(..., description="Type of the claim")
    status: VerificationStatus = Field(..., description="Verification status outcome")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting project evidence files")
    source_ids: List[str] = Field(default_factory=list, description="IDs of supporting project info fields or external sources")
    reason: Optional[str] = Field(default=None, description="User-facing rationale for the status determination")
    requires_review: bool = Field(default=False, description="True if manual student/advisor review is recommended")
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Traceability details (exact snippet, field name, etc.)")
    verifier_version: str = Field(default="1.0.0", description="Version of the verifier engine")
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VerificationSummary(BaseModel):
    """Aggregate metric breakdown of claim verification statuses."""
    model_config = ConfigDict(extra="ignore")

    total_claims: int = 0
    supported: int = 0
    partially_supported: int = 0
    unsupported: int = 0
    requires_review: int = 0
    missing_evidence: int = 0
    citation_required: int = 0
    citation_invalid: int = 0
    verification_failed: int = 0
    grounding_rate_percent: float = 0.0


class QualityGateResult(BaseModel):
    """Assessment of whether the report meets quality gates for downstream document generation."""
    model_config = ConfigDict(extra="ignore")

    can_proceed_to_document_generation: bool = True
    blocking_issues: List[str] = Field(default_factory=list, description="Critical issues preventing document compilation")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking observations or recommendations")


class ReportVerificationReport(BaseModel):
    """Complete structured verification result for an entire report version."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique ID of the verification run")
    report_id: str = Field(..., description="ID of the report")
    report_version_id: str = Field(..., description="ID of the report version")
    version_number: int = Field(default=1, description="Version number of the verified report")
    project_id: str = Field(..., description="ID of the owning project")
    verifier_version: str = Field(default="1.0.0", description="Verifier software version")
    summary: VerificationSummary = Field(default_factory=VerificationSummary)
    quality_gates: QualityGateResult = Field(default_factory=QualityGateResult)
    claims: List[ClaimVerificationRecord] = Field(default_factory=list)
    section_verifications: Dict[str, List[ClaimVerificationRecord]] = Field(default_factory=dict)
    status: str = Field(default="completed")
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
