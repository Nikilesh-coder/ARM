"""
ReportForge AI - Project & Evidence Schemas
Stage 5: Project Information + Evidence Locker
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProjectCreateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    project_name: Optional[str] = None
    title: Optional[str] = None
    report_title: Optional[str] = None
    report_type: Optional[str] = None
    project_type: Optional[str] = "capstone"
    description: Optional[str] = None
    academic_year: Optional[str] = "2026-2027"
    department: Optional[str] = None
    institution: Optional[str] = None
    semester: Optional[str] = None
    guide_name: Optional[str] = None
    abstract_summary: Optional[str] = None
    problem_statement: Optional[str] = None
    objectives: Optional[str] = None
    scope: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    additional_notes: Optional[str] = None
    instructions: Optional[str] = None
    template_id: Optional[str] = None
    is_team_project: Optional[bool] = False
    target_page_count: Optional[int] = 30
    tech_stack: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None


class ProjectUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_name: Optional[str] = None
    title: Optional[str] = None
    report_title: Optional[str] = None
    report_type: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None
    academic_year: Optional[str] = None
    department: Optional[str] = None
    institution: Optional[str] = None
    semester: Optional[str] = None
    guide_name: Optional[str] = None
    abstract_summary: Optional[str] = None
    problem_statement: Optional[str] = None
    objectives: Optional[str] = None
    scope: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    additional_notes: Optional[str] = None
    instructions: Optional[str] = None
    template_id: Optional[str] = None
    is_team_project: Optional[bool] = None
    target_page_count: Optional[int] = None
    tech_stack: Optional[List[str]] = None
    status: Optional[str] = None


class ProjectResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: Optional[str] = None
    owner_id: Optional[str] = None
    project_name: Optional[str] = None
    title: Optional[str] = None
    report_title: Optional[str] = None
    report_type: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None
    academic_year: Optional[str] = None
    department: Optional[str] = None
    institution: Optional[str] = None
    semester: Optional[str] = None
    guide_name: Optional[str] = None
    abstract_summary: Optional[str] = None
    problem_statement: Optional[str] = None
    objectives: Optional[str] = None
    scope: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    additional_notes: Optional[str] = None
    instructions: Optional[str] = None
    template_id: Optional[str] = None
    is_team_project: Optional[bool] = False
    target_page_count: Optional[int] = 30
    tech_stack: List[str] = Field(default_factory=list)
    status: str = "draft"
    template_name: Optional[str] = None
    generation_status: Optional[str] = "not_started"
    latest_report: Optional[Dict[str, Any]] = None
    latest_job_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Project Members DTOs ---

class ProjectMemberCreateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1)
    roll_number: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "Member"


class ProjectMemberUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, min_length=1)
    roll_number: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class ProjectMemberResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    project_id: str
    user_id: Optional[str] = None
    name: str
    roll_number: Optional[str] = None
    email: Optional[str] = None
    role: str = "Member"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Evidence Locker DTOs ---

class EvidenceResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    project_id: str
    user_id: Optional[str] = None
    file_name: str
    file_type: str = "evidence"
    mime_type: Optional[str] = None
    file_size_bytes: int = 0
    storage_path: str
    sha256_hash: Optional[str] = None
    category: str = "other"
    description: Optional[str] = None
    upload_status: str = "ready"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EvidenceUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: Optional[str] = None
    description: Optional[str] = None


# --- Project Readiness DTO ---

class ProjectReadinessDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    template_locked: bool
    info_completed: bool
    evidence_count: int
    members_count: int
    is_ready_for_generation: bool
    missing_fields: List[str] = Field(default_factory=list)
    completion_percentage: int = 0
