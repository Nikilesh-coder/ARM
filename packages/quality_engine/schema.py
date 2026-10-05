"""
ARM Stage 11 - Report Validation & Quality Engine Schema
Defines structured models, enums, check categories, issue severities,
quality gate statuses, and audit records for the comprehensive quality gate.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import hashlib
import json
from pydantic import BaseModel, Field, ConfigDict


CheckStatus = Literal["PASS", "WARNING", "FAIL", "NOT_TESTED"]
IssueSeverity = Literal["INFO", "WARNING", "ERROR", "BLOCKING"]
QualityGateStatus = Literal["READY", "READY_WITH_WARNINGS", "REVIEW_REQUIRED", "BLOCKED", "FAILED"]

ValidationCategory = Literal[
    "template_compliance",
    "report_plan_compliance",
    "section_completeness",
    "content_grounding",
    "evidence_compliance",
    "internal_consistency",
    "data_integrity",
    "docx_validation",
    "pdf_validation",
    "cross_artifact_consistency",
    "security_validation",
    "quality_gate"
]


class ValidationCheck(BaseModel):
    """An individual validation check result within a layer."""
    model_config = ConfigDict(extra="ignore")

    check_id: str = Field(..., description="Unique check identifier")
    category: str = Field(..., description="Validation category or layer name")
    status: CheckStatus = Field(default="NOT_TESTED", description="Outcome: PASS, WARNING, FAIL, NOT_TESTED")
    severity: IssueSeverity = Field(default="INFO", description="Severity: INFO, WARNING, ERROR, BLOCKING")
    message: str = Field(..., description="Human-readable explanation of check finding")
    source: Optional[str] = Field(default=None, description="System or component that performed the check")
    section_id: Optional[str] = Field(default=None, description="ID of affected section if applicable")


class ValidationIssue(BaseModel):
    """A surfaced issue requiring attention, review, or blocking progression."""
    model_config = ConfigDict(extra="ignore")

    issue_id: str = Field(..., description="Unique issue identifier")
    category: str = Field(..., description="Category: template, plan, content, evidence, consistency, etc.")
    severity: IssueSeverity = Field(..., description="Severity: INFO, WARNING, ERROR, BLOCKING")
    message: str = Field(..., description="Actionable description of the problem")
    section_id: Optional[str] = Field(default=None, description="Affected section ID")
    section_title: Optional[str] = Field(default=None, description="Affected section title")
    affected_claim: Optional[str] = Field(default=None, description="Specific claim text if applicable")
    evidence_id: Optional[str] = Field(default=None, description="Evidence ID or citation reference if applicable")
    suggested_action: Optional[str] = Field(default=None, description="Recommended remediation step for user or system")


class ValidationSummary(BaseModel):
    """Factual aggregate counts and final quality gate assessment."""
    model_config = ConfigDict(extra="ignore")

    total_checks: int = 0
    passed_checks: int = 0
    warning_checks: int = 0
    failed_checks: int = 0
    not_tested_checks: int = 0
    blocking_count: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    info_count: int = 0
    gate_status: QualityGateStatus = "READY"


class InputHashes(BaseModel):
    """Cryptographic hashes of all inputs for stale validation detection."""
    model_config = ConfigDict(extra="ignore")

    content_sha256: str = Field(default="", description="SHA-256 of report content JSON")
    docx_sha256: Optional[str] = Field(default=None, description="SHA-256 of compiled DOCX artifact")
    pdf_sha256: Optional[str] = Field(default=None, description="SHA-256 of compiled PDF artifact")
    template_sha256: Optional[str] = Field(default=None, description="SHA-256 of template schema or template file")
    plan_sha256: Optional[str] = Field(default=None, description="SHA-256 of report plan")

    @classmethod
    def compute_sha256(cls, data: Any) -> str:
        """Deterministic SHA-256 for strings, bytes, or serialized dicts."""
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        if isinstance(data, str):
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @classmethod
    def compute_content_hash(cls, report_data: Any) -> str:
        """Deterministic hash of report substantive content (ignoring dynamic timestamp metadata)."""
        if not report_data:
            return ""
        sections = report_data.get("sections") if isinstance(report_data, dict) else getattr(report_data, "sections", [])
        title = report_data.get("title") if isinstance(report_data, dict) else getattr(report_data, "title", "")
        version_num = report_data.get("version_number") if isinstance(report_data, dict) else getattr(report_data, "version_number", 1)

        content_repr = {
            "title": title,
            "version_number": version_num,
            "sections": [
                {
                    "section_id": s.get("section_id") if isinstance(s, dict) else getattr(s, "section_id", None),
                    "title": s.get("section_title") if isinstance(s, dict) else getattr(s, "section_title", None),
                    "blocks": [
                        {
                            "type": b.get("block_type") if isinstance(b, dict) else getattr(b, "block_type", None),
                            "text": b.get("text") if isinstance(b, dict) else getattr(b, "text", None),
                            "items": b.get("items") if isinstance(b, dict) else getattr(b, "items", None),
                            "rows": b.get("rows") if isinstance(b, dict) else getattr(b, "rows", None),
                            "evidence": b.get("source_evidence_ids") if isinstance(b, dict) else getattr(b, "source_evidence_ids", None)
                        }
                        for b in (s.get("content_blocks") if isinstance(s, dict) else getattr(s, "content_blocks", []))
                    ]
                }
                for s in (sections or [])
            ]
        }
        return cls.compute_sha256(content_repr)


class ReportQualityResult(BaseModel):
    """Authoritative validation result for a complete academic report version."""
    model_config = ConfigDict(extra="ignore")

    validation_id: str = Field(..., description="Unique UUID for this validation result")
    report_id: str = Field(..., description="Associated Report UUID")
    report_version_id: str = Field(..., description="Associated Report Version UUID")
    version_number: int = Field(default=1, description="Report version number")
    project_id: str = Field(..., description="Associated Project UUID")
    validator_version: str = Field(default="1.0.0", description="Semantic version of the quality engine")
    status: QualityGateStatus = Field(default="READY", description="Final verdict: READY, READY_WITH_WARNINGS, REVIEW_REQUIRED, BLOCKED, FAILED")
    gate_status: QualityGateStatus = Field(default="READY", description="Quality gate status")
    checks: List[ValidationCheck] = Field(default_factory=list, description="Array of all evaluated checks")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Array of all surfaced issues")
    summary: ValidationSummary = Field(default_factory=ValidationSummary, description="Factual numerical summary")
    input_hashes: InputHashes = Field(default_factory=InputHashes, description="Input hashes for stale detection")
    is_stale: bool = Field(default=False, description="True if underlying report or artifacts were modified since validation")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
