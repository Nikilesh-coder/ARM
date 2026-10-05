"""
ARM - Carbone Document Generation Provider
Implements the DocumentProvider interface using Carbone Cloud REST API (v4).
Accepts template, structured data, and image assets, and generates completed documents.
Strictly requires CARBONE_API_KEY in backend environment variables.
Never exposes API keys in frontend responses or client bundles.
Never produces fake successful documents.
"""

import os
import base64
import tempfile
import mimetypes
from typing import Dict, Any, Optional, List, Tuple
import httpx

from apps.api.core.logging import get_logger
from apps.api.core.config import settings
from packages.replacement_engine.providers.base import (
    DocumentProvider,
    ProviderGenerationResult,
)

logger = get_logger("document_provider.carbone")


class CarboneDocumentProvider(DocumentProvider):
    """
    Optional external document generation provider leveraging Carbone API.
    Can be swapped out or toggled without impacting core ARM architecture.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        version: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ):
        # Resolve from parameter or backend settings (NEVER exposed to frontend)
        self.api_key = api_key or settings.document_provider.carbone_api_key or os.getenv("CARBONE_API_KEY")
        self.api_url = (api_url or settings.document_provider.carbone_api_url or os.getenv("CARBONE_API_URL", "https://api.carbone.io")).rstrip("/")
        self.version = str(version or settings.document_provider.carbone_version or os.getenv("CARBONE_VERSION", "4"))
        self.timeout = timeout_seconds

    def get_provider_name(self) -> str:
        return "carbone"

    def is_configured(self) -> bool:
        """Returns True only when a non-empty CARBONE_API_KEY is present in backend environment."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def generate(
        self,
        template_path: str,
        data: Dict[str, Any],
        image_assets: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        output_format: str = "docx",
    ) -> ProviderGenerationResult:
        """
        Executes document synthesis using Carbone Cloud API:
        1. Validates configuration.
        2. Prepares structured data and encodes image assets to base64.
        3. Uploads template to Carbone.
        4. Renders document.
        5. Downloads compiled document to target output path.
        """
        # 1. Configuration check (No fake documents)
        if not self.is_configured():
            err_msg = (
                "Carbone API key is not configured. "
                "Please set the CARBONE_API_KEY environment variable in backend configuration."
            )
            logger.error(err_msg)
            return ProviderGenerationResult(
                success=False,
                status="unconfigured",
                provider=self.get_provider_name(),
                output_format=output_format,
                errors=[err_msg],
            )

        if not os.path.exists(template_path):
            err_msg = f"Template file does not exist at path: '{template_path}'"
            logger.error(err_msg)
            return ProviderGenerationResult(
                success=False,
                status="failed",
                provider=self.get_provider_name(),
                output_format=output_format,
                errors=[err_msg],
            )

        # Generate output path if omitted
        if not output_path:
            ext = output_format.lower().lstrip(".")
            tmp_dir = os.path.join(tempfile.gettempdir(), "arm_reports")
            os.makedirs(tmp_dir, exist_ok=True)
            output_path = os.path.join(tmp_dir, f"carbone_report.{ext}")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 2. Prepare structured data and image assets
        payload = self._prepare_data_payload(data, image_assets or {})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "carbone-version": self.version,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 3. Upload template
                logger.info(f"Uploading template '{os.path.basename(template_path)}' to Carbone API...")
                with open(template_path, "rb") as f_tmpl:
                    template_bytes = f_tmpl.read()

                files = {"template": (os.path.basename(template_path), template_bytes)}
                upload_res = client.post(f"{self.api_url}/template", headers=headers, files=files)

                if upload_res.status_code == 401:
                    err_msg = "Carbone API authentication failed (401 Unauthorized). Please verify CARBONE_API_KEY."
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                if upload_res.status_code != 200:
                    err_detail = upload_res.text
                    try:
                        err_json = upload_res.json()
                        err_detail = err_json.get("error") or err_json.get("message") or upload_res.text
                    except Exception:
                        pass
                    err_msg = f"Carbone template upload failed (status {upload_res.status_code}): {err_detail}"
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                upload_data = upload_res.json()
                template_id = upload_data.get("data", {}).get("templateId")
                if not template_id:
                    err_msg = f"Carbone API did not return a valid templateId: {upload_res.text}"
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                logger.info(f"Template successfully uploaded to Carbone. templateId={template_id}")

                # 4. Render template
                render_payload = {
                    "data": payload,
                    "convertTo": output_format.lower().lstrip("."),
                }
                render_res = client.post(
                    f"{self.api_url}/render/{template_id}",
                    headers=headers,
                    json=render_payload,
                )

                if render_res.status_code != 200:
                    err_detail = render_res.text
                    try:
                        err_json = render_res.json()
                        err_detail = err_json.get("error") or err_json.get("message") or render_res.text
                    except Exception:
                        pass
                    err_msg = f"Carbone template render failed (status {render_res.status_code}): {err_detail}"
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                render_data = render_res.json()
                render_id = render_data.get("data", {}).get("renderId")
                if not render_id:
                    err_msg = f"Carbone API did not return a valid renderId: {render_res.text}"
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                logger.info(f"Render job completed on Carbone. renderId={render_id}")

                # 5. Download rendered document
                download_res = client.get(f"{self.api_url}/render/{render_id}", headers=headers)
                if download_res.status_code != 200:
                    err_msg = f"Failed to download rendered document from Carbone (status {download_res.status_code}): {download_res.text}"
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                doc_bytes = download_res.content
                if not doc_bytes or len(doc_bytes) == 0:
                    err_msg = "Carbone returned a zero-byte document."
                    logger.error(err_msg)
                    return ProviderGenerationResult(
                        success=False,
                        status="failed",
                        provider=self.get_provider_name(),
                        output_format=output_format,
                        errors=[err_msg],
                    )

                with open(output_path, "wb") as f_out:
                    f_out.write(doc_bytes)

                file_size = os.path.getsize(output_path)
                logger.info(f"Carbone document generated successfully at: {output_path} ({file_size} bytes)")

                return ProviderGenerationResult(
                    success=True,
                    status="completed",
                    provider=self.get_provider_name(),
                    output_path=output_path,
                    output_format=output_format,
                    file_size_bytes=file_size,
                    metadata={
                        "carbone_template_id": template_id,
                        "carbone_render_id": render_id,
                        "output_format": output_format,
                    },
                )

        except httpx.RequestError as exc:
            err_msg = f"Carbone API connection error: {str(exc)}"
            logger.error(err_msg)
            return ProviderGenerationResult(
                success=False,
                status="unreachable",
                provider=self.get_provider_name(),
                output_format=output_format,
                errors=[err_msg],
            )
        except Exception as ex:
            err_msg = f"Carbone generation unexpected failure: {str(ex)}"
            logger.error(err_msg)
            return ProviderGenerationResult(
                success=False,
                status="failed",
                provider=self.get_provider_name(),
                output_format=output_format,
                errors=[err_msg],
            )

    def _prepare_data_payload(
        self,
        data: Dict[str, Any],
        image_assets: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Structures the data payload for Carbone template rendering:
        - Converts local image files to base64 data URIs for dynamic image tags.
        - Provides both top-level variables and nested 'd' object.
        """
        payload: Dict[str, Any] = dict(data)

        # Process image assets into base64 data URIs
        for slot_key, asset_val in image_assets.items():
            img_path = None
            if isinstance(asset_val, dict):
                img_path = asset_val.get("storage_path") or asset_val.get("file_path")
            elif isinstance(asset_val, str) and os.path.exists(asset_val):
                img_path = asset_val

            if img_path and os.path.exists(img_path):
                data_uri = self._encode_image_as_data_uri(img_path)
                if data_uri:
                    payload[slot_key] = data_uri

        # Duplicate into nested 'd' container for standard Carbone {d.field} tags
        payload["d"] = dict(payload)
        return payload

    def _encode_image_as_data_uri(self, image_path: str) -> Optional[str]:
        """Reads a local image file and converts it into a base64 Data URI."""
        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/png"
            with open(image_path, "rb") as f_img:
                b64_content = base64.b64encode(f_img.read()).decode("utf-8")
            return f"data:{mime_type};base64,{b64_content}"
        except Exception as e:
            logger.warning(f"Failed to encode image {image_path} to base64: {e}")
            return None
