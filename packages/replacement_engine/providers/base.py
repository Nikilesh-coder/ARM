"""
ARM - Document Generation Provider Interface
Defines the abstract interface for document generation engines (Internal OpenXML, Carbone Cloud, etc.)
allowing ARM to plug in external engines without permanent dependency on any single provider.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ProviderGenerationResult(BaseModel):
    """Result returned by a document generation provider."""
    success: bool
    status: str  # "completed", "failed", "unconfigured", "unreachable"
    provider: str
    output_path: Optional[str] = None
    output_format: str = "docx"
    file_size_bytes: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentProvider(ABC):
    """
    Abstract Document Provider interface for ARM.
    Accepts:
    - Template (file path)
    - Structured report data
    - Image assets
    Returns:
    - Generated document
    - Generation status
    - Error information
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the unique identifier of the provider (e.g. 'internal', 'carbone')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider is fully configured with required credentials."""
        pass

    @abstractmethod
    def generate(
        self,
        template_path: str,
        data: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        output_format: str = "docx",
    ) -> ProviderGenerationResult:
        """
        Generates a document from the template, structured data, and image assets.
        Must never fake successful documents if generation cannot be performed.
        """
        pass
