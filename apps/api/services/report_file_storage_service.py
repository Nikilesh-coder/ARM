"""
ReportForge AI - Canonical Report File Storage Service
======================================================
Single source of truth for report file persistence, atomic saves, resolution,
verification, and lifecycle management.

Guarantees:
1. Absolute canonical storage root derived from backend configuration, strictly
   anchored to WORKSPACE_ROOT (completely immune to working directory shifts).
2. Deterministic canonical paths: <storage_root>/reports/<report_id>.<extension>
3. Atomic file writes: staged in <storage_root>/reports/.staging/, flushed, verified,
   and atomically replaced onto the destination path.
4. Persistent metadata catalog in <storage_root>/reports/.metadata/<report_id>.json
   surviving FastAPI reload, uvicorn worker restarts, and server reboot.
5. Strict completion ordering: GENERATE -> WRITE -> VERIFY FILE SIZE > 0 -> SAVE KEY -> STATUS = COMPLETED.
6. Support for both DOCX and PPTX document formats.
7. Diagnostics and consistency checks: No silent file regeneration on download.
8. Deletion prevention: Completed reports remain persistent until explicit user deletion.
"""

import os
import re
import json
import uuid
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, Union, List

from apps.api.core.config import settings, WORKSPACE_ROOT
from apps.api.core.logging import get_logger

logger = get_logger("report_file_storage")


