"""
ARM Stage: Central ARM Visual Engine
====================================
Central decision-maker and orchestrator for all visual assets in ARM reports:
1. Real-world AI photographs (via ImageGenerationManager: Cache -> RTX 3050 -> Cloudflare -> HF -> Together)
2. Mermaid architectural and sequence diagrams (via MermaidDiagramService: Cache -> Mermaid Renderer)
3. Quantitative performance charts (via ChartEngine: Real Data -> Matplotlib)
4. Existing template assets (retained logos, borders)
5. Controlled 'none' for textual slides (References, Citations)

Normalized Output Interface:
{
  "success": true,
  "visual_type": "image | mermaid | chart | existing_asset | none",
  "asset_path": "...",
  "asset_format": "png | svg | jpg",
  "width": 1600,
  "height": 900,
  "source": "cache | local_rtx | cloudflare | huggingface | together | mermaid | chart",
  "cached": false,
  "validated": true,
  "reason": "...",
  "error": null
}
"""

import os
import re
import logging
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

from apps.api.services.image_generation_manager import (
    image_generation_manager,
    ImageGenerationRequest,
)
from apps.api.services.mermaid_diagram_service import mermaid_diagram_service
from apps.api.services.chart_engine import chart_engine
from apps.api.services.gemini_visual_pipeline_service import gemini_visual_pipeline_service

logger = logging.getLogger(__name__)


