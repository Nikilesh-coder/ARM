"""
ARM Stage 11 - Specialized Quality Rules & Checkers
Implements deterministic heuristics for placeholder detection, numerical consistency,
technology consistency, duplicate content detection, secret scanning, and prompt injection defense.
"""

import re
import difflib
from typing import List, Dict, Any, Tuple, Optional, Set
from packages.quality_engine.schema import ValidationIssue, ValidationCheck, IssueSeverity


# Controlled unresolved placeholder patterns
REQUIRED_PLACEHOLDER_REGEX = re.compile(
    r'(\{\{[A-Za-z0-9_\-]+\}\}|\[(?:TODO|TBD|INSERT\s+HERE|ADD\s+IMAGE|INSERT\s+CITATION|INSERT\s+FIGURE|ADD\s+CONTENT)\])',
    re.IGNORECASE
)
OPTIONAL_PLACEHOLDER_REGEX = re.compile(
    r'(\[optional:?[^\]]*\]|\[note:?[^\]]*\])',
    re.IGNORECASE
)

# Secret scanning regexes
SECRET_PATTERNS = [
    (re.compile(r'AIza[0-9A-Za-z-_]{35}'), "Gemini API Key"),
    (re.compile(r'eyJhbGciOi[0-9A-Za-z-_]+\.[0-9A-Za-z-_]+\.[0-9A-Za-z-_]+'), "JWT / Supabase Service Key"),
    (re.compile(r'postgres://[^\s:]+:[^\s@]+@'), "PostgreSQL Connection String with Password"),
    (re.compile(r'sbp_[0-9a-fA-F]{30,}'), "Supabase Secret Token"),
    (re.compile(r'sk-[0-9A-Za-z]{32,}'), "Secret API Key"),
    (re.compile(r'BEGIN PRIVATE KEY'), "RSA / Private Key Block")
]

# Prompt injection patterns designed to trick automated systems
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'\bignore\s+(all\s+)?(previous\s+)?instructions\b', re.IGNORECASE),
    re.compile(r'\bmark\s+(this\s+)?report\s+as\s+verified\b', re.IGNORECASE),
    re.compile(r'\bbypass\s+validation\b', re.IGNORECASE),
    re.compile(r'\breveal\s+(the\s+)?system\s+prompt\b', re.IGNORECASE),
    re.compile(r'\boverride\s+quality\s+gate\b', re.IGNORECASE),
    re.compile(r'\bset\s+status\s+to\s+ready\b', re.IGNORECASE),
]

# Known tech families for conflict detection
TECH_FAMILIES = {
    "languages": {"python", "java", "c++", "c#", "rust", "go", "php", "ruby", "swift", "kotlin", "javascript", "typescript"},
    "backend_frameworks": {"fastapi", "django", "flask", "spring boot", "express", "nestjs", "asp.net", "laravel", "rails"},
    "frontend_frameworks": {"react", "angular", "vue", "next.js", "svelte"},
    "platform_type": {"mobile application", "web application", "desktop application", "iot firmware"}
}

# Metric extraction regex (percentages, user counts, accuracy)
ACCURACY_METRIC_REGEX = re.compile(
    r'(?:accuracy|precision|recall|f1(?:-score)?)[^%\d]{1,25}?(\d{1,3}(?:\.\d+)?)\s*%',
    re.IGNORECASE
)
USER_COUNT_REGEX = re.compile(
    r'(\d+)\s+(?:active\s+)?users\b',
    re.IGNORECASE
)


