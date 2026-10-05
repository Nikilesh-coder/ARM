"""
ARM Gemini Visual Generation Pipeline Service
============================================
Implements:
1. Slide Understanding before Image Generation (Visual Requirement Analysis).
2. Purpose Detection across key slide roles (Introduction, Problem, Existing, Proposed,
   Soil Moisture, AI Decision, Architecture, Working Process, Field Deployment, Results, Future Scope, Conclusion).
3. Detailed Concept & Physical Object Extraction from Slide Matter.
4. Dynamic Gemini Prompt Engineering (Slide Heading + Slide Matter > Project Name).
5. Visual Type Matching (Photographs, Technical Diagrams, Infographics, Process Illustrations).
6. Elimination of Old Template Subjects & Generic Tropes (Zero glowing brains, zero electrical safety).
7. Automated Image Relevance Verification & Regeneration Safeguards.
8. Visual Diversity Enforcement across slides.
9. Precision Template Container Fitting (100% template preservation).
10. Comprehensive Debug Logging (ARM GEMINI VISUAL GENERATION).
"""

import os
import re
import json
import base64
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field
import httpx
from PIL import Image as PILImage

from apps.api.core.config import settings
from apps.api.core.logging import get_logger

logger = get_logger("gemini_visual.pipeline")


class SlideVisualPurpose:
    INTRODUCTION = "INTRODUCTION"
    PROBLEM_STATEMENT = "PROBLEM_STATEMENT"
    EXISTING_SYSTEM = "EXISTING_SYSTEM"
    PROPOSED_SYSTEM = "PROPOSED_SYSTEM"
    SOIL_MOISTURE_MONITORING = "SOIL_MOISTURE_MONITORING"
    AI_DECISION_MAKING = "AI_DECISION_MAKING"
    SYSTEM_ARCHITECTURE = "SYSTEM_ARCHITECTURE"
    WORKING_PROCESS = "WORKING_PROCESS"
    FIELD_DEPLOYMENT = "FIELD_DEPLOYMENT"
    RESULTS = "RESULTS"
    FUTURE_SCOPE = "FUTURE_SCOPE"
    CONCLUSION = "CONCLUSION"
    GENERAL_TECHNICAL = "GENERAL_TECHNICAL"


class SlideVisualRequirement(BaseModel):
    """
    Internal visual requirement representation compiled prior to invoking image generation.
    Enforces: Slide Heading + Slide Matter > Project Name.
    """
    project_title: str
    slide_index: int = 1
    slide_heading: str
    slide_matter: str
    slide_purpose: str
    key_concepts: List[str]
    visual_type: str
    required_subjects: List[str]
    required_objects: List[str]
    environment: str
    visual_style: str
    negative_constraints: List[str]
    gemini_prompt: str
    relevance_status: str = "PENDING"
    generated_image_path: Optional[str] = None
    image_sha256: Optional[str] = None
    detected_domain: str = "general"
    domain_label: str = "General"
    domain_confidence: float = 1.0


