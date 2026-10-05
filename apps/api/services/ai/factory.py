"""
ReportForge AI - AI Provider Factory
"""

from apps.api.services.ai.base import AIProvider
from apps.api.services.ai.gemini import GeminiProvider
from apps.api.services.ai.mock import MockAIProvider
from apps.api.core.config import settings


def get_ai_provider() -> AIProvider:
    """Returns the configured AI provider, falling back to mock in development if unconfigured."""
    provider_name = settings.ai.default_provider.lower()

    if provider_name == "gemini":
        gemini = GeminiProvider()
        if gemini.is_configured():
            return gemini
        return MockAIProvider()

    if provider_name == "mock":
        return MockAIProvider()

    # Default fallback
    return MockAIProvider()


__all__ = ["AIProvider", "GeminiProvider", "MockAIProvider", "get_ai_provider"]
