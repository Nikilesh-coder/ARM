"""
ReportForge AI - Integrations Router
Exposes secure, sanitized endpoints for monitoring, validating, and testing backend integrations.
SECURITY GUARANTEE: Never exposes API keys, tokens, or credentials in responses or logs.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from apps.api.core.auth import get_current_user_optional
from apps.api.schemas.integration import (
    IntegrationItemDTO,
    IntegrationValidationResultDTO,
    IntegrationsOverviewDTO,
    CanvaExportRequestDTO,
    CanvaExportResponseDTO,
)
from apps.api.services.integration_service import integration_service
from apps.api.core.logging import get_logger

logger = get_logger("routers.integrations")

router = APIRouter(prefix="/integrations", tags=["Integrations & Providers"])


@router.get(
    "/status",
    response_model=IntegrationsOverviewDTO,
    summary="Get sanitized status for all ARM backend integrations",
    description="Inspects backend configuration for AI model, image provider, document engine, and Canva. Never returns secret keys.",
)
def get_integrations_status(
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Returns sanitized configuration statuses for all 4 integration categories."""
    return integration_service.get_all_statuses()


@router.get(
    "/{integration_id}",
    response_model=IntegrationItemDTO,
    summary="Get status for a specific integration",
)
def get_integration_by_id(
    integration_id: str,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Returns sanitized configuration status for a specific integration."""
    item = integration_service.get_status(integration_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found. Supported IDs: ai, image, document, canva.",
        )
    return item


@router.post(
    "/{integration_id}/validate",
    response_model=IntegrationValidationResultDTO,
    summary="Validate and test an integration connection",
    description="Validates environment configuration and performs connectivity check. Returns actionable error if unavailable.",
)
def validate_integration(
    integration_id: str,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Executes live configuration validation for the specified integration."""
    return integration_service.validate(integration_id)


@router.post(
    "/validate-all",
    response_model=List[IntegrationValidationResultDTO],
    summary="Validate all backend integrations",
)
def validate_all_integrations(
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Validates all 4 integration categories simultaneously."""
    return integration_service.validate_all()


@router.post(
    "/canva/export",
    response_model=CanvaExportResponseDTO,
    summary="Export report to Canva (Optional)",
    description="Initiates export to Canva. If Canva is unconfigured, returns an explicit error without fabricating results.",
)
def export_to_canva(
    req: CanvaExportRequestDTO,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Dispatches Canva export or returns clear error if Canva credentials are not set."""
    return integration_service.export_to_canva(req)
