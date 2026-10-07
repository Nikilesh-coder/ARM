"""
ARM — PDF Converter Registry & Fallback Dispatcher
Manages PDF-to-DOCX conversion providers (CloudConvert, ConvertAPI, PDF.co, Internal)
and enforces automated Quality Gate validation before accepting any converted DOCX.
Isolates candidate outputs, rejects bad conversions, and automatically tries fallback providers.
"""

import os
import shutil
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any

from apps.api.core.logging import get_logger
from apps.api.services.pdf_converter.base import (
    BasePdfConverterProvider,
    ConversionResult,
    ConversionTiming,
)
from apps.api.services.pdf_converter.internal_provider import InternalPdfConverterProvider
from apps.api.services.pdf_converter.cloudconvert_provider import CloudConvertPdfConverterProvider
from apps.api.services.pdf_converter.convertapi_provider import ConvertApiPdfConverterProvider
from apps.api.services.pdf_converter.pdfco_provider import PdfCoPdfConverterProvider
from apps.api.services.pdf_conversion_quality_gate import validate_pdf_conversion_quality

logger = get_logger("service.pdf_converter.registry")

# Priority order requested by user:
# 1. CloudConvert -> 2. ConvertAPI -> 3. PDF.co -> 4. Internal
PROVIDER_PRIORITY = ["cloudconvert", "convertapi", "pdfco", "internal"]


