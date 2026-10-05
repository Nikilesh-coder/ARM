"""
ReportForge AI - Template Schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from packages.template_intelligence.schema import TemplateSchema


class TemplateUploadResponse(BaseModel):
    template_id: str
    name: str
    file_size_bytes: int
    is_preset: bool = False
    status: str
    message: str
    file_type: Optional[str] = None
    project_id: Optional[str] = None
    original_file_path: Optional[str] = None
    analysis_status: Optional[str] = "pending"


class TemplateDTO(BaseModel):
    id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    owner_id: Optional[str] = None
    name: str
    original_file_path: Optional[str] = None
    file_type: str = "docx"
    file_size: Optional[int] = None
    status: str = "uploaded"  # uploaded, analyzing, analyzed, confirmed, ready, failed
    analysis_status: Optional[str] = "pending"
    is_locked: bool = False
    is_institution_preset: Optional[bool] = False
    is_master: Optional[bool] = False
    institution: Optional[str] = None
    department: Optional[str] = None
    report_type: Optional[str] = None
    active: Optional[bool] = True
    page_settings: Optional[Dict[str, Any]] = None
    field_mapping: Optional[List[Dict[str, Any]]] = None
    image_mapping: Optional[List[Dict[str, Any]]] = None
    detected_elements: Optional[Dict[str, Any]] = None
    fixed_elements_summary: Optional[Dict[str, Any]] = None
    locked_at: Optional[Any] = None
    locked_by: Optional[str] = None
    locked_schema_version: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class CustomTemplateMappingRequest(BaseModel):
    field_mapping: List[Dict[str, Any]]
    image_mapping: Optional[List[Dict[str, Any]]] = None



class TemplateAnalyzeResponse(BaseModel):
    job_id: str
    template_id: str
    project_id: str
    status: str
    message: str


class TemplateConfirmDTO(BaseModel):
    approved_schema: TemplateSchema
    notes: Optional[str] = None


class TemplateAnalysisResponse(BaseModel):
    template_id: str
    status: str  # pending, analyzing, completed, failed
    schema_version: Optional[str] = "1.0.0"
    parser_version: Optional[str] = "1.0.0"
    schema_data: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GenerationJobResponse(BaseModel):
    id: str
    job_type: str
    status: str  # queued, running, completed, failed
    progress: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    result_payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# Stage 4: Template Review + Lock Schemas
# ------------------------------------------------------------------------------

class TemplateReviewResponse(BaseModel):
    template_id: str
    template_name: str
    project_id: Optional[str] = None
    file_type: str
    file_size: Optional[int] = None
    status: str  # analyzed, reviewing, locked
    review_status: str  # pending_review, in_review, reviewed, locked
    is_locked: bool = False
    source_analysis: Dict[str, Any]
    reviewed_schema: Optional[Dict[str, Any]] = None
    locked_schema: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    unsupported_features: List[str] = []
    confidence_score: float = 1.0
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    locked_schema_version: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TemplateReviewPatchRequest(BaseModel):
    reviewed_schema: Dict[str, Any]
    notes: Optional[str] = None


class TemplateLockRequest(BaseModel):
    confirm: bool = True
    notes: Optional[str] = None


class TemplateLockResponse(BaseModel):
    status: str = "locked"
    is_locked: bool = True
    template_id: str
    project_id: Optional[str] = None
    locked_at: datetime
    locked_by: Optional[str] = None
    locked_schema_version: str = "1.0.0"
    sections_count: int
    locked_schema: Dict[str, Any]
    message: str = "Template locked successfully. This reviewed structure is now the authoritative formatting source of truth."


# ------------------------------------------------------------------------------
# Template Field Schemas (Master College Template & Field Replacement Engine)
# ------------------------------------------------------------------------------

class TemplateFieldDTO(BaseModel):
    field_key: Optional[str] = None
    field_name: str
    field_label: Optional[str] = None
    field_type: str = "text"  # 'text', 'long_text', 'image', 'table', 'list'
    section_key: Optional[str] = None
    page_or_section: Optional[str] = None
    is_required: bool = True
    placeholder_identifier: Optional[str] = None
    content_limits: Optional[Dict[str, Any]] = None
    image_dimensions: Optional[Dict[str, Any]] = None
    ordering: int = 0
    max_length: Optional[int] = None
    bounding_box: Optional[Dict[str, Any]] = None
    default_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateFieldResponseDTO(BaseModel):
    id: str
    template_id: str
    field_key: Optional[str] = None
    field_name: str
    field_label: Optional[str] = None
    field_type: str = "text"
    section_key: Optional[str] = None
    page_or_section: Optional[str] = None
    is_required: bool = True
    placeholder_identifier: Optional[str] = None
    content_limits: Optional[Dict[str, Any]] = None
    image_dimensions: Optional[Dict[str, Any]] = None
    ordering: int = 0
    max_length: Optional[int] = None
    bounding_box: Optional[Dict[str, Any]] = None
    default_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MasterTemplateResponseDTO(BaseModel):
    id: str
    name: str
    is_master: bool = True
    is_locked: bool = True
    status: str = "locked"
    master_version: str = "1.0.0"
    description: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    fields_count: int
    fields: List[TemplateFieldResponseDTO]