class ReportFileStorageService:
    """
    Canonical Storage Abstraction for ARM Report Files.
    Eliminates scattered '.storage/reports' relative path constructions across the backend.
    """

    _storage_root: Optional[Path] = None
    _reports_dir: Optional[Path] = None
    _staging_dir: Optional[Path] = None
    _metadata_dir: Optional[Path] = None

    @classmethod
    def get_storage_root(cls) -> Path:
        """Returns the absolute canonical storage root directory."""
        if cls._storage_root is None:
            # Anchor strictly to WORKSPACE_ROOT if settings.storage.local_dir is relative,
            # or resolve absolute path directly.
            configured = Path(settings.storage.local_dir)
            if configured.is_absolute():
                cls._storage_root = configured.resolve()
            else:
                cls._storage_root = (WORKSPACE_ROOT / configured).resolve()
        return cls._storage_root

    @classmethod
    def get_reports_dir(cls) -> Path:
        """Returns the absolute canonical reports storage directory."""
        if cls._reports_dir is None:
            cls._reports_dir = (cls.get_storage_root() / "reports").resolve()
        return cls._reports_dir

    @classmethod
    def get_staging_dir(cls) -> Path:
        """Returns the atomic staging directory located on the SAME volume/storage root."""
        if cls._staging_dir is None:
            cls._staging_dir = (cls.get_reports_dir() / ".staging").resolve()
        return cls._staging_dir

    @classmethod
    def get_metadata_dir(cls) -> Path:
        """Returns the persistent metadata catalog directory."""
        if cls._metadata_dir is None:
            cls._metadata_dir = (cls.get_reports_dir() / ".metadata").resolve()
        return cls._metadata_dir

    @classmethod
    def initialize(cls) -> None:
        """
        Startup validation:
        1. Resolves canonical storage root.
        2. Creates required directories if missing.
        3. Logs the absolute resolved reports directory.
        4. Does NOT delete or modify existing reports.
        """
        reports_dir = cls.get_reports_dir()
        staging_dir = cls.get_staging_dir()
        meta_dir = cls.get_metadata_dir()

        reports_dir.mkdir(parents=True, exist_ok=True)
        staging_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        existing_count = len(list(reports_dir.glob("*.docx"))) + len(list(reports_dir.glob("*.pptx")))
        logger.info(
            f"[STORAGE-STARTUP] Canonical Report Storage initialized.\n"
            f"  Storage Root: {cls.get_storage_root()}\n"
            f"  Reports Directory: {reports_dir}\n"
            f"  Staging Directory: {staging_dir}\n"
            f"  Metadata Catalog:  {meta_dir}\n"
            f"  Existing Reports Preserved: {existing_count} files"
        )
        print(
            f"[ARM STORAGE] Canonical Reports Directory: {reports_dir} "
            f"({existing_count} existing reports preserved)"
        )

    @classmethod
    def get_canonical_path(cls, report_id: str, extension: str = "docx") -> Path:
        """
        Returns the deterministic canonical path for a report:
        <storage_root>/reports/<report_id>.<extension>
        """
        clean_id = (report_id or "").strip()
        clean_ext = extension.lstrip(".").lower() or "docx"
        return (cls.get_reports_dir() / f"{clean_id}.{clean_ext}").resolve()

    @classmethod
    def get_storage_key(cls, report_id: str, extension: str = "docx") -> str:
        """
        Returns the canonical storage key for persistence:
        reports/<report_id>.<extension>
        """
        clean_id = (report_id or "").strip()
        clean_ext = extension.lstrip(".").lower() or "docx"
        return f"reports/{clean_id}.{clean_ext}"

    @classmethod
    def save_report_file_atomically(
        cls,
        report_id: str,
        source_data_or_path: Union[str, Path, bytes],
        extension: str = "docx",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, str]:
        """
        Atomically saves a generated report file to the canonical storage directory.
        
        Execution steps:
        1. Stages the file in <storage_root>/reports/.staging/
        2. Writes/flushes the entire content and fsyncs to disk
        3. Verifies staging file exists and has size > 0
        4. Atomically replaces destination file (<storage_root>/reports/<report_id>.<ext>)
        5. Verifies canonical file exists and has size > 0
        6. Persists canonical report metadata to disk (.metadata/<report_id>.json)
        
        Returns:
            Tuple of (canonical_path: Path, storage_key: str)
        """
        clean_id = (report_id or "").strip()
        if not clean_id:
            raise ValueError("report_id cannot be empty")

        clean_ext = extension.lstrip(".").lower() or "docx"
        if isinstance(source_data_or_path, (str, Path)) and not extension:
            src_p = Path(source_data_or_path)
            clean_ext = src_p.suffix.lstrip(".").lower() or "docx"

        canonical_path = cls.get_canonical_path(clean_id, clean_ext)
        storage_key = cls.get_storage_key(clean_id, clean_ext)
        staging_dir = cls.get_staging_dir()
        staging_dir.mkdir(parents=True, exist_ok=True)

        staging_path = staging_dir / f"{clean_id}_{uuid.uuid4().hex[:8]}.tmp"

        try:
            # 1. Write or copy to staging path
            if isinstance(source_data_or_path, bytes):
                if len(source_data_or_path) == 0:
                    raise ValueError(f"Cannot save 0-byte report file for {clean_id}")
                with open(staging_path, "wb") as f_out:
                    f_out.write(source_data_or_path)
                    f_out.flush()
                    os.fsync(f_out.fileno())
            elif isinstance(source_data_or_path, (str, Path)):
                src_path = Path(source_data_or_path).resolve()
                if not src_path.exists():
                    raise FileNotFoundError(f"Source file not found for report save: {src_path}")
                if src_path.stat().st_size == 0:
                    raise ValueError(f"Source file is empty (0 bytes) for report {clean_id}: {src_path}")
                shutil.copyfile(str(src_path), str(staging_path))
                # Sync staging file
                with open(staging_path, "rb+") as f_out:
                    f_out.flush()
                    os.fsync(f_out.fileno())
            else:
                raise TypeError(f"Unsupported source data type: {type(source_data_or_path)}")

            # 2. Verify staging file exists and has non-zero size
            if not staging_path.exists():
                raise RuntimeError(f"Staging file does not exist after write: {staging_path}")
            st_size = staging_path.stat().st_size
            if st_size == 0:
                raise RuntimeError(f"Staged report file has 0 bytes: {staging_path}")

            # 3. Compute SHA-256 for audit
            with open(staging_path, "rb") as f_sha:
                file_hash = hashlib.sha256(f_sha.read()).hexdigest()

            # 4. Atomically move/replace to destination
            cls.get_reports_dir().mkdir(parents=True, exist_ok=True)
            os.replace(str(staging_path), str(canonical_path))

            # 5. Verify final canonical path exists and has size > 0
            if not canonical_path.exists():
                raise RuntimeError(f"Canonical report file not found after atomic move: {canonical_path}")
            final_size = canonical_path.stat().st_size
            if final_size == 0:
                raise RuntimeError(f"Canonical report file has 0 bytes after move: {canonical_path}")

            # 6. Save persistent report metadata
            meta_record = {
                "report_id": clean_id,
                "storage_key": storage_key,
                "file_path": str(canonical_path),
                "extension": clean_ext,
                "file_size": final_size,
                "sha256": file_hash,
                "status": "completed",
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                meta_record.update({k: v for k, v in metadata.items() if k not in meta_record})

            cls._save_metadata(clean_id, meta_record)

            logger.info(
                f"[STORAGE-SAVE-SUCCESS] Report '{clean_id}' saved atomically.\n"
                f"  Path: {canonical_path}\n"
                f"  Storage Key: {storage_key}\n"
                f"  Size: {final_size} bytes\n"
                f"  SHA-256: {file_hash}"
            )
            return canonical_path, storage_key

        except Exception as ex:
            if staging_path.exists():
                try:
                    staging_path.unlink()
                except Exception:
                    pass
            logger.error(f"[STORAGE-SAVE-ERROR] Failed to save report file for '{clean_id}': {ex}")
            raise

    @classmethod
    def resolve_report_file(cls, report_id: str) -> Dict[str, Any]:
        """
        Resolves a report file by report ID, job ID, document ID, or filename.
        
        Returns a dictionary with:
        {
            "found": bool,
            "report_id": str,
            "file_path": str,
            "storage_key": str,
            "extension": str,
            "file_size": int,
            "status": "completed" | "FILE_NOT_FOUND" | "FAILED",
            "metadata": dict
        }
        """
        clean_id = (report_id or "").strip()
        # Strip common trailing extensions if caller passed full filename
        if clean_id.lower().endswith(".docx"):
            clean_id = clean_id[:-5]
        elif clean_id.lower().endswith(".pptx"):
            clean_id = clean_id[:-5]
        elif clean_id.lower().endswith(".pdf"):
            clean_id = clean_id[:-4]

        reports_dir = cls.get_reports_dir()
        meta = cls.get_report_metadata(clean_id) or {}

        # Check 1: If metadata exists, verify stored path or canonical path
        if meta:
            cand_path_str = meta.get("file_path")
            cand_ext = meta.get("extension", "docx")
            cand_key = meta.get("storage_key") or cls.get_storage_key(clean_id, cand_ext)

            target_cand = Path(cand_path_str).resolve() if cand_path_str else cls.get_canonical_path(clean_id, cand_ext)
            if target_cand.exists() and target_cand.stat().st_size > 0:
                return {
                    "found": True,
                    "report_id": clean_id,
                    "file_path": str(target_cand),
                    "storage_key": cand_key,
                    "extension": cand_ext,
                    "file_size": target_cand.stat().st_size,
                    "status": "completed",
                    "metadata": meta,
                }
            elif meta.get("status") == "FAILED":
                return {
                    "found": False,
                    "report_id": clean_id,
                    "file_path": str(target_cand),
                    "storage_key": cand_key,
                    "extension": cand_ext,
                    "file_size": 0,
                    "status": "FAILED",
                    "error_reason": meta.get("error_reason", "Generation failed"),
                    "metadata": meta,
                }

        # Check 2: Direct canonical path search in reports directory
        for ext in ("docx", "pptx"):
            cand = cls.get_canonical_path(clean_id, ext)
            if cand.exists() and cand.stat().st_size > 0:
                storage_key = cls.get_storage_key(clean_id, ext)
                return {
                    "found": True,
                    "report_id": clean_id,
                    "file_path": str(cand),
                    "storage_key": storage_key,
                    "extension": ext,
                    "file_size": cand.stat().st_size,
                    "status": "completed",
                    "metadata": meta,
                }

        # Check 3: Check common prefix/suffix conventions (e.g. Report_{id}.docx, ARM_Report_{id}.docx)
        for pattern in (f"Report_{clean_id}.*", f"ARM_Report_{clean_id}.*", f"*{clean_id}*.docx", f"*{clean_id}*.pptx"):
            matches = list(reports_dir.glob(pattern))
            for m in matches:
                if m.is_file() and m.stat().st_size > 0:
                    ext = m.suffix.lstrip(".").lower()
                    return {
                        "found": True,
                        "report_id": clean_id,
                        "file_path": str(m.resolve()),
                        "storage_key": cls.get_storage_key(clean_id, ext),
                        "extension": ext,
                        "file_size": m.stat().st_size,
                        "status": "completed",
                        "metadata": meta,
                    }

        # Check 4: Scan metadata directory for alias matching (e.g. job_id, document_id, project_id)
        alias_meta = cls._find_metadata_by_alias(clean_id)
        if alias_meta:
            a_file = alias_meta.get("file_path")
            a_ext = alias_meta.get("extension", "docx")
            a_key = alias_meta.get("storage_key") or cls.get_storage_key(alias_meta.get("report_id", clean_id), a_ext)
            target_p = Path(a_file).resolve() if a_file else cls.get_canonical_path(alias_meta.get("report_id", clean_id), a_ext)
            if target_p.exists() and target_p.stat().st_size > 0:
                return {
                    "found": True,
                    "report_id": alias_meta.get("report_id", clean_id),
                    "file_path": str(target_p),
                    "storage_key": a_key,
                    "extension": a_ext,
                    "file_size": target_p.stat().st_size,
                    "status": "completed",
                    "metadata": alias_meta,
                }

        # Not found on disk: return diagnostic report
        default_ext = meta.get("extension", "docx") if meta else "docx"
        canonical_p = cls.get_canonical_path(clean_id, default_ext)
        storage_key = cls.get_storage_key(clean_id, default_ext)

        return {
            "found": False,
            "report_id": clean_id,
            "file_path": str(canonical_p),
            "storage_key": storage_key,
            "extension": default_ext,
            "file_size": 0,
            "status": "FILE_NOT_FOUND",
            "metadata": meta,
        }

    @classmethod
    def verify_file_exists(cls, report_id: str) -> bool:
        """Returns True if the report file exists and has size > 0."""
        res = cls.resolve_report_file(report_id)
        return bool(res.get("found"))

    @classmethod
    def get_report_metadata(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Reads persisted report metadata from disk."""
        clean_id = (report_id or "").strip()
        meta_file = cls.get_metadata_dir() / f"{clean_id}.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception as ex:
                logger.warning(f"[METADATA-READ-WARN] Could not parse metadata for '{clean_id}': {ex}")
        return None

    @classmethod
    def record_failed_generation(cls, report_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Persists a generation failure record so download returns a clear error instead of a missing file."""
        clean_id = (report_id or "").strip()
        record = {
            "report_id": clean_id,
            "status": "FAILED",
            "error_reason": str(reason),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            record.update({k: v for k, v in metadata.items() if k not in record})
        cls._save_metadata(clean_id, record)

    @classmethod
    def get_media_type(cls, extension: str) -> str:
        """Returns the RFC-compliant MIME type for the document format."""
        clean_ext = extension.lstrip(".").lower()
        if clean_ext == "pptx":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @classmethod
    def _save_metadata(cls, report_id: str, record: Dict[str, Any]) -> None:
        """Writes metadata dictionary atomically to disk."""
        meta_dir = cls.get_metadata_dir()
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_dir / f"{report_id}.json"
        temp_file = meta_dir / f"{report_id}_{uuid.uuid4().hex[:6]}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as fp:
                json.dump(record, fp, indent=2)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(str(temp_file), str(meta_file))
        except Exception as ex:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            logger.warning(f"[METADATA-SAVE-WARN] Could not write metadata for '{report_id}': {ex}")

    @classmethod
    def _find_metadata_by_alias(cls, alias_id: str) -> Optional[Dict[str, Any]]:
        """Scans metadata directory for matching project_id, job_id, or document_id."""
        meta_dir = cls.get_metadata_dir()
        if not meta_dir.exists():
            return None
        clean_alias = alias_id.strip()
        for f in meta_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    if clean_alias in (
                        data.get("report_id"),
                        data.get("job_id"),
                        data.get("document_id"),
                        data.get("project_id"),
                        f"doc-{data.get('report_id')}",
                    ):
                        return data
            except Exception:
                continue
        return None


# Global service instance
report_file_storage_service = ReportFileStorageService()
