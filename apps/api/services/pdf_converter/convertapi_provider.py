"""
ARM — ConvertAPI PDF to DOCX External Provider
Integrates with ConvertAPI REST service for PDF-to-DOCX conversions.
Credentials managed via CONVERTAPI_SECRET environment variable.
"""

import os
import time
from typing import Optional
import requests

from apps.api.core.logging import get_logger
from apps.api.services.pdf_converter.base import (
    BasePdfConverterProvider,
    ConversionTiming,
    ConversionResult,
)

logger = get_logger("service.pdf_converter.convertapi")

CONVERTAPI_ENDPOINT = "https://v2.convertapi.com/convert/pdf/to/docx"


class ConvertApiPdfConverterProvider(BasePdfConverterProvider):
    """External PDF to DOCX converter provider using ConvertAPI."""

    def __init__(self, api_secret: Optional[str] = None):
        self._api_secret = api_secret or os.getenv("CONVERTAPI_SECRET") or os.getenv("CONVERTAPI_API_KEY")

    @property
    def name(self) -> str:
        return "convertapi"

    @property
    def api_secret(self) -> Optional[str]:
        if not self._api_secret:
            self._api_secret = os.getenv("CONVERTAPI_SECRET") or os.getenv("CONVERTAPI_API_KEY")
        return self._api_secret

    def is_available(self) -> bool:
        """Available only when a valid secret/key is configured."""
        sec = self.api_secret
        return bool(sec and len(sec.strip()) > 5)

    def convert(
        self,
        pdf_path: str,
        output_docx_path: str,
    ) -> ConversionResult:
        """Executes ConvertAPI conversion."""
        if not self.is_available():
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error="ConvertAPI secret is not configured or missing.",
            )

        if not os.path.exists(pdf_path):
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error=f"Source PDF file does not exist: {pdf_path}",
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)
        timing = ConversionTiming()
        t_start = time.perf_counter()

        try:
            logger.info(f"[CONVERTAPI] Sending '{pdf_path}' to ConvertAPI...")
            params = {"Secret": self.api_secret, "StoreFile": "true"}
            with open(pdf_path, "rb") as f:
                files = {"File": (os.path.basename(pdf_path), f, "application/pdf")}
                t_up_start = time.perf_counter()
                resp = requests.post(CONVERTAPI_ENDPOINT, params=params, files=files, timeout=60)
                t_up_end = time.perf_counter()
                timing.upload_sec = round(t_up_end - t_up_start, 3)

            if resp.status_code != 200:
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error=f"ConvertAPI returned status {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            file_info = data.get("Files", [{}])[0]
            file_url = file_info.get("Url")
            if not file_url:
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error="No file download URL in ConvertAPI response.",
                )

            # Download resulting DOCX
            t_dl_start = time.perf_counter()
            dl_resp = requests.get(file_url, timeout=45)
            t_dl_end = time.perf_counter()
            timing.download_sec = round(t_dl_end - t_dl_start, 3)

            with open(output_docx_path, "wb") as f_out:
                f_out.write(dl_resp.content)

            timing.total_sec = round(time.perf_counter() - t_start, 3)
            timing.conversion_sec = max(0.0, timing.total_sec - timing.upload_sec - timing.download_sec)

            return ConversionResult(
                success=True,
                docx_path=output_docx_path,
                docx_bytes=dl_resp.content,
                provider=self.name,
                timing=timing,
            )

        except Exception as e:
            logger.error(f"[CONVERTAPI] Conversion failed: {e}")
            timing.total_sec = round(time.perf_counter() - t_start, 3)
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                timing=timing,
                error=str(e),
            )
