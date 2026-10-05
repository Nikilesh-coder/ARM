"""
ARM Stage 8 - Citation + Evidence Verification Package
"""

from packages.citation_verifier.schema import (
    ClaimType,
    VerificationStatus,
    EvidenceSourceType,
    ExtractedClaim,
    ClaimVerificationRecord,
    VerificationSummary,
    QualityGateResult,
    ReportVerificationReport,
)
from packages.citation_verifier.research_provider import ResearchProvider, MockResearchProvider
from packages.citation_verifier.claim_extractor import ClaimExtractor
from packages.citation_verifier.engine import CitationEvidenceVerificationEngine

__all__ = [
    "ClaimType",
    "VerificationStatus",
    "EvidenceSourceType",
    "ExtractedClaim",
    "ClaimVerificationRecord",
    "VerificationSummary",
    "QualityGateResult",
    "ReportVerificationReport",
    "ResearchProvider",
    "MockResearchProvider",
    "ClaimExtractor",
    "CitationEvidenceVerificationEngine",
]
