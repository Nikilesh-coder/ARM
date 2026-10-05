"""
ARM Stage 10 - Base Template Replacement Engine
Defines abstract contracts, standard 7-state lifecycle, audit models,
and multi-format replacement interfaces.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# FIXED VS REPLACEABLE ELEMENTS SPECIFICATION
# The original college template is the absolute SOURCE OF TRUTH.
# ARM must NEVER modify, redesign, resize, or rebuild FIXED ELEMENTS.
# Only REPLACEABLE ELEMENTS may be modified in-place.
# ==============================================================================

FIXED_ELEMENTS = {
    "college_logo",
    "college_name",
    "university_logo",
    "department_logo",
    "page_border",
    "header",
    "footer",
    "background",
    "watermark",
    "fixed_design_image",
    "fixed_shape",
}

REPLACEABLE_ELEMENTS = {
    "project_title",
    "student_name",
    "roll_number",
    "guide_name",
    "introduction",
    "objectives",
    "problem_statement",
    "methodology",
    "technologies",
    "implementation",
    "results",
    "advantages",
    "limitations",
    "future_scope",
    "conclusion",
    "references",
    "image_1",
    "image_2",
    "image_3",
}


class ReplacementState(str, Enum):
    """
    Authoritative 7-state lifecycle for ARM Template Replacement:
    QUEUED -> ANALYZING -> GENERATING -> REPLACING -> VALIDATING -> COMPLETED / FAILED
    """
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    GENERATING = "GENERATING"
    REPLACING = "REPLACING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FieldReplacementAudit(BaseModel):
    """Detailed audit entry for every template field replacement."""
    field_name: str
    placeholder: str
    field_type: str
    replaced: bool = False
    original_snippet: Optional[str] = None
    new_snippet: Optional[str] = None
    formatting_preserved: bool = True
    error: Optional[str] = None


class ReplacementErrorDetail(BaseModel):
    """Specific error descriptor when a field replacement cannot be safely performed."""
    field: str
    reason: str


class ReplacementResult(BaseModel):
    """Result returned by the replacement engine after compiling the report."""
    success: bool
    job_id: str
    state: ReplacementState
    template_path: str
    output_docx_path: Optional[str] = None
    output_pdf_path: Optional[str] = None
    preview_html: Optional[str] = None
    fields_replaced: int = 0
    total_fields: int = 0
    images_replaced: int = 0
    audit: List[FieldReplacementAudit] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ReplacementErrorDetail] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseReplacementEngine(ABC):
    """
    Abstract interface for ARM Template Replacement.
    Enables support for DOCX and future document formats (PDF, Canva, PPTX).
    """

    @abstractmethod
    def replace(
        self,
        template_path: str,
        field_values: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ReplacementResult:
        """
        Loads the template, substitutes text and image fields in-place,
        preserves typography, styles, layout and geometry, and produces the finalized document.
        """
        pass
