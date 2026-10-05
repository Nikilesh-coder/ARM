"""
ReportForge AI - Assets & Automatic Image System Router
Exposes endpoints for automatic image asset determination, generation, validation, and serving.
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse

from apps.api.core.auth import get_current_user_optional
from apps.api.core.logging import get_logger
from apps.api.schemas.asset import (
    DetermineImageRequirementsRequestDTO,
    DetermineImageRequirementsResponseDTO,
    AutomaticImagePipelineRequestDTO,
    AutomaticImagePipelineResponseDTO,
    ReportAssetItemDTO,
)
from apps.api.services.image_system import automatic_image_pipeline_service

router = APIRouter(prefix="/projects", tags=["Image Assets"])
logger = get_logger("assets.router")


@router.post("/{project_id}/assets/determine-requirements", response_model=DetermineImageRequirementsResponseDTO)
def determine_image_requirements(
    project_id: str,
    dto: DetermineImageRequirementsRequestDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Analyzes project topic, section, description, and template field requirements
    to determine the exact type of image required for each template image field.
    """
    try:
        return automatic_image_pipeline_service.determine_requirements(
            project_title=dto.project_title,
            project_description=dto.project_description,
            template_id=dto.template_id,
            image_fields=dto.image_fields,
        )
    except Exception as e:
        logger.error(f"Error determining image requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to determine image requirements: {str(e)}"
        )


@router.post("/{project_id}/automatic-images", response_model=AutomaticImagePipelineResponseDTO)
@router.post("/{project_id}/assets/pipeline", response_model=AutomaticImagePipelineResponseDTO)
def run_automatic_image_pipeline(
    project_id: str,
    dto: AutomaticImagePipelineRequestDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):

    """
    Executes the full automatic image asset pipeline:
    1. Determine required images.
    2. Search/generate suitable images (with open licensing and attribution).
    3. Validate image dimensions and magic bytes.
    4. Store asset to disk/storage.
    5. Create ReportAsset records.
    6. Map asset to template image fields for document replacement.
    """
    dto.project_id = project_id
    try:
        return automatic_image_pipeline_service.run_pipeline(req=dto, user=user)
    except Exception as e:
        logger.error(f"Error executing automatic image pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automatic image pipeline failed: {str(e)}"
        )


@router.get("/{project_id}/assets", response_model=List[ReportAssetItemDTO])
def list_project_assets(
    project_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieves all ReportAsset records for a project, including license and attribution info."""
    return automatic_image_pipeline_service.list_project_assets(project_id)


@router.get("/{project_id}/assets/{asset_id}/file")
def get_asset_file(
    project_id: str,
    asset_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Serves the raw image file for a project asset."""
    assets = automatic_image_pipeline_service.list_project_assets(project_id)
    target = next((a for a in assets if a.id == asset_id), None)
    if not target or not target.storage_path or not os.path.exists(target.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset file not found.")
    return FileResponse(target.storage_path, media_type=target.mime_type, filename=target.file_name)
