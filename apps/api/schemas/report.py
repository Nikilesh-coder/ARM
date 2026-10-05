"""
ReportForge AI - Report & Planner Schemas
Stage 6: AI Report Planner Structured Schema
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from packages.report_planner.schema import (
    ReportPlan,
    SectionPlanItem,
    PlannerMetadata,
    PlanSummaryMetrics,
    ConfidenceLevel,
    VerificationStatus
)


# --- Legacy Schemas (Preserved for Stage 1 Compatibility) ---
class SectionPlanDTO(BaseModel):
    section_key: str
    title: str
    sequence_order: int
    level: int = 1
    mandatory: bool = True
    estimated_word_count: int = 400


class ReportPlanRequestDTO(BaseModel):
    project_id: str
    template_id: str
    report_title: str
    report_type: str
    custom_sections: Optional[List[SectionPlanDTO]] = None


class ReportPlanResponseDTO(BaseModel):
    report_id: str
    project_id: str
    template_id: str
    title: str
    status: str
    sections: List[SectionPlanDTO]
    created_at: datetime


class SectionContentDTO(BaseModel):
    section_key: str
    title: str
    content_markdown: str
    citations: List[str]
    word_count: int


# --- Stage 6 Request & Response DTOs ---

class PlanReportRequestDTO(BaseModel):
    force: bool = False
    target_page_count: Optional[int] = None


class ApprovePlanRequestDTO(BaseModel):
    plan_id: Optional[str] = None
    notes: Optional[str] = None


class PlanningJobResponseDTO(BaseModel):
    job_id: str
    project_id: str
    status: str
    message: str
    current_stage: str
    progress_percentage: int


# ------------------------------------------------------------------------------
# Report Creation, Generated Content & Asset Schemas
# ------------------------------------------------------------------------------

class ReportCreateDTO(BaseModel):
    title: str
    template_id: Optional[str] = None
    report_type: Optional[str] = "capstone"
    status: Optional[str] = "planning"


class ReportResponseDTO(BaseModel):
    id: str
    project_id: str
    template_id: Optional[str] = None
    title: str
    report_type: Optional[str] = None
    current_version: int = 1
    status: str
    docx_storage_path: Optional[str] = None
    pdf_storage_path: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GeneratedContentCreateDTO(BaseModel):
    section_key: str
    field_key: Optional[str] = None
    content_type: str = "prose"
    raw_content: str
    formatted_content: Optional[str] = None
    word_count: Optional[int] = 0
    character_count: Optional[int] = 0
    token_count: Optional[int] = 0
    confidence_score: Optional[float] = 1.0
    status: Optional[str] = "draft"
    version_number: Optional[int] = 1
    metadata: Optional[Dict[str, Any]] = None


class GeneratedContentResponseDTO(GeneratedContentCreateDTO):
    id: str
    report_id: str
    project_id: str
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReportAssetCreateDTO(BaseModel):
    asset_type: str = "diagram"  # 'image', 'diagram', 'chart', 'canva_asset', 'evidence_photo', 'architecture_diagram'
    source: Optional[str] = "generated"  # 'generated', 'diagram_engine', 'chart_engine', 'unsplash_open', 'evidence'
    title: str
    caption: Optional[str] = None
    description: Optional[str] = None
    file_name: str
    storage_path: str
    file_url: Optional[str] = None
    template_field: Optional[str] = None  # e.g., 'image_1', 'image_2', 'image_3'
    mime_type: Optional[str] = "image/png"
    file_size_bytes: Optional[int] = 0
    source_evidence_id: Optional[str] = None
    section_key: Optional[str] = None
    field_key: Optional[str] = None
    attribution: Optional[str] = "Synthesized via ARM Technical Visual Engine; Open Academic Commons"
    license_info: Optional[str] = "CC-BY-4.0 / Academic Open"
    metadata: Optional[Dict[str, Any]] = None


class ReportAssetResponseDTO(ReportAssetCreateDTO):
    id: str
    report_id: Optional[str] = None
    project_id: str
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


