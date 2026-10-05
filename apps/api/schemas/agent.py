"""
ReportForge AI - AI Report Agent Schemas
Defines structured input, output, and validation models for the AI Report Agent.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EvidenceItemDTO(BaseModel):
    id: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    storage_path: Optional[str] = None
    content_summary: Optional[str] = None


class TemplateFieldSpecDTO(BaseModel):
    field_name: str
    field_type: str = "text"  # 'text', 'long_text', 'image', 'table', 'list'
    field_label: Optional[str] = None
    page_or_section: Optional[str] = "General"
    is_required: bool = True
    placeholder_identifier: Optional[str] = None
    content_limits: Dict[str, Any] = Field(default_factory=dict)
    image_dimensions: Dict[str, Any] = Field(default_factory=dict)
    ordering: int = 0


class AIReportAgentInputDTO(BaseModel):
    project_title: str
    project_description: str
    user_instructions: Optional[str] = None
    template_id: Optional[str] = "00000000-0000-0000-0000-000000000001"
    template_fields: Optional[List[TemplateFieldSpecDTO]] = None
    evidence_files: Optional[List[EvidenceItemDTO]] = None
    project_id: Optional[str] = None
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    guide_name: Optional[str] = None


class FieldValidationResult(BaseModel):
    field_name: str
    is_valid: bool
    field_type: str
    word_count: Optional[int] = None
    item_count: Optional[int] = None
    message: Optional[str] = None


class ValidationReportDTO(BaseModel):
    is_valid: bool
    total_fields: int
    valid_fields_count: int
    missing_required_fields: List[str] = Field(default_factory=list)
    field_results: List[FieldValidationResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AIReportAgentOutputDTO(BaseModel):
    status: str = "completed"  # 'completed', 'failed', 'thinking', 'creating'
    stage: str = "completed"   # 'thinking', 'creating', 'completed', 'failed'
    content: Dict[str, Any]
    validation: ValidationReportDTO
    model_used: str
    generated_at: str
    job_id: Optional[str] = None
    error: Optional[str] = None


class AgentJobStatusDTO(BaseModel):
    job_id: str
    status: str  # 'thinking', 'creating', 'completed', 'failed'
    stage: str
    progress_percent: int
    stage_label: str
    stage_detail: str
    error: Optional[str] = None
    created_at: str
    updated_at: str
