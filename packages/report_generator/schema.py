"""
ARM Stage 7 - Structured Report Generation Schema
Defines the Pydantic data models for section-by-section academic report generation.
Strictly versioned, validated, and aligned with Stage 4 Locked Template and Stage 6 Approved Plan.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


BlockType = Literal["heading", "paragraph", "bullet_list", "numbered_list", "table", "quote", "note"]
GroundingStatus = Literal["grounded", "partially_grounded", "requires_review", "missing_information", "validation_failed"]
SeverityLevel = Literal["info", "warning", "critical"]


class ContentBlock(BaseModel):
    """A discrete structured block of content within a section."""
    model_config = ConfigDict(extra="ignore")

    block_type: str = Field(default="paragraph", description="Type of content block")
    text: str = Field(default="", description="Main textual content or caption")
    level: Optional[int] = Field(default=None, ge=1, le=6, description="Heading level if block_type == 'heading'")
    items: Optional[List[str]] = Field(default=None, description="List items if block_type is a list")
    headers: Optional[List[str]] = Field(default=None, description="Table column headers if block_type == 'table'")
    rows: Optional[List[List[str]]] = Field(default=None, description="Table rows if block_type == 'table'")
    source_evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence files substantiating this block")


class MissingInformationItem(BaseModel):
    """Explicitly flagged gap in project ground truth."""
    model_config = ConfigDict(extra="ignore")

    field: str = Field(..., description="Name of the missing project fact or evidence field")
    reason: str = Field(..., description="Explanation of why this information is missing and what is needed")
    severity: SeverityLevel = Field(default="warning", description="Severity level: info, warning, critical")


class VisualRequirement(BaseModel):
    """Structured visual or diagram placeholder (no fake image generated in Stage 7)."""
    model_config = ConfigDict(extra="ignore")

    visual_type: str = Field(..., description="Type of visual needed: architecture_diagram, flow_chart, chart, mockup")
    description: str = Field(..., description="Description of the visual to be generated in later stages")
    status: str = Field(default="pending", description="Status of the visual asset")


class SectionGenerationOutput(BaseModel):
    """Complete structured output for a single generated report section."""
    model_config = ConfigDict(extra="ignore")

    section_id: str = Field(..., description="Matches the section_id in the approved ReportPlan")
    section_title: str = Field(..., description="Matches the section title in the approved ReportPlan")
    section_order: int = Field(default=1, ge=1, description="Sequential index of this section in the report outline")
    content_blocks: List[ContentBlock] = Field(default_factory=list, description="List of validated content blocks")
    missing_information: List[MissingInformationItem] = Field(
        default_factory=list,
        description="Structured gaps where project facts or evidence were unavailable"
    )
    grounding_status: GroundingStatus = Field(
        default="grounded",
        description="Grounding integrity assessment: grounded, partially_grounded, requires_review, missing_information, validation_failed"
    )
    grounding_notes: List[str] = Field(
        default_factory=list,
        description="Audit notes explaining fact sources and evidence linkages"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-blocking operational or academic warnings"
    )
    research_marker_preserved: bool = Field(
        default=False,
        description="True if external academic research remains required (deferred to research stage)"
    )
    visual_requirements: List[VisualRequirement] = Field(
        default_factory=list,
        description="Placeholders for visuals/diagrams deferred to visual generation stage"
    )
    word_count: int = Field(default=0, ge=0, description="Computed word count of all text blocks")


class GenerationMetadata(BaseModel):
    """Audit and provenance metadata for the generated report draft."""
    model_config = ConfigDict(extra="ignore")

    generator_version: str = "1.0.0"
    ai_provider: str = "gemini"
    ai_model: str = "gemini-3.1-flash-lite"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    template_schema_version: str = "1.0.0"
    report_plan_id: str = ""
    report_plan_version: str = "1.0.0"
    total_sections_planned: int = 0
    total_sections_generated: int = 0
    total_word_count: int = 0
    generation_job_id: Optional[str] = None


class GeneratedReport(BaseModel):
    """Authoritative representation of a complete generated report version."""
    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(..., description="Unique UUID for this academic report")
    project_id: str = Field(..., description="Project UUID to which this report belongs")
    template_id: str = Field(..., description="Locked template UUID controlling this report")
    template_schema_version: str = Field(default="1.0.0", description="Version of the locked template schema")
    report_plan_id: str = Field(..., description="Approved ReportPlan UUID")
    report_plan_version: str = Field(default="1.0.0", description="Version of the approved report plan")
    version_number: int = Field(default=1, ge=1, description="Sequential version number of this report draft")
    title: str = Field(..., description="Formal academic report title")
    sections: List[SectionGenerationOutput] = Field(default_factory=list, description="Ordered list of generated sections")
    overall_grounding: GroundingStatus = Field(default="grounded", description="Overall factual grounding state")
    total_word_count: int = Field(default=0, ge=0, description="Total word count across all sections")
    status: str = Field(default="completed", description="Report lifecycle status: draft, generating, completed, failed")
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata, description="Audit provenance metadata")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
