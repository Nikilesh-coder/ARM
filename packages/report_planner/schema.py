"""
ARM Stage 6 - Structured Report Plan Schema
Defines the Pydantic data model for the AI Report Planner.
Strictly versioned, validated, and aligned with Stage 4 Locked Template Schema.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]
VerificationStatus = Literal["READY", "PARTIALLY_VERIFIED", "MISSING_INFORMATION", "RESEARCH_REQUIRED"]


class SectionPlanItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section_id: str = Field(..., description="Unique section key/id corresponding to the template section")
    title: str = Field(..., description="Title of the section as defined in the template")
    level: int = Field(default=1, ge=1, le=6, description="Heading level hierarchy (1-6)")
    order: int = Field(..., ge=1, description="Sequential position in the report outline")
    semantic_role: str = Field(
        default="body",
        description="Role: cover, certificate, declaration, abstract, introduction, literature_review, methodology, implementation, results, conclusion, references, appendix"
    )
    purpose: str = Field(..., description="Objective and narrative purpose of this section")
    required: bool = Field(default=True, description="Whether this section is mandatory per college template")
    content_requirements: List[str] = Field(
        default_factory=list,
        description="Key factual topics and components required in this section"
    )
    project_fact_references: List[str] = Field(
        default_factory=list,
        description="Names of project facts grounding this section (e.g. problem_statement, objectives, methodology)"
    )
    evidence_references: List[str] = Field(
        default_factory=list,
        description="Filenames or IDs of uploaded evidence assets mapped to substantiate this section"
    )
    required_evidence_types: List[str] = Field(
        default_factory=list,
        description="Types of supporting evidence expected (e.g. dataset, system_output, code_sample)"
    )
    research_required: bool = Field(
        default=False,
        description="True if external academic literature or citations will be needed later"
    )
    research_notes: Optional[str] = Field(
        default=None,
        description="Guidance on what external literature to search for"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Explicit gaps in project information or evidence that must not be hallucinated"
    )
    generation_notes: Optional[str] = Field(
        default=None,
        description="Non-prose guidelines for future generation: strict boundaries and cautions"
    )
    confidence: ConfidenceLevel = Field(
        default="HIGH",
        description="Confidence level in factual grounding: HIGH, MEDIUM, LOW"
    )
    verification_status: VerificationStatus = Field(
        default="READY",
        description="Operational state: READY, PARTIALLY_VERIFIED, MISSING_INFORMATION, RESEARCH_REQUIRED"
    )


class PlannerMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planner_version: str = "1.0.0"
    ai_provider: str = "gemini"
    ai_model: str = "gemini-3.1-flash-lite"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    template_schema_version: str = "1.0.0"
    project_updated_at: Optional[str] = None
    evidence_count: int = 0
    members_count: int = 0


class PlanSummaryMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_sections: int = 0
    ready_sections: int = 0
    partially_verified_sections: int = 0
    missing_info_sections: int = 0
    research_required_sections: int = 0
    total_missing_items: int = 0
    total_evidence_mappings: int = 0
    overall_confidence: ConfidenceLevel = "HIGH"


class ReportPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0.0", description="Report plan schema specification version")
    plan_id: Optional[str] = Field(default=None, description="Unique UUID for this report plan")
    project_id: str = Field(..., description="Project UUID to which this plan belongs")
    template_id: str = Field(..., description="Locked template UUID controlling this plan")
    template_schema_version: str = Field(default="1.0.0", description="Version of the locked template schema")
    title: str = Field(..., description="Formal academic report title")
    target_page_count: int = Field(default=30, ge=5, le=200, description="Target report length in pages")
    sections: List[SectionPlanItem] = Field(..., min_length=1, description="Ordered list of planned sections")
    global_requirements: List[str] = Field(
        default_factory=list,
        description="Overall formatting, stylistic, and academic conventions prescribed by template"
    )
    unresolved_items: List[str] = Field(
        default_factory=list,
        description="Project-wide gaps or inconsistencies requiring student clarification"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Operational cautions or missing evidence alerts"
    )
    summary_metrics: PlanSummaryMetrics = Field(
        default_factory=PlanSummaryMetrics,
        description="Aggregated readiness metrics across all sections"
    )
    planner_metadata: PlannerMetadata = Field(
        default_factory=PlannerMetadata,
        description="Audit metadata regarding the planning process and model used"
    )
    is_stale: bool = Field(default=False, description="True if project information was modified after this plan was generated")
    status: str = Field(default="draft", description="Plan lifecycle status: draft, completed, approved")
    is_approved: bool = Field(default=False, description="Whether the plan has been reviewed and approved by student")
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
