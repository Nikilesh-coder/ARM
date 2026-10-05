"""
ReportForge AI - Job Schemas
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class JobStatusDTO(BaseModel):
    job_id: str
    job_type: str
    status: str  # queued, running, processing, completed, failed, cancelled
    progress_percentage: Optional[int] = 0
    progress: Optional[int] = 0
    current_stage: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    report_id: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