class QualityRulesEngine:
    """Deterministic static analysis rules for Stage 11 Quality Engine."""

    @staticmethod
    def detect_placeholders(text: str, section_id: Optional[str] = None, section_title: Optional[str] = None) -> List[ValidationIssue]:
        """Detects unresolved placeholders in report text."""
        issues = []
        if not text:
            return issues

        # Check required placeholders
        for match in REQUIRED_PLACEHOLDER_REGEX.finditer(text):
            ph = match.group(1)
            issues.append(
                ValidationIssue(
                    issue_id=f"issue_ph_{abs(hash(ph + str(section_id)))}",
                    category="data_integrity",
                    severity="BLOCKING",
                    message=f"Unresolved mandatory placeholder '{ph}' detected in section '{section_title or section_id}'.",
                    section_id=section_id,
                    section_title=section_title,
                    suggested_action=f"Replace '{ph}' with actual project content or verified data."
                )
            )

        # Check optional placeholders
        for match in OPTIONAL_PLACEHOLDER_REGEX.finditer(text):
            ph = match.group(1)
            issues.append(
                ValidationIssue(
                    issue_id=f"issue_opt_ph_{abs(hash(ph + str(section_id)))}",
                    category="data_integrity",
                    severity="WARNING",
                    message=f"Optional placeholder annotation '{ph}' detected in section '{section_title or section_id}'.",
                    section_id=section_id,
                    section_title=section_title,
                    suggested_action=f"Verify if annotation '{ph}' should be removed before final submission."
                )
            )

        return issues

    @staticmethod
    def scan_for_secrets(content: str, source_label: str = "report") -> List[ValidationIssue]:
        """Scans text or extracted content for high-entropy secrets and credentials."""
        issues = []
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(content):
                issues.append(
                    ValidationIssue(
                        issue_id=f"sec_leak_{abs(hash(label + source_label))}",
                        category="security_validation",
                        severity="BLOCKING",
                        message=f"Security violation: Sensitive {label} detected in {source_label}.",
                        suggested_action=f"Remove secret token or credential immediately from {source_label}."
                    )
                )
        return issues

    @staticmethod
    def check_prompt_injection(text: str, section_id: Optional[str] = None, section_title: Optional[str] = None) -> List[ValidationIssue]:
        """Scans for adversarial prompt injection text intended to manipulate the quality gate."""
        issues = []
        for pattern in PROMPT_INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                snippet = match.group(0)
                issues.append(
                    ValidationIssue(
                        issue_id=f"injection_{abs(hash(snippet + str(section_id)))}",
                        category="security_validation",
                        severity="WARNING",
                        message=f"Adversarial or prompt-injection text pattern detected: '{snippet}' in section '{section_title or section_id}'. Engine rules remain unchanged.",
                        section_id=section_id,
                        section_title=section_title,
                        suggested_action="Review and remove instructional meta-commentary from report prose."
                    )
                )
        return issues

    @staticmethod
    def check_numerical_consistency(sections_text: List[Tuple[str, str, str]]) -> List[ValidationIssue]:
        """
        sections_text: List of (section_id, section_title, text)
        Checks for conflicting metrics (e.g. accuracy = 92% in Results vs 97% in Conclusion).
        """
        issues = []
        accuracies: Dict[str, List[Tuple[str, str, float]]] = {}
        user_counts: List[Tuple[str, str, int]] = []

        for sec_id, sec_title, text in sections_text:
            # Check accuracy metrics
            acc_matches = ACCURACY_METRIC_REGEX.findall(text)
            for m in acc_matches:
                try:
                    val = float(m)
                    accuracies.setdefault("accuracy", []).append((sec_id, sec_title, val))
                except ValueError:
                    pass

            # Check user count mentions
            uc_matches = USER_COUNT_REGEX.findall(text)
            for m in uc_matches:
                try:
                    u_val = int(m)
                    user_counts.append((sec_id, sec_title, u_val))
                except ValueError:
                    pass

        # Check for contradicting accuracies (> 1.0% divergence)
        if "accuracy" in accuracies and len(accuracies["accuracy"]) > 1:
            first_sec_id, first_title, first_val = accuracies["accuracy"][0]
            for sec_id, sec_title, val in accuracies["accuracy"][1:]:
                if abs(first_val - val) > 0.5:
                    issues.append(
                        ValidationIssue(
                            issue_id=f"num_inconsistency_acc_{abs(hash(sec_id + str(val)))}",
                            category="internal_consistency",
                            severity="ERROR",
                            message=f"Numerical inconsistency: Accuracy cited as {first_val}% in '{first_title}' but {val}% in '{sec_title}'.",
                            section_id=sec_id,
                            section_title=sec_title,
                            suggested_action="Harmonize accuracy metric across sections based on verified test evidence."
                        )
                    )

        # Check for contradicting user counts
        if len(user_counts) > 1:
            first_sec_id, first_title, first_cnt = user_counts[0]
            for sec_id, sec_title, cnt in user_counts[1:]:
                if first_cnt != cnt:
                    issues.append(
                        ValidationIssue(
                            issue_id=f"num_inconsistency_users_{abs(hash(sec_id + str(cnt)))}",
                            category="internal_consistency",
                            severity="ERROR",
                            message=f"Numerical inconsistency: User count cited as {first_cnt} in '{first_title}' but {cnt} in '{sec_title}'.",
                            section_id=sec_id,
                            section_title=sec_title,
                            suggested_action="Reconcile user sample counts with project experimental setup."
                        )
                    )

        return issues

    @staticmethod
    def check_technology_consistency(sections_text: List[Tuple[str, str, str]]) -> List[ValidationIssue]:
        """Checks for conflicting technology assertions across sections."""
        issues = []
        found_by_sec: Dict[str, Dict[str, Set[str]]] = {}

        for sec_id, sec_title, text in sections_text:
            text_lower = text.lower()
            found_by_sec[sec_id] = {"title": sec_title, "languages": set(), "backends": set(), "platform": set()}

            for lang in TECH_FAMILIES["languages"]:
                if re.search(r'\b' + re.escape(lang) + r'\b', text_lower):
                    found_by_sec[sec_id]["languages"].add(lang)

            for be in TECH_FAMILIES["backend_frameworks"]:
                if re.search(r'\b' + re.escape(be) + r'\b', text_lower):
                    found_by_sec[sec_id]["backends"].add(be)

            for plat in TECH_FAMILIES["platform_type"]:
                if plat in text_lower:
                    found_by_sec[sec_id]["platform"].add(plat)

        # Compare methodology vs implementation vs conclusion
        # If methodology specifies Python and implementation/conclusion claims Java without mention of Python
        sec_items = list(found_by_sec.items())
        for i in range(len(sec_items)):
            id1, data1 = sec_items[i]
            for j in range(i + 1, len(sec_items)):
                id2, data2 = sec_items[j]

                # Conflicting languages (e.g. only python in sec1 vs only java in sec2)
                if data1["languages"] and data2["languages"] and not (data1["languages"] & data2["languages"]):
                    # If mutually disjoint single-language mentions
                    if len(data1["languages"]) == 1 and len(data2["languages"]) == 1:
                        l1 = list(data1["languages"])[0]
                        l2 = list(data2["languages"])[0]
                        issues.append(
                            ValidationIssue(
                                issue_id=f"tech_conflict_{abs(hash(id1 + id2 + l1 + l2))}",
                                category="internal_consistency",
                                severity="ERROR",
                                message=f"Technology inconsistency: '{data1['title']}' describes {l1.capitalize()} while '{data2['title']}' describes {l2.capitalize()}.",
                                section_id=id2,
                                section_title=data2["title"],
                                suggested_action=f"Ensure consistent technology stack descriptions across all chapters."
                            )
                        )

                # Conflicting platforms (e.g. mobile application vs web application)
                if data1["platform"] and data2["platform"] and not (data1["platform"] & data2["platform"]):
                    p1 = list(data1["platform"])[0]
                    p2 = list(data2["platform"])[0]
                    issues.append(
                        ValidationIssue(
                            issue_id=f"plat_conflict_{abs(hash(id1 + id2 + p1 + p2))}",
                            category="internal_consistency",
                            severity="ERROR",
                            message=f"Platform inconsistency: '{data1['title']}' mentions '{p1}' while '{data2['title']}' mentions '{p2}'.",
                            section_id=id2,
                            section_title=data2["title"],
                            suggested_action="Harmonize target platform architecture between problem definition and implementation."
                        )
                    )

        return issues

    @staticmethod
    def detect_duplicate_content(sections_paragraphs: List[Tuple[str, str, str]]) -> List[ValidationIssue]:
        """
        Detects exact or near-identical paragraphs (> 0.88 similarity and > 50 chars) across sections.
        """
        issues = []
        n = len(sections_paragraphs)
        for i in range(n):
            sec_id_1, title_1, p1 = sections_paragraphs[i]
            if len(p1.strip()) < 50:
                continue
            for j in range(i + 1, n):
                sec_id_2, title_2, p2 = sections_paragraphs[j]
                if len(p2.strip()) < 50:
                    continue

                if p1.strip().lower() == p2.strip().lower():
                    issues.append(
                        ValidationIssue(
                            issue_id=f"dup_{abs(hash(p1[:30] + sec_id_1 + sec_id_2))}",
                            category="data_integrity",
                            severity="WARNING",
                            message=f"Duplicate content: Identical paragraph repeated in '{title_1}' and '{title_2}'.",
                            section_id=sec_id_2,
                            section_title=title_2,
                            suggested_action="Refactor or synthesize duplicate text to eliminate redundancy."
                        )
                    )
                else:
                    ratio = difflib.SequenceMatcher(None, p1.strip().lower(), p2.strip().lower()).ratio()
                    if ratio > 0.88:
                        issues.append(
                            ValidationIssue(
                                issue_id=f"near_dup_{abs(hash(p1[:30] + sec_id_1 + sec_id_2))}",
                                category="data_integrity",
                                severity="WARNING",
                                message=f"Near-duplicate content ({int(ratio*100)}% match) between '{title_1}' and '{title_2}'.",
                                section_id=sec_id_2,
                                section_title=title_2,
                                suggested_action="Review repeated wording and tailor to section purpose."
                            )
                        )
        return issues
