"""
ARM — PDF to DOCX Converter Provider Abstraction
Defines common interfaces, timing data models, and conversion results for PDF converters.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from apps.api.core.logging import get_logger

logger = get_logger("service.pdf_converter.base")


class ConversionTiming(BaseModel):
    """Detailed stage timings for PDF to DOCX conversion."""
    upload_sec: float = 0.0
    conversion_sec: float = 0.0
    download_sec: float = 0.0
    total_sec: float = 0.0

    def log_timing_summary(self, provider_name: str = "External") -> None:
        """Emits standard formatted timing logs."""
        logger.info(f"[{provider_name.upper()} TIMING] External upload: {self.upload_sec:.2f} sec")
        logger.info(f"[{provider_name.upper()} TIMING] External conversion: {self.conversion_sec:.2f} sec")
        logger.info(f"[{provider_name.upper()} TIMING] DOCX download: {self.download_sec:.2f} sec")
        logger.info(f"[{provider_name.upper()} TIMING] Total PDF → DOCX: {self.total_sec:.2f} sec")


class ConversionResult(BaseModel):
    """Normalized result returned by any PDF to DOCX converter provider."""
    success: bool
    docx_path: str
    docx_bytes: Optional[bytes] = None
    provider: str
    timing: ConversionTiming = Field(default_factory=ConversionTiming)
    stats: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    fallback_used: bool = False


class BasePdfConverterProvider(ABC):
    """Abstract base class for all PDF to DOCX conversion providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g. 'internal', 'cloudconvert')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is ready to process conversions (e.g. credentials set)."""
        pass

    @abstractmethod
    def convert(
        self,
        pdf_path: str,
        output_docx_path: str,
    ) -> ConversionResult:
        """Converts a local PDF file to a DOCX file on disk."""
        pass
