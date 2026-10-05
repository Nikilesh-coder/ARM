"""
ReportForge AI - Automatic Image System Schemas
Defines structured models for determining image needs, validation, acquisition, and ReportAsset tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ImageRequirementDTO(BaseModel):
    template_field: str  # e.g., 'image_1', 'image_2', 'image_3'
    section_key: str     # e.g., 'Chapter 2: System Methodology'
    field_label: str
    asset_type: str      # 'architecture_diagram', 'implementation_setup', 'empirical_chart', 'technical_photo'
    title: str
    description: str
    suggested_prompt: str
    target_dimensions: Dict[str, Any] = Field(default_factory=lambda: {"width": 800, "height": 500, "dpi": 300, "aspect_ratio": "16:9"})
    acquisition_mode: str = "diagram_engine"  # 'diagram_engine', 'chart_engine', 'external_api', 'evidence'
    license_type: str = "CC-BY-4.0 / Academic Open"
    attribution: str = "Synthesized via ARM Technical Visual Engine; Open Academic Commons"


class ImageValidationResultDTO(BaseModel):
    is_valid: bool
    mime_type: str
    width: int
    height: int
    dpi: int
    file_size_bytes: int
    aspect_ratio: str
    passed_checks: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ReportAssetItemDTO(BaseModel):
    id: str
    project_id: str
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    template_field: str
    asset_type: str
    source: str
    title: str
    caption: Optional[str] = None
    description: Optional[str] = None
    file_name: str
    storage_path: str
    file_url: Optional[str] = None
    mime_type: str = "image/png"
    file_size_bytes: int = 0
    attribution: str
    license_info: str
    section_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DetermineImageRequirementsRequestDTO(BaseModel):
    project_id: Optional[str] = None
    project_title: str
    project_description: str
    template_id: Optional[str] = "00000000-0000-0000-0000-000000000001"
    image_fields: Optional[List[str]] = None  # None means all template image fields


class DetermineImageRequirementsResponseDTO(BaseModel):
    project_title: str
    total_image_fields: int
    requirements: List[ImageRequirementDTO]


class AutomaticImagePipelineRequestDTO(BaseModel):
    project_id: str
    report_id: Optional[str] = None
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    template_id: Optional[str] = "00000000-0000-0000-0000-000000000001"
    target_fields: Optional[List[str]] = None  # Optional subset of image fields to process
    preferred_provider: Optional[str] = None  # 'internal_engine', 'unsplash', 'dalle', 'gemini'
    force_regenerate: bool = False


class PipelineStepResultDTO(BaseModel):
    template_field: str
    status: str  # 'completed', 'failed', 'skipped'
    asset: Optional[ReportAssetItemDTO] = None
    validation: Optional[ImageValidationResultDTO] = None
    error: Optional[str] = None


class AutomaticImagePipelineResponseDTO(BaseModel):
    project_id: str
    status: str  # 'completed', 'partial_failure', 'failed'
    total_images_processed: int
    successful_images_count: int
    failed_images_count: int
    assets: List[ReportAssetItemDTO] = Field(default_factory=list)
    field_mapping: Dict[str, str] = Field(default_factory=dict)  # field_name -> storage_path/URL
    step_results: List[PipelineStepResultDTO] = Field(default_factory=list)
    completed_at: str
