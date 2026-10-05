"""
ARM Stage 8 - Claim Extractor
Extracts discrete, verifiable assertions (metrics, technologies, results,
citations, and project facts) from generated section content blocks.
"""

import re
import hashlib
from typing import List, Optional, Dict, Any
from packages.report_generator.schema import SectionGenerationOutput, ContentBlock
from packages.citation_verifier.schema import ExtractedClaim, ClaimType


# Common tech keywords to identify technology claims
KNOWN_TECHNOLOGIES = {
    "python", "fastapi", "django", "flask", "react", "next.js", "nextjs", "vue", "angular",
    "postgresql", "postgres", "mysql", "mongodb", "sqlite", "redis", "docker", "kubernetes",
    "tensorflow", "pytorch", "opencv", "scikit-learn", "keras", "pandas", "numpy",
    "esp32", "arduino", "raspberry pi", "lorawan", "rfid", "bluetooth", "mqtt", "aws", "gcp", "azure"
}

# Regex pattern for numerical claims, percentages, and metrics
# Note: % has no trailing word boundary \b because % is punctuation
NUMERICAL_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?\s*(?:ms|seconds|minutes|hours|fps|kb|mb|gb|users|images|samples|records|devices)\b|\baccuracy(?:\s*of|\s*was|\s*is|\s*[:=])?\s*\d+(?:\.\d+)?%?|\b\d+(?:\.\d+)?%?\s*(?:accuracy|precision|recall|f1)\b|\b\d+(?:\.\d+)?%\s*(?:water|power|energy|time|latency)?\s*savings\b",
    re.IGNORECASE
)

# Regex pattern for citation mentions (e.g., "[1]", "(Author, 2024)", "Author et al. (2025)", "[CITATION_REQUIRED]")
CITATION_PATTERN = re.compile(
    r"\[(?:CITATION_REQUIRED|\d+)\]|[A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,?\s*(?:\(\d{4}\)|\d{4})",
    re.UNICODE
)


class ClaimExtractor:
    """Extracts verifiable claims from generated report sections."""

    def __init__(self, ai_provider: Optional[Any] = None):
        self.ai_provider = ai_provider

    def extract_from_section(
        self,
        section: SectionGenerationOutput,
        research_required: bool = False
    ) -> List[ExtractedClaim]:
        """Extracts structured claims from a SectionGenerationOutput object."""
        claims: List[ExtractedClaim] = []
        seen_texts = set()

        for block in section.content_blocks:
            texts_to_process: List[str] = []
            if block.text and block.text.strip():
                texts_to_process.append(block.text.strip())
            if block.items:
                for item in block.items:
                    if item and item.strip():
                        texts_to_process.append(item.strip())

            for full_text in texts_to_process:
                sentences = self._split_sentences(full_text)
                for sentence in sentences:
                    sentence_clean = sentence.strip()
                    if not sentence_clean or len(sentence_clean) < 10:
                        continue
                    if sentence_clean in seen_texts:
                        continue

                    extracted = self._classify_and_extract(
                        sentence_clean,
                        section.section_id,
                        block.source_evidence_ids,
                        research_required
                    )
                    if extracted:
                        claims.append(extracted)
                        seen_texts.add(sentence_clean)

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """Splits prose into distinct sentences while respecting abbreviations like et al."""
        # Protect common abbreviations with periods
        protected = text
        protected = re.sub(r"\bet\s+al\.", "et al<DOT>", protected, flags=re.IGNORECASE)
        protected = re.sub(r"\be\.g\.", "e<DOT>g<DOT>", protected, flags=re.IGNORECASE)
        protected = re.sub(r"\bi\.e\.", "i<DOT>e<DOT>", protected, flags=re.IGNORECASE)
        protected = re.sub(r"\bvs\.", "vs<DOT>", protected, flags=re.IGNORECASE)
        protected = re.sub(r"\bfig\.", "fig<DOT>", protected, flags=re.IGNORECASE)

        parts = re.split(r"(?<=[.!?])\s+", protected)
        restored = [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]
        return restored

    def _classify_and_extract(
        self,
        sentence: str,
        section_id: str,
        source_evidence_ids: List[str],
        section_research_required: bool
    ) -> Optional[ExtractedClaim]:
        """Determines if a sentence is a claim requiring verification, and categorizes it."""
        s_lower = sentence.lower()

        # Generate deterministic claim ID
        claim_hash = hashlib.sha256(f"{section_id}:{sentence}".encode()).hexdigest()[:12]
        claim_id = f"claim_{claim_hash}"

        # 1. Check for explicit citation markers or author references
        if "[citation_required]" in s_lower:
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="citation_claim",
                raw_citation="[CITATION_REQUIRED]",
                source_evidence_ids=source_evidence_ids
            )

        citation_match = CITATION_PATTERN.search(sentence)
        if citation_match and ("et al" in citation_match.group(0).lower() or re.search(r"\(\d{4}\)", citation_match.group(0))):
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="citation_claim",
                raw_citation=citation_match.group(0),
                source_evidence_ids=source_evidence_ids
            )

        # 2. Check for numerical values, percentages, performance metrics (PRIORITY OVER DATASET)
        num_matches = NUMERICAL_PATTERN.findall(sentence)
        if num_matches:
            is_result = any(w in s_lower for w in ["achieved", "reduced", "improved", "result", "tested", "obtained", "reached", "handled", "measured", "accuracy", "savings"])
            claim_type: ClaimType = "project_result" if is_result else "metric"
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type=claim_type,
                extracted_entities=num_matches,
                source_evidence_ids=source_evidence_ids
            )

        # 3. Check for technologies
        tech_found = [tech for tech in KNOWN_TECHNOLOGIES if re.search(r"\b" + re.escape(tech) + r"\b", s_lower)]
        if tech_found and any(w in s_lower for w in ["uses", "used", "built", "implemented", "stack", "technology", "backend", "frontend", "database", "hardware"]):
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="technology",
                extracted_entities=tech_found,
                source_evidence_ids=source_evidence_ids
            )

        # 4. Check for dataset assertions
        if any(w in s_lower for w in ["dataset", "data set", "training data", "samples", "corpus"]):
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="dataset",
                extracted_entities=[],
                source_evidence_ids=source_evidence_ids
            )

        # 5. Check for research claim if section marked research_required
        if section_research_required and any(w in s_lower for w in ["study", "studies", "research", "literature", "prior work", "state of the art", "authors"]):
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="research_claim",
                source_evidence_ids=source_evidence_ids
            )

        # 6. Check for general project fact
        if any(w in s_lower for w in ["the project", "this project", "the system", "the application", "designed to", "aims to", "architecture"]):
            return ExtractedClaim(
                claim_id=claim_id,
                section_id=section_id,
                text=sentence,
                claim_type="project_fact",
                source_evidence_ids=source_evidence_ids
            )

        return None
