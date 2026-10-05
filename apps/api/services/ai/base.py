"""
ReportForge AI - AI Provider Abstraction
Decouples application logic from specific LLM providers (Gemini, OpenAI, Anthropic).
"""

from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    """Abstract base class for all AI generation providers."""

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """Generates standard prose text given a user prompt and optional system instructions."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> T:
        """Generates structured output strictly adhering to the provided Pydantic model."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has valid credentials configured."""
        pass
