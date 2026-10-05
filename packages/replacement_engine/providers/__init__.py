"""
ARM - Document Generation Providers Package
Exports DocumentProvider base interface, ProviderGenerationResult,
InternalDocumentProvider, CarboneDocumentProvider, and document_provider_registry.
"""

from packages.replacement_engine.providers.base import (
    DocumentProvider,
    ProviderGenerationResult,
)
from packages.replacement_engine.providers.internal_provider import InternalDocumentProvider
from packages.replacement_engine.providers.carbone_provider import CarboneDocumentProvider
from packages.replacement_engine.providers.registry import (
    DocumentProviderRegistry,
    document_provider_registry,
)

__all__ = [
    "DocumentProvider",
    "ProviderGenerationResult",
    "InternalDocumentProvider",
    "CarboneDocumentProvider",
    "DocumentProviderRegistry",
    "document_provider_registry",
]