class GeminiVisualPipelineService:
    """
    Core orchestrator for high-relevance Gemini visual generation in ARM.
    Guarantees every image represents the specific slide heading and matter.
    """

    # Universal negative constraints to stop generic tropes and old template artifacts
    UNIVERSAL_NEGATIVE_CONSTRAINTS = [
        "electrical safety imagery",
        "electrical outlets and sockets",
        "power strips and electric cables",
        "electrical hazard signs",
        "glowing brain",
        "generic glowing AI brain",
        "generic AI brain",
        "futuristic robot humanoid",
        "random green motherboard and circuit boards",
        "abstract floating blue cyberspace matrix",
        "unrelated corporate business office",
        "unrelated sterile indoor computer lab",
        "stock photo white backdrop",
        "low quality blurry rendering",
        "unnecessary large overlay text",
    ]

    @staticmethod
    def _normalize_str(val: Any) -> str:
        """Safely normalizes strings, lists of strings, or other types to a clean string."""
        if val is None:
            return ""
        if isinstance(val, (list, tuple, set)):
            return " ".join(GeminiVisualPipelineService._normalize_str(x) for x in val)
        return str(val).strip()

    @classmethod
    def detect_visual_purpose(cls, heading: str, matter: str = "") -> str:
        """
        Determines the slide's communication purpose from heading and matter.
        """
        heading = cls._normalize_str(heading)
        matter = cls._normalize_str(matter)
        h_lower = heading.lower()
        m_lower = matter.lower()
        combined = f"{h_lower} {m_lower}"

        if any(w in h_lower for w in ("intro", "overview", "background", "about the project", "what is")) or (
            "title" in h_lower or "cover" in h_lower
        ):
            return SlideVisualPurpose.INTRODUCTION

        if any(w in h_lower for w in ("problem", "challenge", "need", "issue", "scarcity", "deficit", "wastage")):
            return SlideVisualPurpose.PROBLEM_STATEMENT

        if any(w in h_lower for w in ("existing", "traditional", "conventional", "current system", "manual")):
            return SlideVisualPurpose.EXISTING_SYSTEM

        if any(w in h_lower for w in ("proposed", "smart", "solution", "our system", "novel")):
            return SlideVisualPurpose.PROPOSED_SYSTEM

        if any(w in h_lower for w in ("moisture", "sensor", "probe", "capacitive", "vitals", "soil moisture")) and not any(w in h_lower for w in ("architecture", "structure")):
            return SlideVisualPurpose.SOIL_MOISTURE_MONITORING

        if any(w in h_lower for w in ("ai", "machine learning", "ml", "decision", "algorithm", "intelligence", "predict")):
            return SlideVisualPurpose.AI_DECISION_MAKING

        if any(w in h_lower for w in ("architecture", "telemetry", "block diagram", "hardware stack", "topology", "layers")):
            return SlideVisualPurpose.SYSTEM_ARCHITECTURE

        if any(w in h_lower for w in ("working", "process", "workflow", "methodology", "pipeline", "sequence", "operation")):
            return SlideVisualPurpose.WORKING_PROCESS

        if any(w in h_lower for w in ("deployment", "field", "photo", "installed", "in practice", "demonstration")):
            return SlideVisualPurpose.FIELD_DEPLOYMENT

        if any(w in h_lower for w in ("result", "performance", "benchmark", "evaluation", "saving", "efficiency")):
            return SlideVisualPurpose.RESULTS

        if any(w in h_lower for w in ("future", "roadmap", "next step", "extension", "enhancement")):
            return SlideVisualPurpose.FUTURE_SCOPE

        if any(w in h_lower for w in ("conclusion", "summary", "closing")):
            return SlideVisualPurpose.CONCLUSION

        if any(w in combined for w in ("moisture", "soil", "sensor probe", "sensing", "capacitive", "humidity", "vwc")):
            return SlideVisualPurpose.SOIL_MOISTURE_MONITORING

        return SlideVisualPurpose.GENERAL_TECHNICAL

    @classmethod
    def _extract_domain_anchor(cls, project_title: str) -> str:
        """
        Extracts salient topic keywords from the project title, removing common filler/academic stopwords.
        """
        clean = cls._normalize_str(project_title).lower()
        stopwords = {
            "ai", "based", "system", "systems", "management", "smart", "using", "automated",
            "for", "the", "in", "of", "and", "a", "an", "on", "with", "to", "via", "through",
            "study", "project", "analysis", "design", "development", "implementation", "approach",
            "model", "platform", "framework", "application", "tool", "solution"
        }
        tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", clean) if w not in stopwords]
        return " ".join(tokens) if tokens else clean or "technical engineering"

    @classmethod
    def detect_project_domain_and_context(
        cls,
        project_title: str,
        project_description: str = "",
        slide_heading: str = "",
        slide_matter: str = "",
    ) -> Tuple[str, str, float]:
        """
        Dynamically determines the visual domain from the current project context.
        Uses: Project Title + Project Description + Slide Heading + Slide Matter.

        Returns: (domain_key, domain_label, confidence_score)

        STRICT RULES:
        1. NEVER defaults to agriculture/irrigation.
        2. Agriculture is ONLY returned if the project content explicitly matches agriculture/farming.
        3. Completely stateless: Evaluated fresh on every call without caching or stale cross-project state.
        """
        title_norm = cls._normalize_str(project_title).lower()
        desc_norm = cls._normalize_str(project_description).lower()
        head_norm = cls._normalize_str(slide_heading).lower()
        matter_norm = cls._normalize_str(slide_matter).lower()

        DOMAIN_PROFILES = {
            "irrigation": {
                "label": "Agriculture / Irrigation",
                "keywords": [
                    "irrigat", "soil", "moisture", "crop", "crops", "farm", "farming",
                    "farmland", "agricult", "drip", "plant", "plants", "harvest",
                    "hydrology", "agronomy", "fertiliz", "aquifer", "water canal", "cultivation"
                ],
            },
            "attendance": {
                "label": "Education / Attendance",
                "keywords": [
                    "attend", "attand", "facial", "biometric", "roll call", "presence",
                    "student", "students", "classroom", "lecture hall", "rfid", "campus",
                    "face recognition", "facial recognition", "school", "university", "faculty"
                ],
            },
            "healthcare": {
                "label": "Healthcare / Hospital",
                "keywords": [
                    "hospital", "health", "medical", "doctor", "doctors", "patient",
                    "patients", "clinic", "clinical", "nursing", "physician", "ehr",
                    "emr", "telemedicine", "pharmacy", "healthcare", "biomedical",
                    "disease", "treatment", "medicine", "triage", "radiology", "pathology"
                ],
            },
            "cybersecurity": {
                "label": "Cybersecurity / Network Security",
                "keywords": [
                    "cyber", "security", "threat", "malware", "intrusion", "firewall",
                    "soc", "phishing", "vulnerability", "encryption", "ddos",
                    "network security", "penetration", "cyberattack", "infosec", "antivirus",
                    "ransomware", "zero day", "siem", "cryptograph"
                ],
            },
            "ecommerce": {
                "label": "E-Commerce / Online Shopping",
                "keywords": [
                    "commerce", "e-commerce", "shopping", "cart", "checkout", "retail",
                    "marketplace", "inventory", "catalog", "order management", "online store",
                    "storefront", "pos", "merchandise", "logistics", "fulfillment", "supply chain"
                ],
            },
            "traffic": {
                "label": "Smart Transportation / Traffic",
                "keywords": [
                    "traffic", "vehicle", "vehicles", "transport", "transportation",
                    "road", "roads", "highway", "intersection", "transit", "congestion",
                    "traffic signal", "automotive", "fleet", "pedestrian", "mobility"
                ],
            },
            "energy": {
                "label": "Renewable Energy / Smart Grid",
                "keywords": [
                    "solar", "power grid", "microgrid", "renewable energy", "wind turbine",
                    "battery storage", "photovoltaic", "clean energy", "inverter", "substation",
                    "power plant", "grid telemetry"
                ],
            },
            "finance": {
                "label": "FinTech / Banking",
                "keywords": [
                    "bank", "banking", "fintech", "finance", "financial", "payment gateway",
                    "fraud detection", "loan", "credit", "ledger", "stock market",
                    "cryptocurrency", "wealth", "portfolio"
                ],
            },
            "robotics": {
                "label": "Robotics / Autonomous Systems",
                "keywords": [
                    "robot", "robotics", "robotic", "drone", "drones", "uav", "manipulator",
                    "autonomous mobile robot", "slam", "lidar", "rover", "quadcopter"
                ],
            },
        }

        # Weighted scoring: Title matches carry highest weight
        scores: Dict[str, float] = {}
        for d_key, d_info in DOMAIN_PROFILES.items():
            kws = d_info["keywords"]
            score = 0.0
            for kw in kws:
                if kw in title_norm:
                    score += 4.0
                if kw in desc_norm:
                    score += 2.0
                if kw in head_norm:
                    score += 1.0
                if kw in matter_norm:
                    score += 0.5
            if score > 0:
                scores[d_key] = score

        if scores:
            best_domain = max(scores.items(), key=lambda x: x[1])[0]
            best_score = scores[best_domain]
            confidence = min(1.0, round(best_score / 4.0, 2))
            label = DOMAIN_PROFILES[best_domain]["label"]
            return best_domain, label, confidence

        # Dynamic / Unknown domain handling (NEVER AGRICULTURE!)
        anchor = cls._extract_domain_anchor(project_title)
        return "dynamic_general", f"Custom Domain ({anchor.title()})", 0.35

    @classmethod
    def extract_matter_concepts(
        cls,
        heading: str,
        matter: str,
        project_title: str,
        domain: str = "dynamic_general",
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Extracts key concepts, physical objects, and subjects from the actual slide matter,
        strictly contextualized by the project domain.
        """
        heading = cls._normalize_str(heading)
        matter = cls._normalize_str(matter)
        project_title = cls._normalize_str(project_title)
        combined = f"{heading} {matter} {project_title}".lower()

        # Domain-aware entity catalog
        OBJECT_CANDIDATES = [
            # Irrigation
            ("soil moisture sensor", ["soil moisture sensor", "moisture sensor", "sensor probe", "capacitive probe", "sensor"]),
            ("plant roots", ["plant roots", "root zone", "roots", "plants", "crop"]),
            ("drip irrigation tubing", ["drip irrigation", "drip lines", "drip tubing", "emitters", "water pipe"]),
            ("solenoid water valve", ["solenoid", "valve", "water pump", "pump", "actuator"]),
            ("agricultural soil", ["soil", "farmland", "field", "ground", "earth"]),
            ("crop canopy", ["crop", "crops", "plants", "leaves", "vegetation", "canopy"]),
            ("dry cracked soil", ["dry soil", "drought", "water scarcity", "cracked earth", "water loss"]),
            ("traditional water furrow", ["flood irrigation", "furrow", "manual hose", "channel"]),
            # Attendance
            ("facial recognition camera", ["face recognition", "facial recognition", "attendance camera", "biometric camera", "cctv", "camera module"]),
            ("biometric attendance terminal", ["biometric", "attendance terminal", "rfid scanner", "fingerprint", "attendance"]),
            ("attendance ledger sheet", ["roll call", "attendance sheet", "register", "paper log"]),
            ("classroom lecture hall", ["classroom", "lecture hall", "students", "campus", "school", "college"]),
            # Healthcare
            ("electronic health record terminal", ["ehr", "emr", "medical record", "patient file", "charting"]),
            ("clinical patient monitor", ["patient monitor", "vital signs", "telemetry monitor", "oximeter", "ecg"]),
            ("digital prescription interface", ["prescription", "pharmacy", "medication", "dosage"]),
            ("hospital nursing station", ["nursing station", "hospital ward", "clinic desk", "hospital reception"]),
            ("hospital consultation desk", ["doctor desk", "consultation room", "examination room", "physician desk"]),
            # Cybersecurity
            ("security operations center monitor", ["soc", "security operations", "cyber monitoring", "threat screen"]),
            ("firewall gateway appliance", ["firewall", "gateway", "network appliance", "packet filter"]),
            ("network packet inspection console", ["packet inspection", "wireshark", "deep packet", "network stream"]),
            ("threat telemetry dashboard", ["threat dashboard", "incident response", "siem", "malware log"]),
            ("server rack infrastructure", ["server rack", "datacenter", "servers", "mainframe"]),
            # E-Commerce
            ("e-commerce storefront display", ["storefront", "online store", "product catalog", "web shop"]),
            ("digital shopping cart checkout interface", ["shopping cart", "checkout", "payment screen", "billing gateway"]),
            ("warehouse inventory scanner", ["inventory scanner", "barcode scanner", "rfid warehouse", "pallet"]),
            ("order fulfillment dispatch station", ["fulfillment", "order packaging", "dispatch counter", "logistics hub"]),
            # Traffic
            ("smart traffic signal controller", ["traffic signal", "traffic light", "signal controller", "intersection control"]),
            ("traffic monitoring surveillance camera", ["traffic camera", "surveillance camera", "road camera", "cctv road"]),
            ("vehicular flow sensor", ["vehicle sensor", "inductive loop", "traffic radar", "speed detector"]),
            ("urban transit command console", ["traffic control center", "transit console", "urban mobility screen"]),
            # Energy
            ("solar photovoltaic inverter array", ["solar", "photovoltaic", "solar panel", "inverter"]),
            ("smart energy storage battery", ["battery storage", "bess", "lithium battery", "accumulator"]),
            ("grid telemetry monitoring panel", ["power grid", "substation", "grid telemetry", "distribution panel"]),
            # Finance
            ("financial transaction processing terminal", ["transaction terminal", "payment gateway", "banking terminal", "pos"]),
            ("digital banking verification screen", ["banking dashboard", "ledger screen", "fraud check", "account balance"]),
            # Robotics
            ("autonomous mobile robot chassis", ["robot chassis", "amr", "agv", "mobile robot", "rover"]),
            ("robotic sensor array with lidar", ["lidar", "ultrasonic sensor", "depth camera", "robot arm"]),
            # Common Hardware
            ("IoT microcontroller", ["esp32", "microcontroller", "iot controller", "edge node", "gateway", "lora", "raspberry pi"]),
            ("system workstation monitor", ["workstation", "computer monitor", "operator screen", "control console"]),
            ("weather station", ["weather", "ambient temperature", "humidity", "rain gauge"]),
            ("solar panel", ["solar", "battery", "photovoltaic"]),
        ]

        found_objects = []
        for canonical, triggers in OBJECT_CANDIDATES:
            if any(t in combined for t in triggers):
                found_objects.append(canonical)

        # Domain-aware default objects if none found
        if not found_objects:
            if domain == "irrigation":
                found_objects = ["healthy crop plants", "agricultural soil", "irrigation tubing"]
            elif domain == "attendance":
                found_objects = ["facial recognition camera", "classroom lecture hall", "attendance terminal"]
            elif domain == "healthcare":
                found_objects = ["clinical patient monitor", "hospital workstation", "electronic health record system"]
            elif domain == "cybersecurity":
                found_objects = ["security operations center monitor", "network firewall appliance", "threat detection console"]
            elif domain == "ecommerce":
                found_objects = ["e-commerce digital interface", "inventory management terminal", "order checkout station"]
            elif domain == "traffic":
                found_objects = ["smart traffic signal controller", "traffic surveillance camera", "urban transit monitor"]
            elif domain == "energy":
                found_objects = ["solar inverter array", "power grid telemetry panel", "battery storage system"]
            elif domain == "finance":
                found_objects = ["transaction processing terminal", "banking dashboard", "digital payment gateway"]
            elif domain == "robotics":
                found_objects = ["autonomous mobile robot", "robotic control unit", "navigation telemetry display"]
            else:
                anchor = cls._extract_domain_anchor(project_title)
                found_objects = [f"{anchor} controller unit", f"{anchor} monitoring terminal", "operational telemetry interface"]

        # Extract technical concepts based on domain and text
        found_concepts: List[str] = []
        if domain == "irrigation":
            CONCEPT_CANDIDATES = [
                "volumetric water content", "evapotranspiration", "threshold trigger",
                "autonomous irrigation", "water conservation", "precision agriculture",
                "edge AI inference", "telemetry communication", "sensor calibration",
                "leak detection", "closed-loop control", "crop hydrology"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]
        elif domain == "attendance":
            CONCEPT_CANDIDATES = [
                "facial landmark detection", "feature embedding extraction", "biometric enrollment",
                "automated roll call commit", "liveness verification", "roster synchronization",
                "real-time student tracking", "high recognition accuracy", "low inference latency"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]
        elif domain == "healthcare":
            CONCEPT_CANDIDATES = [
                "electronic health records", "clinical triage prioritization", "patient vital telemetry",
                "hospital bed management", "diagnostic workflow optimization", "digital prescription commit",
                "patient wait time reduction", "clinical throughput efficiency"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]
        elif domain == "cybersecurity":
            CONCEPT_CANDIDATES = [
                "deep packet inspection", "intrusion prevention system", "zero-day threat classification",
                "anomaly telemetry scoring", "automated IP quarantine", "malicious payload neutralization",
                "sub-second mitigation latency", "security incident analytics"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]
        elif domain == "ecommerce":
            CONCEPT_CANDIDATES = [
                "real-time inventory synchronization", "secure checkout verification", "personalized recommendation engine",
                "dynamic demand forecasting", "automated order fulfillment", "multichannel sales telemetry"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]
        elif domain == "traffic":
            CONCEPT_CANDIDATES = [
                "adaptive signal phase timing", "vehicular density estimation", "congestion bottleneck mitigation",
                "urban mobility optimization", "intelligent transit priority", "traffic telemetry analytics"
            ]
            found_concepts = [c for c in CONCEPT_CANDIDATES if any(w in combined for w in c.split())]

        if not found_concepts:
            anchor = cls._extract_domain_anchor(project_title)
            found_concepts = [heading.lower(), f"{anchor} telemetry", "system operational monitoring"]

        # Required subjects based on objects and domain (NEVER universal agriculture fallback)
        if domain == "irrigation":
            default_subj = "agricultural environment"
        elif domain == "attendance":
            default_subj = "educational classroom environment"
        elif domain == "healthcare":
            default_subj = "hospital clinical environment"
        elif domain == "cybersecurity":
            default_subj = "cybersecurity operations center"
        elif domain == "ecommerce":
            default_subj = "e-commerce operational platform"
        elif domain == "traffic":
            default_subj = "urban smart transportation network"
        else:
            anchor = cls._extract_domain_anchor(project_title)
            default_subj = f"operational {anchor} environment"

        subjects = [found_objects[0]] if found_objects else [default_subj]
        if len(found_objects) > 1:
            subjects.append(found_objects[1])

        return found_concepts[:5], found_objects[:4], subjects[:3]

    @classmethod
    def compile_visual_requirement(
        cls,
        project_title: str,
        slide_heading: str,
        slide_matter: str,
        slide_index: int = 1,
        project_description: str = "",
    ) -> SlideVisualRequirement:
        """
        Compiles the authoritative SlideVisualRequirement (Step 1).
        Enforces: Slide Heading + Subheading + Slide Matter > Project Name.
        Strictly prohibits unrelated graphs/charts for non-quantitative slides.
        Dynamically detects project domain with ZERO agriculture fallback for non-agriculture projects.
        """
        from apps.api.services.visual_decision_engine import VisualType

        project_title = cls._normalize_str(project_title)
        slide_heading = cls._normalize_str(slide_heading)
        slide_matter = cls._normalize_str(slide_matter)
        purpose = cls.detect_visual_purpose(slide_heading, slide_matter)

        # Dynamic, stateless domain detection fresh per request
        domain, domain_label, confidence = cls.detect_project_domain_and_context(
            project_title=project_title,
            project_description=project_description,
            slide_heading=slide_heading,
            slide_matter=slide_matter,
        )

        concepts, objects, subjects = cls.extract_matter_concepts(
            heading=slide_heading,
            matter=slide_matter,
            project_title=project_title,
            domain=domain,
        )

        # Map to Canonical Visual Types according to ARM Specification
        if domain == "attendance":
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern university lecture hall or smart campus classroom with students seated"
                v_style = "natural realistic educational photography, daylight classroom lighting, sharp depth of field"
                subjects = ["modern educational classroom", "automated attendance recognition setup"]
                objects = ["lecture hall seating", "mounted camera sensor", "students learning"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "busy college classroom with teacher manually marking paper attendance register"
                v_style = "realistic documentary photography, authentic indoor lighting, focused composition"
                subjects = ["manual paper roll call register", "teacher marking attendance with pen"]
                objects = ["paper attendance sheet", "pen and register logbook", "lecture desk"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional classroom desk with manual paper attendance logbook and pen"
                v_style = "authentic documentary photography, realistic indoor classroom environment"
                subjects = ["traditional manual paper attendance register", "handwritten roll call sheet"]
                objects = ["printed attendance ledger", "ballpoint pen", "classroom desk"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern classroom entrance or lecture podium equipped with smart facial recognition camera"
                v_style = "professional clean technological photography, crisp daylight focus"
                subjects = ["automated AI facial recognition attendance system scanning students"]
                objects = ["high-resolution optical camera module", "status display terminal", "lecture entrance"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up of mounted AI vision sensor camera capturing facial features"
                v_style = "sharp macro photography, clean lighting, shallow depth of field focusing on optical sensor"
                subjects = ["optical camera sensor module for real-time facial recognition"]
                objects = ["camera lens", "compact edge computing enclosure", "status LED indicator"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "digital biometric interface overlay showing facial landmark detection and confidence scores"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["AI face detection algorithm matching student identity against secure database"]
                objects = ["bounding box face landmarks", "match confidence percentage", "student ID confirmation"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean hardware setup showing edge camera unit, local processing board, and cloud attendance database"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["AI attendance architecture pipeline connecting edge camera to university database"]
                objects = ["camera module", "edge processing unit", "network switch", "database server icon"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing video stream acquisition, face detection, feature extraction, and database logging"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["end-to-end automated attendance pipeline from video capture to database update"]
                objects = ["video frame capture", "face embedding comparison", "timestamped attendance record"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world university lecture hall with wall-mounted AI attendance camera actively operating during class"
                v_style = "wide-angle realistic institutional photography, authentic classroom setting, natural ambient lighting"
                subjects = ["students in lecture hall with non-intrusive automated attendance camera mounted on wall"]
                objects = ["wall-mounted camera device", "lecture hall rows", "engaged college students"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "digital institutional dashboard displaying automated attendance statistics and accuracy analytics"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = ["real-time attendance metrics dashboard with high recognition accuracy and low latency"]
                objects = ["attendance percentage charts", "student log verification table", "accuracy telemetry"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation smart university campus with seamless contactless biometric access and multi-camera coverage"
                v_style = "forward-looking clean realistic photography, expansive campus architecture, inspiring lighting"
                subjects = ["integrated smart campus ecosystem with contactless biometric authentication"]
                objects = ["smart campus entrance", "connected biometric terminals", "cloud infrastructure"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern high-tech educational campus featuring automated smart attendance operations"
                v_style = "clean professional photography, warm natural daylight, sharp depth of field"
                subjects = ["fully deployed automated AI attendance system in active institutional operation"]
                objects = ["smart campus classroom", "operational attendance camera", "successful student check-in"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "institutional academic laboratory setting with AI computer vision attendance setup"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["AI attendance recognition system setup"]
                objects = ["camera module", "computer screen showing verification", "academic workstation"]

        elif domain == "irrigation":
            # Standard Agricultural / Irrigation domain (strictly preserved for AI Irrigation)
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "sunlit lush commercial agricultural farm with healthy crop rows"
                v_style = "natural realistic agricultural photography, golden hour daylight, sharp depth of field"
                subjects = ["healthy green crop field", "modern clean precision farm landscape"]
                objects = ["vibrant growing crops", "neat planting rows", "subtle clean drip irrigation lines"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "parched agricultural field under intense harsh sun, demonstrating severe water shortage"
                v_style = "realistic documentary photography, dramatic warm lighting, stark texture contrast"
                subjects = ["dry agricultural soil", "water-stressed crop plants"]
                objects = ["parched earth textures", "fissured soil ground", "water shortage context"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional conventional agricultural field using flood or furrow irrigation"
                v_style = "authentic documentary agricultural photography, realistic outdoor environment"
                subjects = ["traditional conventional irrigation", "unmetered water flowing in soil furrows"]
                objects = ["open water furrows", "traditional manual water gates", "muddy soil channels"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern precision agricultural plot equipped with automated smart drip irrigation"
                v_style = "professional clean technological photography, crisp daylight focus"
                subjects = ["automated drip irrigation lines delivering water directly to plant root zones"]
                objects = ["clean drip emitters with gentle water drops", "healthy nourished crops", "low-profile smart controller"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up ground-level agricultural soil bed near plant root systems"
                v_style = "sharp macro photography, natural soil lighting, shallow depth of field focusing on sensor probe"
                subjects = ["soil moisture sensor probe inserted into damp dark agricultural earth near plant stem"]
                objects = ["capacitive moisture probe prongs in soil", "healthy green plant base", "dark moist soil texture"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "agricultural field overlay with clear agronomic data indicators and moisture threshold logic"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["agricultural field with scientific moisture thresholds and decision logic"]
                objects = ["sensor reading telemetry", "crop health indicators", "decision metric callout"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean professional hardware setup showing edge telemetry nodes, cloud AI, and actuator valves"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["smart edge IoT telemetry node connected to solenoid valve and field sensors"]
                objects = ["weatherproof IoT enclosure", "12V solenoid valve", "connecting telemetry cables", "sensor probe"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing closed-loop sensing, analysis, and automated water delivery"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["precision water delivery process in action triggered by real-time soil condition"]
                objects = ["water droplet release from drip line", "active root zone absorption", "calibrated sensor"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world open-air agricultural field plot with fully operational installed smart irrigation system"
                v_style = "wide-angle realistic field photography, authentic farm setting, daytime natural lighting"
                subjects = ["wide crop rows with installed solar-powered IoT telemetry node on pole"]
                objects = ["pole-mounted solar IoT node", "extensive drip irrigation tubing across field", "thriving green crops"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "bountiful healthy harvest plot showcasing vigorous crop development and clean water conservation"
                v_style = "high-contrast professional photography, rich natural colors, bright clear lighting"
                subjects = ["abundant healthy crop yield with minimal water consumption"]
                objects = ["flourishing crop produce", "well-hydrated root zones", "optimized water delivery lines"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation sustainable agro-ecosystem with precision aerial telemetry and solar micro-irrigation"
                v_style = "forward-looking clean realistic photography, expansive open sky, inspiring natural lighting"
                subjects = ["advanced precision farm landscape with integrated multi-sensor telemetry"]
                objects = ["solar-powered smart irrigation array", "broad sustainable crop perimeter"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "flourishing modern agricultural farm with sustainable water irrigation operations"
                v_style = "clean professional photography, golden hour natural daylight, sharp depth of field"
                subjects = ["sustainable irrigated farmland", "thriving crop rows"]
                objects = ["healthy crop plants", "irrigation system in operation", "sustainable farm field"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "agricultural field setting with dedicated technical precision irrigation hardware"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["smart precision irrigation setup"]
                objects = ["crop plants", "soil moisture hardware", "drip tubing"]

        elif domain == "healthcare":
            # Healthcare / Hospital Management System domain
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern hospital healthcare facility with clean medical reception and clinical staff"
                v_style = "natural realistic medical photography, bright clean clinical daylight, sharp depth of field"
                subjects = ["modern healthcare hospital setting", "hospital management technology infrastructure"]
                objects = ["clinical ward reception", "medical staff workstation", "digital hospital signage"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "busy hospital administrative desk with disorganized paper medical charts and patient queues"
                v_style = "realistic documentary photography, authentic indoor hospital lighting, focused composition"
                subjects = ["paper medical record binders", "healthcare workers managing manual patient logs"]
                objects = ["stacks of paper patient files", "manual clinic clipboard", "hospital reception desk"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional clinic doctor consultation desk with physical paper prescription pads and filing cabinets"
                v_style = "authentic documentary medical photography, realistic indoor clinical environment"
                subjects = ["traditional manual paper medical charting", "physical clinic record storage"]
                objects = ["paper medical case sheets", "consultation desk", "metal medical filing cabinet"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern integrated hospital consultation room with doctor using smart electronic health record workstation"
                v_style = "professional clean healthcare technology photography, crisp daylight focus"
                subjects = ["streamlined digital hospital management system actively displaying patient telemetry"]
                objects = ["clinical workstation monitor", "digital patient profile", "modern consultation room"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up of digital medical patient monitoring sensor and diagnostic interface"
                v_style = "sharp macro photography, clean clinical lighting, shallow depth of field focusing on medical instrumentation"
                subjects = ["biomedical patient vital signs sensor and digital telemetry monitor"]
                objects = ["vital signs sensor probe", "digital patient monitor display", "clean clinical cart"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "clinical intelligence analytics dashboard showing triage optimization and patient recovery trends"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["AI-assisted clinical decision support system analyzing patient vitals and treatment pathways"]
                objects = ["diagnostic analytics chart", "risk prediction telemetry", "patient status indicators"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean enterprise healthcare infrastructure diagram connecting hospital EMR server, doctor terminals, and patient portal"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["hospital management system multi-tier architecture connecting clinical wards, pharmacy, and central database"]
                objects = ["hospital database server", "clinical terminal icon", "secure API gateway", "patient mobile app portal"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing patient check-in, triage assessment, doctor consultation, digital prescription, and billing"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["end-to-end patient workflow through hospital management system"]
                objects = ["patient registration node", "EHR record lookup", "treatment pathway", "automated billing commit"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world operating hospital ward with clinical staff using tablet computers and wall-mounted digital management displays"
                v_style = "wide-angle realistic clinical photography, authentic hospital ward setting, bright professional lighting"
                subjects = ["nurses and doctors in hospital corridor utilizing digital management terminals for patient care"]
                objects = ["mobile clinical workstation", "wall-mounted bed availability display", "modern hospital corridor"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "hospital administration analytics dashboard displaying reduced wait times, bed occupancy rates, and patient throughput"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = ["healthcare management performance metrics showing 40% reduction in patient wait times and high operational throughput"]
                objects = ["bed occupancy graph", "average wait time telemetry", "clinical throughput chart"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation interconnected smart hospital with AI-driven remote telemedicine and robotic pharmacy dispensing"
                v_style = "forward-looking clean realistic photography, expansive modern medical center architecture, inspiring lighting"
                subjects = ["connected digital healthcare ecosystem with remote patient monitoring and automated clinical robotics"]
                objects = ["smart hospital campus", "telemedicine conference screen", "automated medical dispensing unit"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern state-of-the-art medical center showcasing fully operational digital healthcare workflow"
                v_style = "clean professional photography, warm natural daylight, sharp depth of field"
                subjects = ["successfully deployed hospital management system empowering clinical teams and patient care"]
                objects = ["contemporary hospital lobby", "active digital consultation counters", "satisfied patients"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "professional healthcare medical center setting with clinical IT workstation"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["hospital management software terminal and clinical equipment"]
                objects = ["medical monitor", "clinical workstation desk", "hospital management interface"]

        elif domain == "cybersecurity":
            # Cybersecurity / Threat Detection domain
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern enterprise cybersecurity operations center (SOC) with security analysts monitoring network activity"
                v_style = "natural realistic technological photography, professional dark ambient SOC lighting, sharp depth of field"
                subjects = ["security operations center analyst environment", "cyber threat intelligence monitoring screens"]
                objects = ["multi-monitor analyst workstation", "live network telemetry screen", "secure SOC facility"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "enterprise IT server infrastructure experiencing sophisticated unauthorized intrusion attempts and data breaches"
                v_style = "realistic documentary photography, dramatic atmospheric lighting, focused composition"
                subjects = ["compromised network infrastructure", "unauthorized cyber intrusion indicators"]
                objects = ["server rack warning indicators", "unauthorized access logs", "network perimeter alert"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "legacy IT security room relying on static rule-based firewalls and manual antivirus log inspection"
                v_style = "authentic documentary photography, realistic indoor server room environment"
                subjects = ["traditional rule-based network security", "outdated static firewall appliances"]
                objects = ["legacy firewall hardware", "printed network logs", "unmanaged server console"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern secure datacenter facility equipped with automated AI cyber threat detection appliances"
                v_style = "professional clean technological photography, crisp focus"
                subjects = ["AI-powered threat detection system actively filtering malicious network packets"]
                objects = ["high-throughput security appliance", "status LED telemetry", "secure server rack"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up of enterprise network security hardware appliance with active fiber optic packet inspection links"
                v_style = "sharp macro photography, clean lighting, shallow depth of field"
                subjects = ["network telemetry packet capture hardware module"]
                objects = ["fiber optic patch cables", "high-speed network interface", "status telemetry indicators"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "cybersecurity analytics dashboard displaying neural anomaly detection and automated threat risk scoring"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["machine learning intrusion detection engine classifying zero-day attack vectors"]
                objects = ["anomaly risk scoring metric", "attack vector telemetry", "quarantine trigger indicators"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean cybersecurity architecture diagram connecting edge packet sensors, SIEM engine, and incident response server"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["threat detection architecture pipeline connecting network firewalls, ML engine, and security database"]
                objects = ["perimeter firewall icon", "ML inference engine", "central SIEM database", "analyst console"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing packet capture, feature extraction, ML anomaly detection, and automated IP quarantine"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["end-to-end automated cyber defense pipeline from traffic ingestion to threat neutralization"]
                objects = ["packet ingestion node", "feature vector extraction", "threat classifier", "automated quarantine commit"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world enterprise datacenter with security operations engineers actively managing cyber defenses"
                v_style = "wide-angle realistic IT photography, authentic datacenter setting, cool ambient lighting"
                subjects = ["security engineers in enterprise datacenter overseeing live threat mitigation systems"]
                objects = ["datacenter server rows", "monitoring consoles", "active enterprise hardware"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "cybersecurity performance analytics dashboard displaying 99.8% threat mitigation rate and sub-second response latency"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = ["cyber defense benchmarks showing rapid intrusion containment and near-zero false positives"]
                objects = ["threat mitigation percentage chart", "response latency graph", "quarantine event logs"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation autonomous cyber defense grid with quantum-safe encryption and predictive threat intelligence"
                v_style = "forward-looking clean realistic photography, expansive futuristic server facility, inspiring lighting"
                subjects = ["quantum-resistant autonomous cyber defense ecosystem"]
                objects = ["quantum security terminal", "distributed threat intelligence nodes", "secure network infrastructure"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "secure modern digital enterprise infrastructure protected by automated AI threat intelligence"
                v_style = "clean professional photography, sharp depth of field"
                subjects = ["fully deployed cyber threat defense system successfully safeguarding enterprise operations"]
                objects = ["active SOC consoles", "secure server facilities", "resilient digital enterprise"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "cybersecurity research laboratory workstation with live network threat monitoring screens"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["cyber defense workstation and network analysis setup"]
                objects = ["network packet monitor", "security appliance", "academic workstation"]

        elif domain == "ecommerce":
            # E-Commerce / Online Shopping domain
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern digital e-commerce marketplace platform displaying products and responsive shopping interfaces"
                v_style = "natural realistic commercial photography, bright clean lighting, sharp depth of field"
                subjects = ["digital e-commerce marketplace platform", "online customer shopping ecosystem"]
                objects = ["responsive storefront screen", "product catalog display", "digital shopping interface"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional retail store facing inventory stockouts, disorganized manual billing, and limited customer reach"
                v_style = "realistic documentary photography, authentic ambient lighting, focused composition"
                subjects = ["manual retail inventory challenges", "traditional store sales bottlenecks"]
                objects = ["disorganized store shelves", "manual paper ledger", "checkout queue"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional retail counter using standalone manual cash registers and physical ledger logbooks"
                v_style = "authentic documentary photography, realistic retail environment"
                subjects = ["traditional manual retail checkout", "isolated cash register systems"]
                objects = ["mechanical cash register", "printed receipt rolls", "physical inventory binder"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern cloud-native e-commerce management workstation with real-time inventory synchronization"
                v_style = "professional clean technological photography, crisp daylight focus"
                subjects = ["smart e-commerce platform actively managing customer orders and multichannel inventory"]
                objects = ["modern management dashboard", "digital inventory console", "secure payment terminal"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up of modern point-of-sale barcode scanner and contactless payment terminal"
                v_style = "sharp macro photography, clean lighting, shallow depth of field"
                subjects = ["digital retail inventory barcode scanner and contactless payment verification terminal"]
                objects = ["optical barcode scanner", "contactless payment card reader", "digital receipt screen"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "e-commerce analytics interface showing AI customer product recommendation vectors and dynamic demand pricing"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["machine learning recommendation algorithm predicting consumer purchasing patterns"]
                objects = ["recommendation accuracy metrics", "customer demand curve", "conversion optimization telemetry"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean e-commerce microservices architecture connecting web storefront, payment gateway, and warehouse database"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["scalable e-commerce platform architecture connecting shopping cart, payment API, and fulfillment server"]
                objects = ["web storefront portal", "payment gateway icon", "inventory database server", "fulfillment node"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing product discovery, cart addition, encrypted checkout, and automated warehouse dispatch"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["end-to-end e-commerce order fulfillment pipeline from click to delivery"]
                objects = ["product selection step", "payment authentication", "order commit", "logistics dispatch notification"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world automated order fulfillment center with logistics packing stations and digital management displays"
                v_style = "wide-angle realistic logistics photography, authentic warehouse setting, bright clear lighting"
                subjects = ["fulfillment logistics workers packaging customer orders using digital tracking tablets"]
                objects = ["automated sorting conveyor", "digital packing terminal", "neatly organized inventory racks"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "e-commerce business performance dashboard displaying 45% conversion uplift and sub-second page loads"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = ["sales performance analytics demonstrating rapid checkout conversion and zero cart abandonment"]
                objects = ["revenue growth chart", "conversion rate telemetry", "order completion logs"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation omnichannel retail ecosystem with augmented reality shopping and autonomous drone delivery"
                v_style = "forward-looking clean realistic photography, expansive modern retail hub, inspiring lighting"
                subjects = ["future intelligent retail marketplace with immersive shopping experiences"]
                objects = ["AR product visualization screen", "connected delivery drone station", "smart logistics network"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "thriving modern commercial enterprise successfully utilizing automated e-commerce infrastructure"
                v_style = "clean professional photography, sharp depth of field"
                subjects = ["fully deployed e-commerce management platform driving multichannel retail growth"]
                objects = ["active commerce control room", "online customer order monitors", "commercial enterprise setting"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "digital retail operations workstation with e-commerce management software"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["e-commerce management terminal and digital storefront interface"]
                objects = ["online catalog monitor", "order management console", "commercial workstation"]

        elif domain == "traffic":
            # Smart Traffic Management System domain
            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "urban smart transportation corridor with connected vehicles and intelligent traffic signal infrastructure"
                v_style = "natural realistic urban photography, daylight city lighting, sharp depth of field"
                subjects = ["smart city traffic management ecosystem", "modern intelligent roadway intersection"]
                objects = ["intelligent traffic signal heads", "overhead road surveillance cameras", "flowing urban traffic"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "congested urban street intersection suffering severe vehicle gridlock, idling emissions, and long commuter delays"
                v_style = "realistic documentary photography, authentic city atmospheric lighting, focused composition"
                subjects = ["heavy urban traffic gridlock", "congested roadway bottlenecks"]
                objects = ["dense lines of stopped vehicles", "congested intersection", "commuter delay indicators"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traditional city roadway intersection operating on fixed-timer traffic signals regardless of actual traffic density"
                v_style = "authentic documentary photography, realistic urban street environment"
                subjects = ["conventional static traffic light timer", "unresponsive manual traffic control"]
                objects = ["traditional electromechanical signal box", "fixed timer lights", "unmonitored roadway"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "modern smart intersection equipped with AI adaptive signal controllers and dynamic phase adjustments"
                v_style = "professional clean technological photography, crisp daylight focus"
                subjects = ["automated AI smart traffic management system dynamically regulating green light durations"]
                objects = ["intelligent signal controller enclosure", "pole-mounted vehicle sensor", "smoothly clearing intersection"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = "close-up of roadway vehicle detection radar and roadside edge computing telemetry unit"
                v_style = "sharp macro photography, clean lighting, shallow depth of field focusing on traffic sensor"
                subjects = ["optical and radar vehicular detection sensor module"]
                objects = ["high-accuracy traffic radar sensor", "weatherproof roadside enclosure", "status telemetry indicators"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "traffic control center analytics display showing dynamic green light timing calculations and queue length predictions"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = ["machine learning traffic optimization algorithm balancing urban network flow"]
                objects = ["queue length telemetry graph", "signal phase timing chart", "congestion reduction metric"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = "clean intelligent transportation system architecture connecting road sensors, edge signal controllers, and central traffic server"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = ["multi-tier traffic management architecture connecting intersection nodes to municipal control center"]
                objects = ["roadside controller node", "fiber optic network link", "traffic management server", "operator console"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = "stepped sequence showing vehicle density capture, queue length estimation, adaptive phase calculation, and signal switching"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = ["end-to-end adaptive traffic signal pipeline from vehicle detection to green light extension"]
                objects = ["vehicle detection node", "density computation step", "phase optimization trigger", "signal actuation commit"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = "real-world metropolitan traffic command center with operators monitoring citywide traffic cameras and signal telemetry"
                v_style = "wide-angle realistic municipal photography, authentic control room setting, clean ambient lighting"
                subjects = ["traffic control operators managing citywide signal networks on large multi-screen video walls"]
                objects = ["municipal video monitoring wall", "operator workstations", "live traffic telemetry feeds"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = "urban transit analytics dashboard displaying 35% reduction in commuter travel times and reduced vehicle idling"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = ["traffic engineering performance metrics showing significant delay reduction and improved network flow"]
                objects = ["commuter delay reduction chart", "average speed telemetry", "intersection throughput graph"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = "next-generation connected vehicle ecosystem with V2X vehicle-to-infrastructure communication and autonomous fleet coordination"
                v_style = "forward-looking clean realistic photography, expansive smart city boulevard, inspiring lighting"
                subjects = ["future intelligent transportation network with automated connected vehicle routing"]
                objects = ["smart mobility corridor", "connected transit vehicles", "smart city digital infrastructure"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = "modern metropolitan avenue with smoothly flowing vehicular traffic under coordinated AI traffic signal management"
                v_style = "clean professional photography, sharp depth of field"
                subjects = ["fully deployed smart traffic management system creating efficient congestion-free urban mobility"]
                objects = ["well-managed city intersection", "clear roadway lanes", "active smart traffic infrastructure"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = "traffic engineering research laboratory with simulation workstations and signal controllers"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = ["smart traffic management control console and simulation monitors"]
                objects = ["traffic simulation display", "signal controller hardware", "academic workstation"]

        else:
            # Dynamic / General Engineering domain (Adaptive to Project Title & Slide Heading - ZERO AGRICULTURE FALLBACK)
            anchor = cls._extract_domain_anchor(project_title)
            anchor_title = anchor.title()

            if purpose == SlideVisualPurpose.INTRODUCTION:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"professional technological setting demonstrating real-world operational {anchor} environment"
                v_style = "natural realistic technological photography, daylight focus, sharp depth of field"
                subjects = [f"operational {anchor} deployment", f"core {project_title} infrastructure"]
                objects = [f"{anchor} hardware modules", "system monitoring terminal", "operational setup"]

            elif purpose == SlideVisualPurpose.PROBLEM_STATEMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"operational facility experiencing inefficiencies, delays, and critical bottlenecks in {anchor} operations"
                v_style = "realistic documentary photography, authentic ambient lighting, focused composition"
                subjects = [f"operational challenges and manual bottlenecks in {anchor}"]
                objects = ["legacy equipment", "manual logging records", "operational bottleneck indicators"]

            elif purpose == SlideVisualPurpose.EXISTING_SYSTEM:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"conventional legacy facility utilizing manual or unautomated methods for {anchor}"
                v_style = "authentic documentary photography, realistic environment"
                subjects = [f"traditional conventional {anchor} methods", "manual operational workflows"]
                objects = ["manual controls", "outdated legacy equipment", "paper records"]

            elif purpose == SlideVisualPurpose.PROPOSED_SYSTEM:
                v_type = VisualType.TECHNICAL_PHOTO
                env = f"advanced modern facility equipped with automated {project_title} technology"
                v_style = "professional clean technological photography, crisp focus"
                subjects = [f"intelligent {project_title} system in active operation"]
                objects = [f"specialized {anchor} controller", "digital status display", "modern operating station"]

            elif purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING:
                v_type = VisualType.TECHNICAL_PHOTO
                env = f"close-up view of technical sensor probes and edge telemetry hardware for {anchor}"
                v_style = "sharp macro photography, clean lighting, shallow depth of field"
                subjects = [f"specialized sensor instrumentation for real-time {anchor} monitoring"]
                objects = ["calibrated sensor probe", "compact hardware enclosure", "status telemetry readout"]

            elif purpose == SlideVisualPurpose.AI_DECISION_MAKING:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = f"high-tech telemetry interface displaying machine learning inference models and decision metrics for {anchor}"
                v_style = "clean academic technological visual, balanced composition, realistic background with subtle telemetry overlay"
                subjects = [f"algorithmic decision-making pipeline optimizing {anchor} performance"]
                objects = ["predictive analytics metrics", "decision threshold indicators", "performance telemetry"]

            elif purpose == SlideVisualPurpose.SYSTEM_ARCHITECTURE:
                v_type = VisualType.SYSTEM_ARCHITECTURE_CANONICAL
                env = f"clean industrial system architecture showing edge nodes, central processing unit, and cloud database for {project_title}"
                v_style = "crisp technical industrial diagram, clean academic presentation lighting"
                subjects = [f"multi-tier technical architecture pipeline connecting sensors, controller, and server database for {project_title}"]
                objects = [f"{anchor} controller node", "network gateway", "central database server", "user terminal"]

            elif purpose == SlideVisualPurpose.WORKING_PROCESS:
                v_type = VisualType.FLOWCHART_CANONICAL
                env = f"stepped sequential operational diagram showing data ingestion, analysis, and automated execution in {project_title}"
                v_style = "clean process diagrammatic illustration, sequential visual clarity"
                subjects = [f"end-to-end working process pipeline for {anchor} operations"]
                objects = ["data acquisition node", "computational processing step", "automated control trigger"]

            elif purpose == SlideVisualPurpose.FIELD_DEPLOYMENT:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"real-world field deployment setting with fully operational installed {project_title} hardware and active monitoring"
                v_style = "wide-angle realistic photography, authentic real-world setting, natural lighting"
                subjects = [f"operational {project_title} system actively deployed and functioning in real-world environment"]
                objects = ["deployed hardware units", "connecting telemetry cabling", "active operational setting"]

            elif purpose == SlideVisualPurpose.RESULTS:
                has_quant = any(char.isdigit() for char in slide_matter)
                v_type = VisualType.CHART if has_quant else VisualType.CONCEPTUAL_ILLUSTRATION
                env = f"digital telemetry dashboard displaying verified quantitative performance improvements and accuracy in {anchor}"
                v_style = "high-contrast professional photography, crisp clean screen interface, modern lighting"
                subjects = [f"real-world performance metrics showing significant optimization and high operational efficiency in {anchor}"]
                objects = ["performance telemetry chart", "efficiency comparison metric", "system status logs"]

            elif purpose == SlideVisualPurpose.FUTURE_SCOPE:
                v_type = VisualType.CONCEPTUAL_ILLUSTRATION
                env = f"next-generation forward-looking ecosystem with advanced autonomous scaling and cloud telemetry for {anchor}"
                v_style = "forward-looking clean realistic photography, expansive open perspective, inspiring lighting"
                subjects = [f"future development roadmap with integrated cloud intelligence and automated expansion for {anchor}"]
                objects = ["smart infrastructure array", "scalable network nodes", "next-generation technology setup"]

            elif purpose == SlideVisualPurpose.CONCLUSION:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"modern cutting-edge technological setting showcasing complete operational success of {project_title}"
                v_style = "clean professional photography, natural lighting, sharp depth of field"
                subjects = [f"fully deployed {project_title} delivering measurable real-world outcomes"]
                objects = ["operational installation", "active system monitors", "satisfied operators"]

            else:
                v_type = VisualType.REALISTIC_PHOTO
                env = f"technological laboratory setting with dedicated {anchor} hardware"
                v_style = "clean academic photography, natural daytime lighting"
                subjects = [f"{project_title} setup"]
                objects = [f"{anchor} hardware modules", "system monitoring screen", "workstation"]

        # Build dynamic prompt (Step 4)
        clean_matter = " ".join(slide_matter.split()[:40]) if slide_matter else ""
        matter_context = f"The slide explains: '{clean_matter}'." if clean_matter else ""

        # Display purpose formatted appropriately for domain
        if purpose == SlideVisualPurpose.SOIL_MOISTURE_MONITORING and domain != "irrigation":
            if domain == "healthcare":
                disp_purpose = "Biomedical Sensor Monitoring"
            elif domain == "attendance":
                disp_purpose = "Vision Sensor Monitoring"
            elif domain == "cybersecurity":
                disp_purpose = "Network Telemetry Hardware"
            elif domain == "ecommerce":
                disp_purpose = "POS & Scanner Hardware"
            elif domain == "traffic":
                disp_purpose = "Roadway Traffic Sensor"
            else:
                disp_purpose = "Sensor & Hardware Monitoring"
        else:
            disp_purpose = purpose.replace('_', ' ').title()

        gemini_prompt = (
            f"Create a high-quality {v_type.replace('_', ' ')} for an academic presentation slide titled \"{slide_heading}\".\n\n"
            f"Project Context: {project_title}.\n"
            f"Slide Purpose: {disp_purpose}.\n"
            f"{matter_context}\n\n"
            f"Required Subjects: {', '.join(subjects)}.\n"
            f"Key Objects in Scene: {', '.join(objects)}.\n"
            f"Environment: {env}.\n"
            f"Visual Style: {v_style}.\n"
            f"Composition: Academic presentation ready, uncluttered, clear focal subject, professional natural lighting.\n\n"
            f"Negative Constraints (CRITICAL): Do NOT include any {', '.join(cls.UNIVERSAL_NEGATIVE_CONSTRAINTS)}."
        )

        return SlideVisualRequirement(
            project_title=project_title,
            slide_index=slide_index,
            slide_heading=slide_heading,
            slide_matter=slide_matter,
            slide_purpose=purpose,
            key_concepts=concepts,
            visual_type=v_type,
            required_subjects=subjects,
            required_objects=objects,
            environment=env,
            visual_style=v_style,
            negative_constraints=cls.UNIVERSAL_NEGATIVE_CONSTRAINTS,
            gemini_prompt=gemini_prompt,
            relevance_status="COMPILED",
            detected_domain=domain,
            domain_label=domain_label,
            domain_confidence=confidence,
        )

    @classmethod
    def validate_image_relevance(
        cls,
        req: SlideVisualRequirement,
        generated_prompt_or_text: str = "",
    ) -> Tuple[bool, str]:
        """
        Runs automated relevance check on the visual requirement (Step 7).
        Rejects generic AI brains, electrical safety leftovers, and stock clichés.
        """
        prompt_positive = req.gemini_prompt.split("Negative Constraints")[0] if "Negative Constraints" in req.gemini_prompt else req.gemini_prompt
        corpus = f"{prompt_positive} {req.slide_heading} {req.slide_matter} {' '.join(req.required_subjects)} {' '.join(req.required_objects)} {generated_prompt_or_text}".lower()

        FORBIDDEN_PATTERNS = [
            ("electric safety", "Contains leftover electrical safety references"),
            ("socket", "Contains electrical socket references"),
            ("electric hazard", "Contains electrical hazard references"),
            ("glowing brain", "Contains generic glowing brain cliché"),
            ("humanoid robot", "Contains generic robot cliché"),
            ("motherboard", "Contains random computer motherboard reference"),
            ("generic tech", "Contains vague non-specific technology prompt"),
        ]

        for pattern, reason in FORBIDDEN_PATTERNS:
            if pattern in corpus:
                return False, f"FAILED: {reason}"

        # Safeguard: Rejection of inappropriate agriculture imagery in non-agricultural projects
        if getattr(req, "detected_domain", "general") != "irrigation":
            AGRICULTURE_FORBIDDEN = [
                ("agricultural farm", "Inappropriate agricultural farm visual for non-agricultural project"),
                ("irrigation tubing", "Inappropriate irrigation hardware visual for non-agricultural project"),
                ("soil moisture sensor", "Inappropriate soil moisture visual for non-agricultural project"),
                ("drip irrigation", "Inappropriate drip irrigation visual for non-agricultural project"),
                ("crop field", "Inappropriate crop field visual for non-agricultural project"),
                ("lush commercial agricultural", "Inappropriate agriculture fallback visual"),
            ]
            for pattern, reason in AGRICULTURE_FORBIDDEN:
                if pattern in prompt_positive.lower() or pattern in generated_prompt_or_text.lower():
                    return False, f"FAILED: {reason}"

        if not req.required_subjects or not req.required_objects:
            return False, "FAILED: Missing concrete required physical subjects/objects"

        if len(req.slide_heading.strip()) < 3:
            return False, "FAILED: Empty or invalid slide heading"

        return True, "PASS"

    # Per-report tracking of generated image SHA-256 hashes to guarantee no duplicates across slides
    _REPORT_SLIDE_HASHES: Dict[str, Dict[int, str]] = {}

    @classmethod
    def clear_cache(cls, report_id: Optional[str] = None) -> None:
        """Clears all in-memory image trackers to prevent cross-report or cross-run reuse."""
        if report_id and report_id in cls._REPORT_SLIDE_HASHES:
            del cls._REPORT_SLIDE_HASHES[report_id]
        elif not report_id:
            cls._REPORT_SLIDE_HASHES.clear()

    @classmethod
    def generate_and_replace_slide_image(
        cls,
        project_title: str,
        slide_heading: str,
        slide_matter: str = "",
        subheading: str = "",
        aspect_ratio: float = 1.33,
        out_file_path: str = "",
        slide_index: int = 1,
        image_id: str = "",
        target_fmt: str = "PNG",
        sub_role: str = "",
        report_id: str = "diagnostic_run",
        project_description: str = "",
    ) -> SlideVisualRequirement:
        """
        Full Execution Pipeline for Slide-Specific Image Generation:
        1. Create report-isolated directory: generated_images/{report_id}/
        2. Force unique non-generic filename: {report_id}_slide_{slide_number}_{unique_id}.png
        3. Compile internal visual requirement (Slide Heading + Subheading + Matter > Project Name).
        4. Attempt real Gemini Image API synthesis with exact required debug log block.
        5. Verify SHA-256 uniqueness across slides (fail if duplicate).
        6. Disable ALL fallbacks (if Gemini fails -> DO NOT insert any image, NEVER use graphs).
        """
        import uuid
        import hashlib

        project_title = cls._normalize_str(project_title)
        slide_heading = cls._normalize_str(slide_heading)
        slide_matter = cls._normalize_str(slide_matter)
        subheading = cls._normalize_str(subheading)
        effective_image_id = image_id or f"slide_{slide_index}_visual"

        # Step 2: Fresh generation directory per report_id
        effective_report_id = str(report_id or "default_report").strip()
        report_gen_dir = os.path.abspath(os.path.join("generated_images", effective_report_id))
        os.makedirs(report_gen_dir, exist_ok=True)

        # Step 3: Force unique image filename
        unique_token = uuid.uuid4().hex[:8]
        if not out_file_path or "slide_" in os.path.basename(out_file_path):
            target_filename = f"{effective_report_id}_slide_{slide_index}_{unique_token}.png"
            out_file_path = os.path.join(report_gen_dir, target_filename)
        else:
            # Ensure output is inside report_gen_dir with unique pattern
            target_filename = f"{effective_report_id}_slide_{slide_index}_{unique_token}_{os.path.basename(out_file_path)}"
            if not target_filename.endswith(".png"):
                target_filename = os.path.splitext(target_filename)[0] + ".png"
            out_file_path = os.path.join(report_gen_dir, target_filename)

        # Step 1: Compile requirement
        req = cls.compile_visual_requirement(
            project_title=project_title,
            slide_heading=slide_heading,
            slide_matter=slide_matter,
            slide_index=slide_index,
            project_description=project_description,
        )

        # Requirement 9: Dedicated Debug Logging for Every Generated Image
        domain_debug_log = (
            f"\n[ARM VISUAL DOMAIN DEBUG]\n"
            f"Project Title: {req.project_title}\n"
            f"Detected Domain: {req.domain_label}\n"
            f"Domain Confidence: {req.domain_confidence:.2f}\n"
            f"Slide Number: {req.slide_index}\n"
            f"Slide Heading: {req.slide_heading}\n"
            f"Visual Purpose: {req.slide_purpose}\n"
            f"Final Image Prompt: {req.gemini_prompt}\n"
        )
        logger.info(domain_debug_log)
        try:
            print(domain_debug_log)
        except Exception:
            pass

        # Relevance Check
        is_relevant, rel_reason = cls.validate_image_relevance(req)
        req.relevance_status = rel_reason

        # Real Gemini Image API Execution (NO FALLBACKS, NO MATPLOTLIB, NO CHARTS)
        generated_successfully, img_sha = cls._execute_image_generation(
            req=req,
            out_file_path=out_file_path,
            aspect_ratio=aspect_ratio,
            target_fmt="PNG",
            report_id=effective_report_id,
            subheading=subheading,
        )

        if generated_successfully and img_sha:
            # Step 3 SHA-256 collision check across slides in current report
            if effective_report_id not in cls._REPORT_SLIDE_HASHES:
                cls._REPORT_SLIDE_HASHES[effective_report_id] = {}

            seen_hashes = cls._REPORT_SLIDE_HASHES[effective_report_id]
            for prior_slide_idx, prior_hash in seen_hashes.items():
                if prior_slide_idx != slide_index and prior_hash == img_sha:
                    err_msg = (
                        f"FATAL: DUPLICATE IMAGE SHA-256 DETECTED IN REPORT '{effective_report_id}'! "
                        f"Slide {slide_index} has identical hash {img_sha} as Slide {prior_slide_idx}."
                    )
                    logger.error(err_msg)
                    print(f"\n[ARM ERROR] {err_msg}\n")
                    raise RuntimeError(err_msg)

            seen_hashes[slide_index] = img_sha
            req.relevance_status = "SUCCESS_GENERATED"
            req.generated_image_path = out_file_path
            req.image_sha256 = img_sha
        else:
            req.relevance_status = "GEMINI_GENERATION_FAILED_NO_FALLBACK"
            req.generated_image_path = None
            req.image_sha256 = None

        return req

    @classmethod
    def _execute_image_generation(
        cls,
        req: SlideVisualRequirement,
        out_file_path: str,
        aspect_ratio: float,
        target_fmt: str,
        report_id: str = "report",
        subheading: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """
        Executes real Gemini image synthesis with strict logging (Step 4).
        If Gemini fails, DOES NOT insert any image and DOES NOT fallback to graphs.
        Returns: (success_bool, sha256_hash_str)
        """
        import hashlib
        api_key = settings.ai.gemini_api_key
        has_key = bool(api_key and not api_key.startswith("placeholder"))
        image_bytes: Optional[bytes] = None
        used_model: str = "None"
        used_endpoint: str = "None"
        response_status: str = "NO_API_KEY" if not has_key else "ATTEMPTING"

        # 1. Attempt xKiro (sensenova/sensenova-u1.5-lite) as PRIMARY provider
        from apps.api.services.xkiro_image_provider import XKiroImageProvider

        if XKiroImageProvider.is_configured():
            logger.info(f"[ARM IMAGE PIPELINE] Attempting xKiro (sensenova/sensenova-u1.5-lite) for Slide {req.slide_index}...")
            xkiro_res = XKiroImageProvider.generate_image(prompt=req.gemini_prompt)
            if xkiro_res and xkiro_res.image_bytes:
                image_bytes = xkiro_res.image_bytes
                used_model = xkiro_res.model_name
                used_endpoint = f"xKiro/{xkiro_res.provider_name}"
                response_status = xkiro_res.http_status
            else:
                logger.warning(f"[ARM IMAGE PIPELINE] xKiro did not return image bytes for Slide {req.slide_index}.")

        # 2. Attempt Cloudflare Workers AI if configured (fallback only)
        if not image_bytes:
            from apps.api.services.cloudflare_image_provider import CloudflareImageProvider

            if CloudflareImageProvider.is_configured():
                logger.info(f"[ARM IMAGE PIPELINE] Attempting Cloudflare Workers AI fallback for Slide {req.slide_index}...")
                cf_res = CloudflareImageProvider.generate_image(prompt=req.gemini_prompt)
                if cf_res and cf_res.image_bytes:
                    image_bytes = cf_res.image_bytes
                    used_model = cf_res.model_name
                    used_endpoint = f"Cloudflare/{cf_res.provider_name}"
                    response_status = cf_res.http_status
                else:
                    logger.warning(f"[ARM IMAGE PIPELINE] Cloudflare Workers AI did not return image bytes for Slide {req.slide_index}.")

        # 2. Attempt Hugging Face Inference Providers if Cloudflare did not return bytes
        if not image_bytes:
            from apps.api.services.hf_image_provider import HFImageProvider

            if HFImageProvider.is_configured():
                logger.info(f"[ARM IMAGE PIPELINE] Attempting Hugging Face Inference Provider for Slide {req.slide_index}...")
                hf_res = HFImageProvider.generate_image(prompt=req.gemini_prompt)
                if hf_res and hf_res.image_bytes:
                    image_bytes = hf_res.image_bytes
                    used_model = hf_res.model_name
                    used_endpoint = f"HuggingFace/{hf_res.provider_name}"
                    response_status = hf_res.http_status
                else:
                    logger.warning(f"[ARM IMAGE PIPELINE] Hugging Face did not return image bytes for Slide {req.slide_index}.")

        # 3. If neither Cloudflare nor Hugging Face yielded image bytes, check Gemini Image API
        if not image_bytes and has_key:
            # Candidate models to probe for valid image synthesis
            candidate_endpoints = [
                ("gemini-2.5-flash-image", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"),
                ("gemini-3.1-flash-image", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={api_key}"),
                ("gemini-3-pro-image", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent?key={api_key}"),
                ("gemini-3.1-flash-lite-image", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-image:generateContent?key={api_key}"),
                ("imagen-3.0-generate-002", f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"),
            ]

            payload = {
                "contents": [{"parts": [{"text": req.gemini_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]}
            }

            for model_name, endpoint_url in candidate_endpoints:
                used_model = model_name
                used_endpoint = endpoint_url.split("?key=")[0]
                try:
                    with httpx.Client(timeout=8.0) as client:
                        if "imagen" in model_name:
                            img_payload = {
                                "instances": [{"prompt": req.gemini_prompt}],
                                "parameters": {"sampleCount": 1}
                            }
                            res = client.post(endpoint_url, json=img_payload)
                        else:
                            res = client.post(endpoint_url, json=payload)

                        response_status = f"{res.status_code} {res.reason_phrase}"
                        if res.status_code == 200:
                            data = res.json()
                            if "predictions" in data:
                                preds = data.get("predictions", [])
                                if preds and "bytesBase64Encoded" in preds[0]:
                                    image_bytes = base64.b64decode(preds[0]["bytesBase64Encoded"])
                                    break
                            elif "candidates" in data:
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "inlineData" in p:
                                            b64_data = p["inlineData"].get("data")
                                            if b64_data:
                                                image_bytes = base64.b64decode(b64_data)
                                                break
                                    if image_bytes:
                                        break
                        else:
                            logger.info(f"[GEMINI PROBE] {model_name} returned {res.status_code}: {res.text[:100]}")
                except Exception as ex:
                    response_status = f"EXCEPTION: {ex}"
                    logger.debug(f"[GEMINI PROBE] {model_name} failed: {ex}")

        # If Gemini returned bytes, save as PNG and compute SHA256
        saved_path = "NONE"
        computed_sha = "NONE"

        if image_bytes:
            try:
                import io
                os.makedirs(os.path.dirname(os.path.abspath(out_file_path)), exist_ok=True)
                with PILImage.open(io.BytesIO(image_bytes)) as pil_img:
                    pil_img.save(out_file_path, format="PNG")

                with open(out_file_path, "rb") as f_img:
                    raw_b = f_img.read()
                    computed_sha = hashlib.sha256(raw_b).hexdigest()
                saved_path = out_file_path
            except Exception as ex:
                logger.error(f"Error saving Gemini image bytes: {ex}")
                image_bytes = None

        # STEP 4 MANDATORY LOG BLOCK
        log_block = (
            f"\n{'=' * 80}\n"
            f"REPORT ID: {report_id}\n"
            f"PROJECT TITLE: {req.project_title}\n"
            f"DETECTED DOMAIN: {req.domain_label}\n"
            f"DOMAIN CONFIDENCE: {req.domain_confidence:.2f}\n"
            f"SLIDE NUMBER: {req.slide_index}\n"
            f"SLIDE HEADING: {req.slide_heading}\n"
            f"SLIDE SUBHEADING: {subheading or 'None'}\n"
            f"SLIDE MATTER: {req.slide_matter or 'None'}\n"
            f"VISUAL PURPOSE: {req.slide_purpose}\n"
            f"IMAGE PROMPT: {req.gemini_prompt}\n"
            f"GEMINI MODEL: {used_model}\n"
            f"API ENDPOINT: {used_endpoint}\n"
            f"RESPONSE STATUS: {response_status}\n"
            f"IMAGE BYTES RECEIVED: {len(image_bytes) if image_bytes else 0}\n"
            f"SAVED IMAGE PATH: {saved_path}\n"
            f"IMAGE SHA256: {computed_sha}\n"
            f"{'=' * 80}\n"
        )
        try:
            print(log_block)
        except UnicodeEncodeError:
            import sys
            if hasattr(sys.stdout, "buffer") and sys.stdout.buffer:
                sys.stdout.buffer.write(log_block.encode("utf-8", errors="replace") + b"\n")
                sys.stdout.buffer.flush()
            else:
                print(log_block.encode("ascii", errors="backslashreplace").decode("ascii"))

        try:
            logger.info(log_block)
        except Exception:
            pass

        # STEP 1: ZERO FALLBACKS
        # If Gemini fails, DO NOT insert any image. Never replace with a graph or chart.
        if not image_bytes:
            logger.warning(
                f"[ARM IMAGE PIPELINE] Gemini Image Generation FAILED for Slide {req.slide_index} "
                f"('{req.slide_heading}'). Status: {response_status}. "
                f"ZERO FALLBACKS APPLIED: No image will be inserted. Graphs/charts strictly prohibited."
            )
            return False, None

        return True, computed_sha


# Singleton instance
gemini_visual_pipeline_service = GeminiVisualPipelineService()