class VisualEngineResult(BaseModel):
    success: bool
    visual_type: str  # "image" | "mermaid" | "chart" | "existing_asset" | "none"
    asset_path: Optional[str] = None
    asset_format: str = "png"
    width: int = 1600
    height: int = 900
    source: str = "none"  # "cache" | "local_rtx" | "cloudflare" | "huggingface" | "together" | "mermaid" | "chart" | "template"
    cached: bool = False
    validated: bool = True
    reason: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VisualEngine:
    """
    Central decision engine determining whether each slide needs an image, diagram, chart, or no visual.
    """

    @classmethod
    def decide_visual_category(
        cls,
        slide_heading: str,
        slide_matter: str,
        detected_domain: str,
        slide_number: int = 1,
    ) -> Tuple[str, str]:
        """
        Intelligently decides whether the slide communicates best via:
        - "none": References, citations, bibliography
        - "chart": Results/evaluation slides containing real numbers
        - "mermaid": Architecture, flow, database, sequence, class, state, timeline, mindmap
        - "image": Field photos, deployment photos, hardware/environment, cover
        Returns: (visual_category, reason)
        """
        h_clean = slide_heading.strip()
        h_lower = h_clean.lower()
        m_lower = slide_matter.lower()

        # 1. Slides that should NOT have any forced visual
        if any(w in h_lower for w in ("reference", "citation", "bibliography", "acknowledgement", "thank you")):
            return "none", "Academic references/closing slides require zero visual decoration."

        # 2. Database Design -> ER Diagram
        if any(w in h_lower for w in ("database", "er diagram", "entity relationship", "data schema", "relational model")):
            return "mermaid", "Database schema and relations best modeled via Mermaid ER Diagram."

        # 3. Sequence / Interaction -> Sequence Diagram
        if any(w in h_lower for w in ("sequence", "call flow", "interaction flow", "message exchange")):
            return "mermaid", "Inter-module message sequence best visualized via Mermaid Sequence Diagram."

        # 4. Class / Object Model -> Class Diagram
        if any(w in h_lower for w in ("class diagram", "object model", "class structure", "oop design")):
            return "mermaid", "Object-oriented class hierarchy best visualized via Mermaid Class Diagram."

        # 5. System States -> State Diagram
        if any(w in h_lower for w in ("system states", "state transition", "state machine", "lifecycle states")):
            return "mermaid", "Finite state transitions best modeled via Mermaid State Diagram."

        # 6. Architecture / Flowchart / Working Process
        if any(w in h_lower for w in ("architecture", "workflow", "working process", "methodology", "data flow", "block diagram")):
            return "mermaid", "Technical system architecture and pipeline flow best communicated via Mermaid Flowchart."

        # 7. Timeline / Roadmap
        if any(w in h_lower for w in ("timeline", "project schedule", "implementation phases", "milestones", "future roadmap")):
            return "mermaid", "Phase-wise project scheduling best visualized via Mermaid Timeline."

        # 8. Concept Overview / Taxonomy -> Mind Map
        if any(w in h_lower for w in ("concept overview", "taxonomy", "concept map", "mind map", "feature decomposition")):
            return "mermaid", "Conceptual domain hierarchy best structured via Mermaid Mind Map."

        # 9. Results / Performance / Benchmarks
        if any(w in h_lower for w in ("result", "performance", "benchmark", "evaluation", "metrics")):
            # Check if real numeric data exists
            has_numeric = bool(chart_engine.extract_numeric_evidence(slide_matter))
            if has_numeric:
                return "chart", "Empirical performance results with quantitative data rendered as Data Chart."
            else:
                return "mermaid", "Results without explicit numbers rendered as architectural evaluation workflow."

        # 10. Field Deployment Photos / Implementation Photos / Hardware Photos
        if any(w in h_lower for w in ("photo", "field", "deployment", "camera", "sensor probe", "device", "hardware setup", "prototype")):
            return "image", "Physical hardware setup and field deployment requires realistic photographic evidence."

        # 11. Cover / Title / Introduction
        if slide_number == 1 or any(w in h_lower for w in ("introduction", "overview", "problem statement")):
            return "image", "Introductory context benefits from high-fidelity domain photograph."

        # Default fallback: If technical topic with steps -> mermaid, else image
        if any(w in m_lower for w in ("step", "process", "pipeline", "transfers", "connects")):
            return "mermaid", "Stepped procedural content best conveyed as architectural diagram."

        return "image", "Domain-specific illustrative photograph."

    @classmethod
    def generate_visual(
        cls,
        project_title: str,
        project_description: str = "",
        detected_domain: str = "general",
        domain_confidence: float = 1.0,
        slide_number: int = 1,
        slide_heading: str = "System Overview",
        slide_matter: str = "",
        visual_requirement: Optional[Dict[str, Any]] = None,
        existing_visual_information: Optional[Dict[str, Any]] = None,
        template_context: Optional[Dict[str, Any]] = None,
        report_id: str = "default_run",
        target_width: int = 1600,
        target_height: int = 900,
        output_path: Optional[str] = None,
    ) -> VisualEngineResult:
        """
        Executes complete intelligent visual generation flow:
        1. Decide visual type (image vs mermaid vs chart vs none)
        2. Dispatch to appropriate engine
        3. Validate visual asset
        4. Return normalized result
        """
        category, reason = cls.decide_visual_category(
            slide_heading=slide_heading,
            slide_matter=slide_matter,
            detected_domain=detected_domain,
            slide_number=slide_number,
        )

        logger.info(
            f"[ARM VISUAL ENGINE] Slide {slide_number} ('{slide_heading}') -> Decision: {category.upper()} ({reason})"
        )

        # CASE A: NONE
        if category == "none":
            return VisualEngineResult(
                success=True,
                visual_type="none",
                asset_path=None,
                source="none",
                reason=reason,
            )

        # Prepare isolated output path if not specified
        final_out_path = output_path
        if not final_out_path:
            out_dir = os.path.abspath(os.path.join("generated_images", report_id))
            os.makedirs(out_dir, exist_ok=True)
            safe_h = re.sub(r"[^\w\-]", "_", slide_heading).lower()
            final_out_path = os.path.join(out_dir, f"visual_{slide_number}_{safe_h}.png")

        # CASE B: CHART
        if category == "chart":
            chart_res = chart_engine.generate_chart(
                project_title=project_title,
                slide_heading=slide_heading,
                slide_matter=slide_matter,
                output_path=final_out_path,
                width=target_width,
                height=target_height,
            )
            if chart_res and chart_res.success and chart_res.asset_path:
                return VisualEngineResult(
                    success=True,
                    visual_type="chart",
                    asset_path=chart_res.asset_path,
                    asset_format="png",
                    width=chart_res.width,
                    height=chart_res.height,
                    source=chart_res.source,
                    cached=chart_res.cached,
                    validated=True,
                    reason=reason,
                    metadata=chart_res.extracted_data,
                )
            # If chart could not be generated (no real data), gracefully fall back to diagram
            category = "mermaid"
            reason = "No verifiable numeric data present; fell back to architectural diagram."

        # CASE C: MERMAID DIAGRAM
        if category == "mermaid":
            diag_res = mermaid_diagram_service.generate_diagram(
                project_title=project_title,
                project_description=project_description,
                domain=detected_domain,
                slide_heading=slide_heading,
                slide_matter=slide_matter,
                output_path=final_out_path,
                width=target_width,
                height=target_height,
            )
            if diag_res and diag_res.success and diag_res.asset_path:
                return VisualEngineResult(
                    success=True,
                    visual_type="mermaid",
                    asset_path=diag_res.asset_path,
                    asset_format="png",
                    width=diag_res.width,
                    height=diag_res.height,
                    source=diag_res.source,
                    cached=diag_res.cached,
                    validated=True,
                    reason=reason,
                    metadata={"diagram_type": diag_res.diagram_type},
                )
            # If diagram fails, fallback to image
            category = "image"
            reason = "Diagram synthesis fell back to photographic visual."

        # CASE D: REAL-WORLD AI PHOTOGRAPH
        # Compile existing domain-aware prompt using gemini_visual_pipeline_service
        req = gemini_visual_pipeline_service.compile_visual_requirement(
            project_title=project_title,
            slide_heading=slide_heading,
            slide_matter=slide_matter,
            slide_index=slide_number,
            project_description=project_description,
        )

        img_req = ImageGenerationRequest(
            project_title=project_title,
            project_description=project_description,
            detected_domain=req.detected_domain,
            domain_confidence=req.domain_confidence,
            slide_number=slide_number,
            slide_heading=slide_heading,
            slide_matter=slide_matter,
            visual_purpose=req.slide_purpose,
            final_image_prompt=req.gemini_prompt,
            width=target_width,
            height=target_height,
            output_format="PNG",
            output_path=final_out_path,
            report_id=report_id,
        )

        img_res = image_generation_manager.generate_image(img_req)

        if img_res.success and img_res.image_path:
            return VisualEngineResult(
                success=True,
                visual_type="image",
                asset_path=img_res.image_path,
                asset_format="png",
                width=img_res.width,
                height=img_res.height,
                source=img_res.source,
                cached=img_res.cached,
                validated=True,
                reason=reason,
                metadata=img_res.metadata,
            )

        # Controlled Failure
        return VisualEngineResult(
            success=False,
            visual_type="image",
            asset_path=None,
            source="none",
            reason=reason,
            error=img_res.error or "Visual synthesis unavailable across all providers",
        )


# Singleton instance
visual_engine = VisualEngine()
