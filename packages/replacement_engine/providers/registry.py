"""
ARM - Document Provider Registry & Factory
Manages available document generation providers (Internal, Carbone, etc.).
Allows ARM to switch providers dynamically or via environment configuration.
"""

from typing import Dict, Any, List, Optional

from apps.api.core.config import settings
from apps.api.core.logging import get_logger
from packages.replacement_engine.providers.base import DocumentProvider
from packages.replacement_engine.providers.internal_provider import InternalDocumentProvider
from packages.replacement_engine.providers.carbone_provider import CarboneDocumentProvider

logger = get_logger("document_provider.registry")


class DocumentProviderRegistry:
    """
    Central registry for ARM Document Providers.
    Decouples document engines from template orchestrators.
    """

    def __init__(self):
        self._providers: Dict[str, DocumentProvider] = {}
        # Register core providers
        self.register_provider(InternalDocumentProvider())
        self.register_provider(CarboneDocumentProvider())

    def register_provider(self, provider: DocumentProvider):
        """Registers a new document provider instance."""
        name = provider.get_provider_name().lower()
        self._providers[name] = provider
        logger.info(f"Registered document provider: '{name}' (configured={provider.is_configured()})")

    def get_provider(self, name: Optional[str] = None) -> DocumentProvider:
        """
        Retrieves the requested provider or falls back to configured default ('internal').
        """
        selected_name = (name or settings.document_provider.default_provider or "internal").lower()

        provider = self._providers.get(selected_name)
        if not provider:
            logger.warning(
                f"Requested document provider '{selected_name}' not found. Falling back to 'internal'."
            )
            provider = self._providers.get("internal")

        return provider

    def list_providers(self) -> List[Dict[str, Any]]:
        """
        Returns public descriptors of available providers.
        Guarantees that sensitive credentials/API keys are NEVER exposed.
        """
        default_name = (settings.document_provider.default_provider or "internal").lower()
        descriptors = []

        descriptions = {
            "internal": "Built-in ARM OpenXML / PDF replacement engine. Fully offline and deterministic.",
            "carbone": "Carbone Cloud document generator. Uses external cloud rendering with template upload.",
        }

        for name, prov in self._providers.items():
            descriptors.append({
                "name": name,
                "is_configured": prov.is_configured(),
                "is_default": name == default_name,
                "description": descriptions.get(name, f"{name.title()} document provider."),
            })

        return descriptors


document_provider_registry = DocumentProviderRegistry()
