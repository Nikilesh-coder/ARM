"""
ReportForge AI - Document Service Abstraction
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from packages.template_intelligence.schema import TemplateSchema


class DocumentService(ABC):
    """Abstract base class defining contract for document operations."""

    @abstractmethod
    def parse_template(self, docx_path: str, template_id: str = "template_custom", template_name: str = "Template") -> TemplateSchema:
        """Deterministically extracts geometry, typography, and sections from a DOCX template."""
        pass

    @abstractmethod
    def assemble_report(
        self,
        schema: TemplateSchema,
        sections: List[Dict[str, Any]],
        output_path: str,
        master_template_path: Optional[str] = None
    ) -> str:
        """Assembles structured content into a formatted DOCX matching the template schema."""
        pass

    @abstractmethod
    def convert_to_pdf(self, docx_path: str, pdf_path: str) -> str:
        """Converts DOCX to PDF preserving 100% typographic and layout fidelity."""
        pass
