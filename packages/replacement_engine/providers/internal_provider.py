"""
ARM - Internal Document Generation Provider
Default, built-in document provider for ARM.
Executes precision in-place OpenXML and PDF template replacement with zero external dependencies.
"""

import os
from typing import Dict, Any, Optional

from apps.api.core.logging import get_logger
from packages.replacement_engine.docx_engine import DocxTemplateReplacementEngine
from packages.replacement_engine.pdf_engine import PdfTemplateReplacementEngine
from packages.replacement_engine.providers.base import (
    DocumentProvider,
    ProviderGenerationResult,
)
from packages.document_engine.converter import pdf_converter_service

logger = get_logger("document_provider.internal")


class InternalDocumentProvider(DocumentProvider):
    """
    Core built-in ARM Document Provider.
    Operates server-side with zero external cloud dependencies.
    Preserves 100% of the college master template formatting and geometry.
    """

    def __init__(self):
        self._docx_engine = DocxTemplateReplacementEngine()
        self._pdf_engine = PdfTemplateReplacementEngine()

    def get_provider_name(self) -> str:
        return "internal"

    def is_configured(self) -> bool:
        """The internal provider is always fully configured and available out-of-the-box."""
        return True

    def generate(
        self,
        template_path: str,
        data: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        output_format: str = "docx",
    ) -> ProviderGenerationResult:
        """
        Executes document replacement using ARM's precision engines:
        - DOCX templates: DocxTemplateReplacementEngine (+ optional PDF conversion)
        - PDF templates: PdfTemplateReplacementEngine
        """
        if not os.path.exists(template_path):
            return ProviderGenerationResult(
                success=False,
                status="failed",
                provider=self.get_provider_name(),
                output_format=output_format,
                errors=[f"Template file not found at: '{template_path}'"],
            )

        is_pdf_template = template_path.lower().endswith(".pdf")
        requested_pdf = output_format.lower() in ("pdf", ".pdf")

        if is_pdf_template:
            res = self._pdf_engine.replace(
                template_path=template_path,
                field_values=data,
                image_assets=image_assets,
                output_path=output_path,
            )
            if not res.success:
                return ProviderGenerationResult(
                    success=False,
                    status="failed",
                    provider=self.get_provider_name(),
                    output_format="pdf",
                    errors=[e.reason for e in res.errors],
                    warnings=res.warnings,
                )
            return ProviderGenerationResult(
                success=True,
                status="completed",
                provider=self.get_provider_name(),
                output_path=res.output_pdf_path,
                output_format="pdf",
                file_size_bytes=os.path.getsize(res.output_pdf_path) if res.output_pdf_path and os.path.exists(res.output_pdf_path) else 0,
                metadata=res.metadata,
            )

        # DOCX Template
        res = self._docx_engine.replace(
            template_path=template_path,
            field_values=data,
            image_assets=image_assets,
            output_path=output_path,
        )

        if not res.success:
            return ProviderGenerationResult(
                success=False,
                status="failed",
                provider=self.get_provider_name(),
                output_format="docx",
                errors=[e.reason for e in res.errors],
                warnings=res.warnings,
            )

        final_output_path = res.output_docx_path

        # If PDF was requested, convert from the completed DOCX
        if requested_pdf and final_output_path:
            pdf_path = final_output_path.replace(".docx", ".pdf")
            try:
                pdf_converter_service.convert(final_output_path, pdf_path)
                final_output_path = pdf_path
                output_format = "pdf"
            except Exception as e:
                logger.warning(f"PDF conversion warning in internal provider: {e}")

        file_size = os.path.getsize(final_output_path) if final_output_path and os.path.exists(final_output_path) else 0

        return ProviderGenerationResult(
            success=True,
            status="completed",
            provider=self.get_provider_name(),
            output_path=final_output_path,
            output_format=output_format,
            file_size_bytes=file_size,
            warnings=res.warnings,
            metadata=res.metadata,
        )
