"""
ARM — CloudConvert PDF to DOCX External Provider
Integrates with CloudConvert API v2 for high-fidelity document conversion.
Strictly isolates credentials in environment variables (CLOUDCONVERT_API_KEY).
Measures and logs precise external upload, conversion, and download timings.
"""

import os
import time
from typing import Optional, Dict, Any
import requests

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from apps.api.services.pdf_converter.base import (
    BasePdfConverterProvider,
    ConversionTiming,
    ConversionResult,
)

logger = get_logger("service.pdf_converter.cloudconvert")

CLOUDCONVERT_API_BASE = "https://api.cloudconvert.com/v2"


class CloudConvertPdfConverterProvider(BasePdfConverterProvider):
    """External PDF to DOCX converter provider using CloudConvert REST API v2."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("CLOUDCONVERT_API_KEY")

    @property
    def name(self) -> str:
        return "cloudconvert"

    @property
    def api_key(self) -> Optional[str]:
        if not self._api_key:
            self._api_key = os.getenv("CLOUDCONVERT_API_KEY")
        return self._api_key

    def is_available(self) -> bool:
        """Available only when a non-empty CLOUDCONVERT_API_KEY is configured."""
        key = self.api_key
        return bool(key and len(key.strip()) > 5)

    def convert(
        self,
        pdf_path: str,
        output_docx_path: str,
    ) -> ConversionResult:
        """
        Executes complete CloudConvert conversion lifecycle:
        1. Create Conversion Job (import/upload -> convert -> export/url)
        2. Upload source PDF (Timing: External upload)
        3. Wait for conversion (Timing: External conversion)
        4. Download resulting DOCX (Timing: DOCX download)
        5. Log detailed timing breakdown
        """
        if not self.is_available():
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error="CloudConvert API key is not configured or missing.",
            )

        if not os.path.exists(pdf_path):
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                error=f"Source PDF file does not exist: {pdf_path}",
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)
        filename = os.path.basename(pdf_path)
        logger.info(f"[CLOUDCONVERT] Initiating job for '{filename}'")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timing = ConversionTiming()
        t_overall_start = time.perf_counter()

        try:
            # 1. Create Job with upload, convert, export tasks
            job_payload = {
                "tasks": {
                    "import-file": {
                        "operation": "import/upload",
                    },
                    "convert-file": {
                        "operation": "convert",
                        "input": "import-file",
                        "input_format": "pdf",
                        "output_format": "docx",
                    },
                    "export-file": {
                        "operation": "export/url",
                        "input": "convert-file",
                        "inline": False,
                        "archive_multiple_files": False,
                    },
                },
                "tag": f"arm-template-{int(time.time())}",
            }

            resp = requests.post(
                f"{CLOUDCONVERT_API_BASE}/jobs",
                headers=headers,
                json=job_payload,
                timeout=30,
            )

            if resp.status_code not in (200, 201):
                err_text = resp.text[:400]
                logger.error(f"[CLOUDCONVERT] Job creation failed ({resp.status_code}): {err_text}")
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    error=f"CloudConvert job creation error ({resp.status_code}): {err_text}",
                )

            job_data = resp.json().get("data", {})
            job_id = job_data.get("id")
            tasks = job_data.get("tasks", [])

            # Locate upload task
            upload_task = next((t for t in tasks if t.get("name") == "import-file"), None)
            if not upload_task or not upload_task.get("result", {}).get("form"):
                # Re-fetch task details if form is not yet ready
                upload_task_id = upload_task.get("id") if upload_task else None
                if upload_task_id:
                    t_resp = requests.get(f"{CLOUDCONVERT_API_BASE}/tasks/{upload_task_id}", headers=headers, timeout=20)
                    if t_resp.status_code == 200:
                        upload_task = t_resp.json().get("data", {})

            upload_form = upload_task.get("result", {}).get("form") if upload_task else None
            if not upload_form or not upload_form.get("url"):
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    error="CloudConvert did not return upload form URL.",
                )

            # 2. Upload PDF file
            t_upload_start = time.perf_counter()
            form_url = upload_form.get("url")
            form_params = upload_form.get("parameters", {})

            with open(pdf_path, "rb") as f_in:
                files = {"file": (filename, f_in, "application/pdf")}
                up_resp = requests.post(form_url, data=form_params, files=files, timeout=90)

            if up_resp.status_code not in (200, 201, 204):
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    error=f"CloudConvert upload failed with status {up_resp.status_code}",
                )

            t_upload_end = time.perf_counter()
            timing.upload_sec = round(t_upload_end - t_upload_start, 3)

            # 3. Wait for conversion to finish
            t_conv_start = time.perf_counter()
            job_status = "processing"
            max_wait_seconds = 180
            poll_interval = 2.0
            start_poll = time.time()
            finished_job_data = None

            while time.time() - start_poll < max_wait_seconds:
                # Use long-polling wait endpoint where available
                wait_resp = requests.get(
                    f"{CLOUDCONVERT_API_BASE}/jobs/{job_id}",
                    headers=headers,
                    timeout=20,
                )
                if wait_resp.status_code == 200:
                    current_job = wait_resp.json().get("data", {})
                    job_status = current_job.get("status")
                    if job_status in ("finished", "error"):
                        finished_job_data = current_job
                        break

                time.sleep(poll_interval)

            t_conv_end = time.perf_counter()
            timing.conversion_sec = round(t_conv_end - t_conv_start, 3)

            if job_status != "finished" or not finished_job_data:
                err_msg = f"CloudConvert job {job_id} did not finish cleanly (status: {job_status})."
                logger.error(f"[CLOUDCONVERT] {err_msg}")
                timing.total_sec = round(time.perf_counter() - t_overall_start, 3)
                timing.log_timing_summary(self.name)
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error=err_msg,
                )

            # 4. Download converted DOCX from export task
            t_down_start = time.perf_counter()
            finished_tasks = finished_job_data.get("tasks", [])
            export_task = next((t for t in finished_tasks if t.get("name") == "export-file"), None)
            if not export_task:
                export_task = next((t for t in finished_tasks if t.get("operation") == "export/url"), None)

            export_files = export_task.get("result", {}).get("files", []) if export_task else []
            if not export_files or not export_files[0].get("url"):
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error="CloudConvert export URL not found in completed job.",
                )

            download_url = export_files[0]["url"]
            dl_resp = requests.get(download_url, timeout=60)
            if dl_resp.status_code != 200:
                return ConversionResult(
                    success=False,
                    docx_path=output_docx_path,
                    provider=self.name,
                    timing=timing,
                    error=f"Failed downloading converted DOCX ({dl_resp.status_code})",
                )

            with open(output_docx_path, "wb") as f_out:
                f_out.write(dl_resp.content)

            t_down_end = time.perf_counter()
            timing.download_sec = round(t_down_end - t_down_start, 3)
            timing.total_sec = round(time.perf_counter() - t_overall_start, 3)

            # 5. Output timing log in the required exact format
            logger.info(f"External upload: {timing.upload_sec:.2f} sec")
            logger.info(f"External conversion: {timing.conversion_sec:.2f} sec")
            logger.info(f"DOCX download: {timing.download_sec:.2f} sec")
            logger.info(f"Total PDF → DOCX: {timing.total_sec:.2f} sec")

            return ConversionResult(
                success=True,
                docx_path=output_docx_path,
                docx_bytes=dl_resp.content,
                provider=self.name,
                timing=timing,
            )

        except Exception as e:
            logger.error(f"[CLOUDCONVERT] Exception during conversion: {e}")
            timing.total_sec = round(time.perf_counter() - t_overall_start, 3)
            return ConversionResult(
                success=False,
                docx_path=output_docx_path,
                provider=self.name,
                timing=timing,
                error=str(e),
            )
