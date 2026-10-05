"""
ReportForge AI - Integration Schemas
Secure, sanitized DTOs for integration status, configuration validation, and health checks.
SECURITY GUARANTEE: Never exposes API keys, tokens, or credentials.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IntegrationItemDTO(BaseModel):
    id: str = Field(..., description="Unique integration identifier: 'ai', 'image', 'document', 'canva'")
    name: str = Field(..., description="Human-readable integration name")
    category: str = Field(..., description="Integration category")
    provider: str = Field(..., description="Active or configured provider name")
    is_configured: bool = Field(..., description="True if mandatory backend environment variables are set")
    status: str = Field(..., description="'ready' | 'configured' | 'unconfigured' | 'degraded' | 'error'")
    status_message: str = Field(..., description="Descriptive status message")
    required_env_vars: List[str] = Field(default_factory=list, description="Names of required environment variables (never values)")
    optional_env_vars: List[str] = Field(default_factory=list, description="Names of optional environment variables (never values)")
    active_model_or_engine: Optional[str] = Field(None, description="Active model name or engine version")
    capabilities: List[str] = Field(default_factory=list, description="List of supported operations")
    fallback_available: bool = Field(True, description="True if ARM can fallback to native or internal engine")
    fallback_description: Optional[str] = Field(None, description="Description of fallback behavior if provider fails")
    error_details: Optional[str] = Field(None, description="Sanitized diagnostic error if configuration or ping failed")
    last_checked_at: str = Field(..., description="ISO 8601 timestamp of last status check")


class IntegrationValidationResultDTO(BaseModel):
    integration_id: str = Field(..., description="Identifier of the validated integration")
    name: str = Field(..., description="Human-readable integration name")
    is_valid: bool = Field(..., description="True if integration is operational and passes validation")
    status: str = Field(..., description="Result status: 'ready' | 'configured' | 'unconfigured' | 'degraded' | 'error'")
    message: str = Field(..., description="Validation outcome message")
    error: Optional[str] = Field(None, description="Error message if validation failed")
    remediation: Optional[str] = Field(None, description="Actionable instructions on how to resolve the issue in .env")
    can_continue_with_arm: bool = Field(True, description="Whether core ARM operations can continue despite issues")
    fallback_active: bool = Field(False, description="True if fallback engine is actively handling operations")
    checked_at: str = Field(..., description="ISO 8601 timestamp of validation check")


class IntegrationsOverviewDTO(BaseModel):
    total_integrations: int = Field(..., description="Total integration count")
    configured_count: int = Field(..., description="Count of properly configured integrations")
    unconfigured_count: int = Field(..., description="Count of unconfigured integrations")
    all_critical_operational: bool = Field(..., description="True if critical document and AI pipelines are ready")
    integrations: List[IntegrationItemDTO] = Field(default_factory=list, description="List of integration statuses")


class CanvaExportRequestDTO(BaseModel):
    project_id: str = Field(..., description="Project identifier to export")
    report_id: Optional[str] = Field(None, description="Optional report ID to export")
    design_type: str = Field("presentation", description="Target Canva design type: 'presentation' | 'report' | 'infographic'")


class CanvaExportResponseDTO(BaseModel):
    status: str = Field(..., description="'success' | 'failed' | 'unconfigured'")
    message: str = Field(..., description="Export status message")
    export_url: Optional[str] = Field(None, description="Canva design URL if export succeeded")
    error: Optional[str] = Field(None, description="Error message if export failed")
    remediation: Optional[str] = Field(None, description="Configuration remediation instructions")
