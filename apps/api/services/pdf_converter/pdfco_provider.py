"""
ARM — PDF.co PDF to DOCX External Provider
Integrates with PDF.co REST API for PDF-to-DOCX conversions.
Credentials managed via PDFCO_API_KEY environment variable.
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

logger = get_logger("service.pdf_converter.pdfco")

PDFCO_UPLOAD_ENDPOINT = "https://api.pdf.co/v1/file/upload"
PDFCO_CONVERT_ENDPOINT = "https://api.pdf.co/v1/pdf/convert/to/doc"


class PdfCoPdfConverterProvider(BasePdfConverterProvider):
    """External PDF to DOCX converter provider using PDF.co API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("PDFCO_API_KEY") or os.getenv("PDF_CO_API_KEY")

    @property
    def name(self) -> str:
        return "pdfco"

    @property
    def api_key(self) -> Optional[str]:
        if not self._api_key:
            self._api_key = os.getenv("PDFCO_API_KEY") or os.getenv("PDF_CO_API_KEY")
        return self._api_key

    def is_available(self) -> bool:
        """Available only when a non-empty API key is configured."""
        key = self.api_key
        return bool(key and len(key.strip()) > 5)

    def convert(
        self,
        pdf_path: str,
        output_docx_path: str,
    ) -> ConversionResult:
        """Executes PDF.co conversion."""
        if not self.is_available():
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error="PDF.co API key is not configured or missing.",
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

        headers = {"x-api-key": self.api_key}

        try:
            # 1. Upload temporary file to PDF.co
            logger.info(f"[PDF.CO] Uploading '{pdf_path}' to PDF.co...")
            t_up_start = time.perf_counter()
            with open(pdf_path, "rb") as f:
                up_resp = requests.post(
                    PDFCO_UPLOAD_ENDPOINT,
                    headers=headers,
                    files={"file": (os.path.basename(pdf_path), f)},
                    timeout=60,
                )
            t_up_end = time.perf_counter()
            timing.upload_sec = round(t_up_end - t_up_start, 3)

            if up_resp.status_code != 200 or up_resp.json().get("error", True):
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error=f"PDF.co upload failed: {up_resp.text[:200]}",
                )

            uploaded_file_url = up_resp.json().get("url")

            # 2. Convert to DOCX
            logger.info(f"[PDF.CO] Requesting DOCX conversion from PDF.co...")
            t_conv_start = time.perf_counter()
            conv_payload = {
                "url": uploaded_file_url,
                "name": os.path.basename(output_docx_path),
                "async": False,
            }
            conv_resp = requests.post(
                PDFCO_CONVERT_ENDPOINT,
                headers=headers,
                json=conv_payload,
                timeout=90,
            )
            t_conv_end = time.perf_counter()
            timing.conversion_sec = round(t_conv_end - t_conv_start, 3)

            conv_data = conv_resp.json()
            if conv_resp.status_code != 200 or conv_data.get("error", True):
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error=f"PDF.co convert failed: {conv_resp.text[:200]}",
                )

            result_url = conv_data.get("url")
            if not result_url:
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error="No download URL returned by PDF.co.",
                )

            # 3. Download DOCX
            t_dl_start = time.perf_counter()
            dl_resp = requests.get(result_url, timeout=45)
            t_dl_end = time.perf_counter()
            timing.download_sec = round(t_dl_end - t_dl_start, 3)

            with open(output_docx_path, "wb") as f_out:
                f_out.write(dl_resp.content)

            timing.total_sec = round(time.perf_counter() - t_start, 3)

            return ConversionResult(
                success=True,
                docx_path=output_docx_path,
                docx_bytes=dl_resp.content,
                provider=self.name,
                timing=timing,
            )

        except Exception as e:
            logger.error(f"[PDF.CO] Conversion failed: {e}")
            timing.total_sec = round(time.perf_counter() - t_start, 3)
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                timing=timing,
                error=str(e),
            )