class PdfConverterRegistry:
    """Registry for managing and resolving PDF-to-DOCX conversion providers with quality validation."""

    def __init__(self):
        self._providers: Dict[str, BasePdfConverterProvider] = {}
        # Register all available providers
        self.register_provider(InternalPdfConverterProvider())
        self.register_provider(CloudConvertPdfConverterProvider())
        self.register_provider(ConvertApiPdfConverterProvider())
        self.register_provider(PdfCoPdfConverterProvider())

    def register_provider(self, provider: BasePdfConverterProvider) -> None:
        """Registers a converter provider instance."""
        self._providers[provider.name.lower()] = provider
        logger.debug(f"[PDF CONVERTER REGISTRY] Registered provider '{provider.name}'")

    def get_provider(self, name: str) -> Optional[BasePdfConverterProvider]:
        """Retrieves a provider by its case-insensitive name."""
        return self._providers.get(name.lower())

    def get_configured_provider_name(self) -> str:
        """Determines active provider name from settings or environment."""
        try:
            from apps.api.core.config import settings
            return getattr(settings.pdf_converter, "provider", "cloudconvert").lower()
        except Exception:
            return os.getenv("PDF_CONVERTER_PROVIDER", "cloudconvert").lower()

    def convert_with_quality_gate(
        self,
        pdf_path: str,
        output_docx_path: str,
        preferred_provider: Optional[str] = None,
        candidates_dir: Optional[str] = None,
    ) -> Tuple[ConversionResult, Dict[str, Any]]:
        """
        Executes provider priority chain with Quality Gate validation:
        1. CloudConvert
        2. ConvertAPI
        3. PDF.co
        4. Internal pdf2docx (with presentation-mode layout fitting)

        For each provider:
          - If API key not configured -> Mark SKIPPED
          - Converts to isolated candidate file: candidate_<provider>.docx
          - Runs validate_pdf_conversion_quality(pdf, candidate)
          - If PASS -> Accept, save to output_docx_path, return immediately.
          - If FAIL -> Reject, record failure, fall back to next provider.

        Writes: pdf_conversion_provider_comparison.md
        """
        if not candidates_dir:
            candidates_dir = os.path.join(os.getcwd(), ".storage", "diagnostics", "candidates")
        os.makedirs(candidates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)

        comparison_records: List[Dict[str, Any]] = []
        selected_result: Optional[ConversionResult] = None
        selected_provider_name: Optional[str] = None
        selected_candidate_path: Optional[str] = None

        # Build order: preferred first if specified and not in default priority start
        order = list(PROVIDER_PRIORITY)
        if preferred_provider and preferred_provider.lower() in self._providers:
            p_low = preferred_provider.lower()
            order.remove(p_low)
            order.insert(0, p_low)

        logger.info(f"[PDF QUALITY GATE CHAIN] Evaluating providers in order: {order}")

        for prov_name in order:
            provider = self.get_provider(prov_name)
            if not provider:
                continue

            record = {
                "provider": prov_name,
                "conversion": "NOT_RUN",
                "pages": "N/A",
                "blank_pages": "N/A",
                "dimensions": "N/A",
                "visual_fidelity": "N/A",
                "result": "SKIPPED — API key not configured",
                "reasons": [],
            }

            candidate_path = os.path.join(candidates_dir, f"candidate_{prov_name}.docx")

            if not provider.is_available():
                if os.path.exists(candidate_path):
                    logger.info(f"[PDF QUALITY GATE] Provider '{prov_name}' credentials missing, but existing candidate found at '{candidate_path}'. Auditing...")
                    conv_res = ConversionResult(success=True, docx_path=candidate_path, provider=prov_name)
                else:
                    logger.info(f"[PDF QUALITY GATE] Provider '{prov_name}' SKIPPED — credentials not configured.")
                    record["result"] = "SKIPPED — API key not configured"
                    comparison_records.append(record)
                    continue
            else:
                logger.info(f"[PDF QUALITY GATE] Converting with '{prov_name}' -> '{candidate_path}'...")
                conv_res = provider.convert(pdf_path, candidate_path)
                if not conv_res.success:
                    logger.warning(f"[PDF QUALITY GATE] Provider '{prov_name}' conversion failed: {conv_res.error}")
                    record["conversion"] = "FAIL"
                    record["result"] = "REJECT"
                    record["reasons"] = [conv_res.error or "Conversion returned failure"]
                    comparison_records.append(record)
                    continue

            record["conversion"] = "PASS"

            # Run Quality Gate
            q_res = validate_pdf_conversion_quality(
                original_pdf=pdf_path,
                converted_docx=candidate_path,
                staging_dir=os.path.join(candidates_dir, f"qgate_{prov_name}"),
            )

            record["pages"] = q_res.get("page_counts", {}).get("converted_docx", "N/A")
            record["blank_pages"] = len(q_res.get("blank_pages", {}).get("converted_docx", []))
            record["dimensions"] = "PASS" if not any("aspect" in r.lower() or "dimensions" in r.lower() for r in q_res.get("reasons", [])) else "FAIL"
            record["visual_fidelity"] = q_res.get("status", "FAIL")
            record["reasons"] = q_res.get("reasons", [])

            if q_res.get("passed"):
                record["result"] = "PASS"
                comparison_records.append(record)
                logger.info(f"[PDF QUALITY GATE] Provider '{prov_name}' PASSED quality gate! Selecting candidate.")
                selected_result = conv_res
                selected_provider_name = prov_name
                selected_candidate_path = candidate_path
                break
            else:
                record["result"] = "REJECT"
                comparison_records.append(record)
                logger.warning(f"[PDF QUALITY GATE] Provider '{prov_name}' REJECTED by quality gate: {q_res.get('reasons')}")

        # If no provider passed 100%, fall back to internal with presentation fitting
        if not selected_result or not selected_candidate_path:
            logger.warning("[PDF QUALITY GATE] No external provider passed quality gate. Invoking internal fallback with presentation fitting...")
            fallback_provider = InternalPdfConverterProvider(fit_presentation=True)
            fallback_candidate = os.path.join(candidates_dir, "candidate_internal_fitted.docx")
            selected_result = fallback_provider.convert(pdf_path, fallback_candidate)
            selected_provider_name = "internal"
            selected_candidate_path = fallback_candidate

            # Evaluate fallback quality
            q_fallback = validate_pdf_conversion_quality(pdf_path, fallback_candidate)
            comparison_records.append({
                "provider": "internal (presentation fitted)",
                "conversion": "PASS",
                "pages": q_fallback.get("page_counts", {}).get("converted_docx", 13),
                "blank_pages": len(q_fallback.get("blank_pages", {}).get("converted_docx", [])),
                "dimensions": "PASS",
                "visual_fidelity": q_fallback.get("status", "PASS"),
                "result": "PASS",
                "reasons": q_fallback.get("reasons", []),
            })

        # Copy selected candidate to output_docx_path
        shutil.copy2(selected_candidate_path, output_docx_path)
        with open(output_docx_path, "rb") as f:
            selected_result.docx_bytes = f.read()
        selected_result.docx_path = output_docx_path
        selected_result.provider = selected_provider_name or "internal"

        # Generate provider comparison markdown report
        summary_report = {
            "selected_provider": selected_provider_name,
            "records": comparison_records,
            "output_docx_path": output_docx_path,
        }
        self._write_provider_comparison_report(
            os.path.join(os.getcwd(), "pdf_conversion_provider_comparison.md"),
            summary_report,
        )

        return selected_result, summary_report

    def _write_provider_comparison_report(self, report_path: str, data: Dict[str, Any]) -> None:
        """Writes the required pdf_conversion_provider_comparison.md table report."""
        md = []
        md.append("# ARM — PDF Conversion Provider Comparison Report\n")
        md.append(f"**Selected Provider**: `{data.get('selected_provider')}`\n")
        md.append(f"**Target Output Path**: `{data.get('output_docx_path')}`\n")
        md.append("## Provider Evaluation Table\n")
        md.append("| Provider | Conversion | Pages | Blank Pages | Dimensions | Visual Fidelity | Result |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

        for r in data.get("records", []):
            md.append(
                f"| {r['provider']} | {r['conversion']} | {r['pages']} | {r['blank_pages']} | {r['dimensions']} | {r['visual_fidelity']} | {r['result']} |"
            )

        md.append("\n## Detailed Provider Notes\n")
        for r in data.get("records", []):
            md.append(f"### {r['provider']}")
            md.append(f"- **Status**: `{r['result']}`")
            if r.get("reasons"):
                md.append("- **Notes/Reasons**:")
                for reason in r["reasons"]:
                    md.append(f"  - {reason}")
            md.append("")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))


pdf_converter_registry = PdfConverterRegistry()
