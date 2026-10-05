"""
Academic Title Formatter Service
Intelligently transforms conversational prompts/search queries into clean, professional academic project titles.
Prevents conversational queries from contaminating document titles or template replacement.
"""

import re
from typing import Tuple, Optional

CONVERSATIONAL_PREFIX_PATTERN = re.compile(
    r"^(?:(?:please\s+)?(?:can\s+you\s+)?(?:give|create|generate|write|make|prepare|produce|provide|build)\s+(?:me\s+)?(?:an?|the|my)?\s*(?:project|academic)?\s*(?:report|presentation|project|synopsis|doc(?:ument)?|paper)?\s*(?:on|for|about)?|"
    r"give\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"create\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"generate\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"write\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"prepare\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"make\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"produce\s+(?:an?|the|my)?\s*(?:report|presentation|project|documentation)?\s*(?:on|for|about)?|"
    r"report\s+(?:on|for|about)|"
    r"project\s+(?:on|for|about)|"
    r"topic\s*:?)\s*",
    re.IGNORECASE
)

ACRONYMS = {
    "ai": "AI",
    "a.i.": "AI",
    "iot": "IoT",
    "i.o.t.": "IoT",
    "ml": "ML",
    "m.l.": "ML",
    "dl": "DL",
    "nlp": "NLP",
    "rfid": "RFID",
    "gps": "GPS",
    "gsm": "GSM",
    "api": "API",
    "cnn": "CNN",
    "rnn": "RNN",
    "uav": "UAV",
    "ieee": "IEEE",
    "ev": "EV",
    "ui": "UI",
    "ux": "UX",
    "ar": "AR",
    "vr": "VR",
    "plc": "PLC",
    "scada": "SCADA",
    "fpga": "FPGA",
    "vlsi": "VLSI",
}

LOWERCASE_WORDS = {
    "and", "or", "of", "in", "on", "at", "to", "for", "with", "by", "a", "an", "the", "using", "via"
}

COMMON_ACADEMIC_ENDINGS = (
    "system", "systems", "platform", "framework", "architecture", "analysis",
    "study", "approach", "model", "network", "mechanism", "technique", "method",
    "methodology", "controller", "project", "monitoring", "design", "investigation",
    "simulation", "optimization", "implementation"
)


def extract_clean_academic_title(raw_text: str) -> str:
    """
    Cleans raw user input or conversational prompt into an authoritative academic title.
    Example:
      'give an report on Ai based irrigation' -> 'AI Based Irrigation System'
      'create report for smart attendance using face recognition' -> 'Smart Attendance Using Face Recognition System'
    """
    text = (raw_text or "").strip()
    if text.startswith(('"', '“', "'")) and text.endswith(('"', '”', "'")):
        text = text[1:-1].strip()

    # Repeatedly strip conversational prefix until none remains
    prev = None
    while prev != text:
        prev = text
        text = CONVERSATIONAL_PREFIX_PATTERN.sub("", text).strip()
        text = re.sub(r"^[:\-\s,]+", "", text).strip()

    if not text:
        return "Technical Research Project"

    words = text.split()
    formatted = []
    for i, w in enumerate(words):
        w_clean = re.sub(r"[^\w\.]", "", w).lower()
        punct_match = re.search(r"[^\w\.]+$", w)
        trailing_punct = punct_match.group(0) if punct_match else ""

        if w_clean in ACRONYMS:
            formatted.append(ACRONYMS[w_clean] + trailing_punct)
        elif w_clean in LOWERCASE_WORDS and i > 0:
            formatted.append(w_clean + trailing_punct)
        else:
            # Title case word, preserving hyphens if any (e.g. AI-Based)
            subparts = w.split("-")
            if len(subparts) > 1:
                sub_formatted = []
                for sp in subparts:
                    sp_clean = sp.lower()
                    if sp_clean in ACRONYMS:
                        sub_formatted.append(ACRONYMS[sp_clean])
                    else:
                        sub_formatted.append(sp.capitalize())
                formatted.append("-".join(sub_formatted))
            else:
                formatted.append(w.capitalize())

    candidate = " ".join(formatted)

    # Check if candidate should be suffixed with "System" if it describes a process/tool/domain without a noun
    cand_lower = candidate.lower().rstrip(".,;:")
    if not any(cand_lower.endswith(end) for end in COMMON_ACADEMIC_ENDINGS):
        candidate = f"{candidate} System"

    return candidate


def separate_title_and_research_query(
    raw_title: Optional[str] = None,
    project_title: Optional[str] = None,
    research_query: Optional[str] = None,
    search_query: Optional[str] = None,
    saved_project_title: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Deterministically separates the authentic academic project title from the research/search query.
    Returns: (authoritative_title, effective_research_query)
    """
    # 1. Authoritative saved project title has absolute priority if present
    if saved_project_title and str(saved_project_title).strip():
        auth_title = str(saved_project_title).strip()
        if auth_title.startswith(('"', '“', "'")) and auth_title.endswith(('"', '”', "'")):
            auth_title = auth_title[1:-1].strip()

        # Determine research query
        query = (research_query or search_query or raw_title or "").strip()
        if query and query.lower() != auth_title.lower():
            return auth_title, query
        return auth_title, None

    # 2. Check if raw_title is conversational
    title_candidate = (project_title or raw_title or "").strip()
    is_conversational = bool(CONVERSATIONAL_PREFIX_PATTERN.match(title_candidate))

    effective_query = (research_query or search_query or "").strip()
    if is_conversational and not effective_query:
        effective_query = title_candidate

    # Clean the title candidate
    cleaned_title = extract_clean_academic_title(title_candidate)

    # If project_title was passed explicitly and isn't conversational, prefer it
    if project_title and not CONVERSATIONAL_PREFIX_PATTERN.match(project_title):
        clean_passed = extract_clean_academic_title(project_title)
        return clean_passed, (effective_query or None)

    return cleaned_title, (effective_query or None)
