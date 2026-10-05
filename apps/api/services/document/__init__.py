"""
ReportForge AI - Document Services Package
"""

from .base import DocumentService
from .service import StandardDocumentService


def get_document_service() -> DocumentService:
    """Factory returning configured document service."""
    return StandardDocumentService()


__all__ = ["DocumentService", "StandardDocumentService", "get_document_service"]
