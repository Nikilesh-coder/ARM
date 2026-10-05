"""
ReportForge AI - AI Report Agent Router
Endpoints for structured AI academic report content synthesis, status polling, and validation.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from apps.api.schemas.agent import (
    AIReportAgentInputDTO,
    AIReportAgentOutputDTO,
    AgentJobStatusDTO,
    ValidationReportDTO,
)
from apps.api.services.ai_report_agent import ai_report_agent_service
from apps.api.core.auth import get_current_user_optional
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger

router = APIRouter(prefix="/agent", tags=["AI Report Agent"])
logger = get_logger("agent.router")


@router.post("/generate-report-content", response_model=AIReportAgentOutputDTO)
def generate_report_content(
    dto: AIReportAgentInputDTO,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Executes the ARM AI Report Agent pipeline:
    1. 'thinking': parses project facts, resolves Master Template fields, and grounds evidence.
    2. 'creating': calls Gemini with strict JSON structured output matching exact fields.
    3. validates content against field types (list, text, long_text, image) and word/item budgets.
    4. returns structured JSON mapped 1:1 to template fields.
    """
    try:
        output = ai_report_agent_service.generate_report_content(input_dto=dto)

        # Optional: Save generated content if project_id is provided
        if dto.project_id:
            client = db_manager.client
            if client:
                try:
                    payload = {
                        "project_id": dto.project_id,
                        "template_id": dto.template_id,
                        "content": output.content,
                        "validation": output.validation.model_dump(),
                        "model_used": output.model_used,
                    }
                    client.table("projects").update({
                        "status": "generated",
                    }).eq("id", dto.project_id).execute()
                except Exception as e:
                    logger.warning(f"Could not persist agent content to database for project {dto.project_id}: {e}")

        return output
    except Exception as e:
        logger.error(f"Error in generate_report_content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Report Agent synthesis failed: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=AgentJobStatusDTO)
def get_agent_job_status(job_id: str):
    """Retrieves live generation status ('thinking' -> 'creating' -> 'completed')."""
    job = ai_report_agent_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent job not found.")
    return job
