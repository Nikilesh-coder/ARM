"""
ARM Stage 8 - Research Provider Abstraction
Provides a minimal provider interface for external academic citation/source lookup,
safeguarding future integration while keeping Stage 8 strictly focused on verification.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ResearchProvider(ABC):
    """Abstract interface for academic source and citation lookups."""

    @abstractmethod
    def search_sources(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search external repositories for academic publications."""
        pass

    @abstractmethod
    def verify_citation(
        self,
        citation_text: str,
        doi: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify whether an academic citation corresponds to a genuine registered publication."""
        pass


class MockResearchProvider(ResearchProvider):
    """Deterministic mock research provider for testing and offline execution."""

    def __init__(self, registered_sources: Optional[List[Dict[str, Any]]] = None):
        self.registered_sources = registered_sources or [
            {
                "id": "src_1",
                "title": "Edge Computing Architectures for Real-Time Computer Vision",
                "authors": ["A. Sharma", "B. Patel"],
                "year": 2024,
                "venue": "IEEE Transactions on Edge Computing",
                "doi": "10.1109/TEC.2024.123456",
            },
            {
                "id": "src_2",
                "title": "Low-Power LoRaWAN Sensor Networks in Smart Irrigation",
                "authors": ["C. Kumar", "D. Rao"],
                "year": 2023,
                "venue": "Journal of Agricultural IoT",
                "doi": "10.1016/j.agriot.2023.789101",
            }
        ]

    def search_sources(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        q_lower = query.lower()
        matches = [
            s for s in self.registered_sources
            if any(term in s["title"].lower() or term in q_lower for term in q_lower.split() if len(term) > 3)
        ]
        return matches[:limit]

    def verify_citation(
        self,
        citation_text: str,
        doi: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        text_lower = citation_text.lower()
        
        # Check DOI match
        if doi:
            for s in self.registered_sources:
                if s.get("doi") and s["doi"].lower() == doi.lower():
                    return {"is_valid": True, "source": s, "confidence": "high"}

        # Check registered sources match
        for s in self.registered_sources:
            if s["title"].lower() in text_lower or (title and title.lower() in s["title"].lower()):
                return {"is_valid": True, "source": s, "confidence": "high"}

        return {
            "is_valid": False,
            "source": None,
            "reason": "Source not found in verified registry"
        }
