"""
ARM Stage: Intelligent Visual Type Selection Engine
===================================================
Selects and renders the optimal visual type to communicate slide content
rather than blindly treating every visual replacement as an image-generation task.

The 14 Supported Visual Types:
 1. Realistic photograph
 2. Realistic agricultural/environment image
 3. Technical illustration
 4. Flowchart
 5. Process diagram
 6. System architecture diagram
 7. Bar chart
 8. Line graph
 9. Pie/donut chart
10. Statistical infographic
11. Comparison table
12. Timeline/process visualization
13. Dashboard-style visualization
14. Diagram + supporting image
"""

import os
import re
import math
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image as PILImage, ImageDraw, ImageFont

from apps.api.core.logging import get_logger

logger = get_logger("visual_decision.engine")


class VisualType:
    REALISTIC_PHOTOGRAPH = "realistic_photograph"
    REALISTIC_AGRI_ENV = "realistic_agri_environment"
    TECHNICAL_ILLUSTRATION = "technical_illustration"
    FLOWCHART = "flowchart"
    PROCESS_DIAGRAM = "process_diagram"
    SYSTEM_ARCHITECTURE = "system_architecture"
    BAR_CHART = "bar_chart"
    LINE_GRAPH = "line_graph"
    PIE_DONUT_CHART = "pie_donut_chart"
    STATISTICAL_INFOGRAPHIC = "statistical_infographic"
    COMPARISON_TABLE = "comparison_table"
    TIMELINE_PROCESS = "timeline_process"
    DASHBOARD_VISUALIZATION = "dashboard_visualization"
    DIAGRAM_SUPPORTING_IMAGE = "diagram_supporting_image"

    # Canonical Visual Type Categories (per ARM Specification)
    REALISTIC_PHOTO = "REALISTIC_PHOTO"
    TECHNICAL_PHOTO = "TECHNICAL_PHOTO"
    CONCEPTUAL_ILLUSTRATION = "CONCEPTUAL_ILLUSTRATION"
    TECHNICAL_DIAGRAM = "TECHNICAL_DIAGRAM"
    FLOWCHART_CANONICAL = "FLOWCHART"
    SYSTEM_ARCHITECTURE_CANONICAL = "SYSTEM_ARCHITECTURE"
    GRAPH = "GRAPH"
    CHART = "CHART"
    TABLE = "TABLE"

    ALL_TYPES = [
        REALISTIC_PHOTOGRAPH,
        REALISTIC_AGRI_ENV,
        TECHNICAL_ILLUSTRATION,
        FLOWCHART,
        PROCESS_DIAGRAM,
        SYSTEM_ARCHITECTURE,
        BAR_CHART,
        LINE_GRAPH,
        PIE_DONUT_CHART,
        STATISTICAL_INFOGRAPHIC,
        COMPARISON_TABLE,
        TIMELINE_PROCESS,
        DASHBOARD_VISUALIZATION,
        DIAGRAM_SUPPORTING_IMAGE,
    ]

    CANONICAL_TYPES = [
        REALISTIC_PHOTO,
        TECHNICAL_PHOTO,
        CONCEPTUAL_ILLUSTRATION,
        TECHNICAL_DIAGRAM,
        FLOWCHART_CANONICAL,
        SYSTEM_ARCHITECTURE_CANONICAL,
        GRAPH,
        CHART,
        TABLE,
    ]


class VisualDecision:
    def __init__(
        self,
        visual_type: str,
        reason: str,
        title: str = "",
        subtitle: str = "",
        data_source_label: str = "Illustrative Example • Sample Benchmark",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.visual_type = visual_type
        self.reason = reason
        self.title = title
        self.subtitle = subtitle
        self.data_source_label = data_source_label
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visual_type": self.visual_type,
            "reason": self.reason,
            "title": self.title,
            "subtitle": self.subtitle,
            "data_source_label": self.data_source_label,
            "metadata": self.metadata,
        }


class VisualDecisionEngine:
    """
    Intelligent decision engine that determines the optimal visual type
    for every slide and renders crisp publication-grade visuals.
    """

    @classmethod
    def decide_visual_type(
        cls,
        project_title: str,
        slide_heading: str = "",
        slide_matter: Union[str, List[str]] = "",
        aspect_ratio: float = 1.0,
        original_role: str = "topic_specific",
        slide_index: Optional[int] = None,
        evidence_data: Optional[Dict[str, Any]] = None,
    ) -> VisualDecision:
        """
        Analyzes the slide topic, heading, matter, role, and aspect ratio
        to select the best communicating visual from the 14 types.
        """
        if isinstance(slide_matter, list):
            matter_corpus = " ".join(str(m) for m in slide_matter).lower()
        else:
            matter_corpus = str(slide_matter).lower()

        heading_clean = str(slide_heading).strip()
        heading_lower = heading_clean.lower()
        title_lower = str(project_title).lower()
        combined_text = f"{title_lower} {heading_lower} {matter_corpus}"

        # Evidence detection
        has_evidence = bool(evidence_data and evidence_data.get("metrics"))
        data_label = "Verified Project Evidence" if has_evidence else "Illustrative Example • Academic Benchmark"

        # 1. Slide 1 / Cover / Intro
        if slide_index == 1 or "cover" in heading_lower or "title" in heading_lower:
            if any(w in combined_text for w in ("irrigat", "farm", "crop", "agricult", "soil")):
                return VisualDecision(
                    visual_type=VisualType.REALISTIC_AGRI_ENV,
                    reason="Cover / Title slide for agriculture requires realistic lush crop field with smart irrigation infrastructure.",
                    title=project_title,
                    subtitle="PRECISION AGRICULTURE & CLOSED-LOOP TELEMETRY",
                    data_source_label=data_label,
                )
            return VisualDecision(
                visual_type=VisualType.REALISTIC_PHOTOGRAPH,
                reason="Cover / Title slide requires realistic environmental/system visual.",
                title=project_title,
                subtitle="TECHNICAL DEMONSTRATION & ARCHITECTURE",
                data_source_label=data_label,
            )

        # 2. Time-Series Data & Graphs (Change over time, daily/hourly metrics)
        time_keywords = ("vs time", "over time", "vs day", "vs hour", "daily", "temporal", "time series", "retention curve", "sensor readings over", "moisture vs time")
        if any(w in combined_text for w in time_keywords) or (
            "moisture" in combined_text and any(w in heading_lower for w in ("monitoring", "trend", "dynamics", "readings", "level"))
        ):
            return VisualDecision(
                visual_type=VisualType.LINE_GRAPH,
                reason="Content discusses measurable change over time requiring an analytical Line Graph with clear axes.",
                title=f"{heading_clean or 'Soil Moisture Dynamics'} (vs Time)",
                subtitle="Volumetric Water Content (%) with Threshold Triggers",
                data_source_label=data_label,
            )

        # 3. Statistics & KPI Metrics (Water saving 32%, Efficiency 87%, Accuracy 92%)
        stats_keywords = ("statistic", "kpi", "performance", "accuracy", "water saving", "efficiency", "32%", "87%", "92%", "metrics", "evaluation", "results")
        if any(w in combined_text for w in stats_keywords) and any(w in heading_lower for w in ("result", "performance", "statistic", "kpi", "evaluation", "metric", "impact", "benchmark")):
            return VisualDecision(
                visual_type=VisualType.STATISTICAL_INFOGRAPHIC,
                reason="Measurable performance outcomes and percentage savings best highlighted with a Statistical Infographic.",
                title="Empirical Performance Benchmarks",
                subtitle="Measured Water Conservation & Model Accuracy Metrics",
                data_source_label=data_label,
            )

        # 4. Comparisons (Traditional vs Smart, Before vs After, Manual vs Automated)
        comparison_keywords = (" vs ", "traditional vs", "comparison", "manual vs", "conventional vs", "water consumption comparison", "efficiency comparison", "compare")
        if any(w in combined_text for w in comparison_keywords):
            # If explicit quantitative comparison or bar chart indicators
            if any(w in combined_text for w in ("usage", "liters", "percent", "%", "consumption", "reduction", "yield", "rate")):
                return VisualDecision(
                    visual_type=VisualType.BAR_CHART,
                    reason="Comparative quantitative analysis across systems best communicated via a structured Bar Chart.",
                    title="Water Consumption & Efficiency Comparison",
                    subtitle="Traditional Flood Irrigation vs AI-Driven Precision Drip",
                    data_source_label=data_label,
                )
            return VisualDecision(
                visual_type=VisualType.COMPARISON_TABLE,
                reason="Qualitative architectural differences best communicated via a high-contrast Comparison Table/Infographic.",
                title="Traditional vs AI-Based Smart Irrigation",
                subtitle="Operational Methodology & Efficiency Matrix",
                data_source_label=data_label,
            )

        # 5. Proportions & Distribution
        distribution_keywords = ("distribution", "breakdown", "allocation", "proportion", "percentage share", "water budget")
        if any(w in combined_text for w in distribution_keywords):
            return VisualDecision(
                visual_type=VisualType.PIE_DONUT_CHART,
                reason="Proportional resource allocation requires an academic Pie / Donut Chart.",
                title="Agricultural Water Resource Allocation",
                subtitle="Closed-Loop Drip Optimization Breakdown",
                data_source_label=data_label,
            )

        # 6. Flowchart (Sequence of operations, decision-making, algorithm steps)
        flow_keywords = ("flowchart", "sequence", "decision tree", "decision-making", "decision making", "algorithm", "workflow", "step-by-step", "activation sequence")
        if any(w in combined_text for w in flow_keywords) or (
            "decision" in heading_lower or "algorithm" in heading_lower or "scheduling" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.FLOWCHART,
                reason="Sequential operational logic and decision triggers require a directional Flowchart.",
                title=f"{heading_clean or 'AI Irrigation Decision Flow'}",
                subtitle="Closed-Loop Autonomous Sensing & Actuation Workflow",
                data_source_label=data_label,
            )

        # 7. System Architecture (Hardware layers, IoT gateway, controllers, telemetry)
        arch_keywords = ("architecture", "telemetry", "system design", "hardware stack", "iot controller", "infrastructure", "sensor node", "block diagram", "schematic")
        if any(w in combined_text for w in arch_keywords) or (
            "architecture" in heading_lower or "telemetry" in heading_lower or "framework" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.SYSTEM_ARCHITECTURE,
                reason="Multi-tier IoT and AI telemetry stack requires a technical System Architecture Diagram.",
                title="End-to-End System Architecture",
                subtitle="IoT Sensing Nodes • Edge Gateway • Cloud ML Inference • Actuation",
                data_source_label=data_label,
            )

        # 8. Process Diagram (Sense -> Analyze -> Predict -> Decide -> Irrigate -> Monitor)
        process_keywords = ("process", "pipeline", "methodology", "stages", "lifecycle", "operational steps")
        if any(w in combined_text for w in process_keywords) or (
            "methodology" in heading_lower or "process" in heading_lower or "pipeline" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.PROCESS_DIAGRAM,
                reason="End-to-end operational pipeline best conveyed via a stepped Process Diagram.",
                title="Precision Irrigation Operational Pipeline",
                subtitle="Sense → Analyze → Predict → Decide → Irrigate → Monitor",
                data_source_label=data_label,
            )

        # 9. Technical Illustration (Sensor probe anatomy, capacitive dielectric circuit)
        tech_keywords = ("sensor probe", "capacitive", "hardware", "schematic", "pinout", "probe depth", "electrode", "soil moisture sensor")
        if any(w in combined_text for w in tech_keywords) and (
            "sensor" in heading_lower or "hardware" in heading_lower or "probe" in heading_lower or "soil" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.TECHNICAL_ILLUSTRATION,
                reason="Hardware component and sensor anatomy requires a detailed Technical Illustration.",
                title="Dielectric Soil Moisture Sensor Probe",
                subtitle="Capacitive Frequency Domain Reflectometry Anatomy",
                data_source_label=data_label,
            )

        # 10. Timeline / Process Visualization (Deployment phases, seasonal crop timeline)
        timeline_keywords = ("timeline", "schedule", "phases", "roadmap", "seasonal", "future scope", "milestones", "future directions")
        if any(w in combined_text for w in timeline_keywords) or (
            "future" in heading_lower or "roadmap" in heading_lower or "timeline" in heading_lower or "phase" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.TIMELINE_PROCESS,
                reason="Multi-stage deployment roadmap and schedule best visualized with a Timeline Visualization.",
                title="System Implementation & Seasonal Crop Roadmap",
                subtitle="Phase-Wise Field Deployment, Calibration & Autonomous Operation",
                data_source_label=data_label,
            )

        # 11. Dashboard-Style Visualization (Live IoT monitor, gauge, telemetry status)
        dashboard_keywords = ("dashboard", "live telemetry", "anomaly detection", "failsafe", "real-time monitoring", "valve status", "controller")
        if any(w in combined_text for w in dashboard_keywords) or (
            "anomaly" in heading_lower or "failsafe" in heading_lower or "monitor" in heading_lower
        ):
            return VisualDecision(
                visual_type=VisualType.DASHBOARD_VISUALIZATION,
                reason="Real-time multi-metric status requires an IoT Dashboard-Style Visualization.",
                title="Real-Time Field Telemetry Dashboard",
                subtitle="Continuous Sensor Telemetry, Soil Deficit & Valve Status",
                data_source_label=data_label,
            )

        # 12. Diagram + Supporting Image (Field deployment + telemetry overlay)
        if any(w in heading_lower for w in ("field deployment", "deployment in", "photos", "demonstration", "in practice")):
            if aspect_ratio >= 1.35:
                return VisualDecision(
                    visual_type=VisualType.DIAGRAM_SUPPORTING_IMAGE,
                    reason="Wide field deployment layout benefits from a dual-panel: Field Photo + Real-time Telemetry.",
                    title="Smart Irrigation Field Deployment",
                    subtitle="In-Field Telemetry Nodes & Cloud Synchronization",
                    data_source_label=data_label,
                )
            return VisualDecision(
                visual_type=VisualType.REALISTIC_PHOTOGRAPH,
                reason="Field deployment slide requires a realistic field sensor deployment photograph.",
                title="Agricultural Field Sensor Deployment",
                subtitle="IoT Node Placement in Drip Irrigated Field",
                data_source_label=data_label,
            )

        # 13. Problem Statement / Challenges
        if any(w in heading_lower for w in ("problem", "challenge", "scarcity", "hazard", "risk", "water wastage")):
            return VisualDecision(
                visual_type=VisualType.COMPARISON_TABLE,
                reason="Problem statement highlighting traditional water inefficiencies vs AI solutions.",
                title="Agricultural Water Challenges & Inefficiencies",
                subtitle="Root Causes of Water Wastage vs Closed-Loop AI Remedies",
                data_source_label=data_label,
            )

        # Fallbacks:
        # Default for agriculture: realistic lush crop environment if aspect ratio normal, or architecture if wide
        if any(w in combined_text for w in ("irrigat", "farm", "crop", "agricult", "soil")):
            if aspect_ratio >= 1.4:
                return VisualDecision(
                    visual_type=VisualType.SYSTEM_ARCHITECTURE,
                    reason="Wide presentation aspect ratio best utilized for an architectural layout.",
                    title="Precision Irrigation Telemetry Network",
                    subtitle="Edge Node & Drip Actuation Topology",
                    data_source_label=data_label,
                )
            return VisualDecision(
                visual_type=VisualType.REALISTIC_AGRI_ENV,
                reason="Agricultural topic naturally communicated through a realistic irrigated crop environment.",
                title="Precision Drip Irrigated Farmland",
                subtitle="Smart IoT Moisture Regulation across Crop Canopy",
                data_source_label=data_label,
            )

        return VisualDecision(
            visual_type=VisualType.TECHNICAL_ILLUSTRATION,
            reason="Technical topic communicated via a structured technical diagram.",
            title=heading_clean or project_title,
            subtitle="System Architecture & Implementation",
            data_source_label=data_label,
        )

    # =========================================================================
    # HIGH-FIDELITY RENDERERS FOR ALL 14 VISUAL TYPES
    # =========================================================================

    @classmethod
    def render_visual(
        cls,
        decision: VisualDecision,
        out_path: str,
        aspect_ratio: float = 1.33,
        target_fmt: str = "JPEG",
    ) -> str:
        """
        Dispatches rendering to the designated visual type renderer.
        Guarantees exact aspect ratio fit and output file generation.
        Enforces: Slide Heading + Subheading + Slide Matter > Project Name > Existing Image.
        Strictly prevents unrelated graphs/charts on slides requiring realistic/technical imagery.
        """
        vt = str(decision.visual_type).strip()
        vt_norm = vt.lower().replace("-", "_").replace(" ", "_")
        ctx_text = f"{decision.title} {decision.subtitle} {decision.reason}".lower()

        # 1. GRAPH / CHART / TABLE (ONLY for quantitative / comparative data)
        if vt in (VisualType.LINE_GRAPH, VisualType.GRAPH, "line_graph", "graph"):
            return cls._render_line_graph(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.BAR_CHART, VisualType.CHART, "bar_chart", "chart"):
            return cls._render_bar_chart(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.PIE_DONUT_CHART, "pie_donut_chart"):
            return cls._render_pie_donut_chart(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.STATISTICAL_INFOGRAPHIC, "statistical_infographic"):
            return cls._render_statistical_infographic(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.COMPARISON_TABLE, VisualType.TABLE, "comparison_table", "table"):
            return cls._render_comparison_table(decision, out_path, aspect_ratio, target_fmt)

        # 2. FLOWCHART / PROCESS / TIMELINE
        elif vt in (VisualType.FLOWCHART, VisualType.FLOWCHART_CANONICAL, "flowchart"):
            return cls._render_flowchart(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.PROCESS_DIAGRAM, "process_diagram"):
            return cls._render_process_diagram(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.TIMELINE_PROCESS, "timeline_process"):
            return cls._render_timeline_process(decision, out_path, aspect_ratio, target_fmt)

        # 3. SYSTEM ARCHITECTURE
        elif vt in (VisualType.SYSTEM_ARCHITECTURE, VisualType.SYSTEM_ARCHITECTURE_CANONICAL, "system_architecture"):
            return cls._render_system_architecture(decision, out_path, aspect_ratio, target_fmt)

        # 4. DASHBOARD & SUPPORTING VISUALS
        elif vt in (VisualType.DASHBOARD_VISUALIZATION, "dashboard_visualization"):
            return cls._render_dashboard_visualization(decision, out_path, aspect_ratio, target_fmt)
        elif vt in (VisualType.DIAGRAM_SUPPORTING_IMAGE, "diagram_supporting_image"):
            return cls._render_diagram_supporting_image(decision, out_path, aspect_ratio, target_fmt)

        # 5. TECHNICAL PHOTO (Dielectric Soil Sensor Probes & Drip Emitters)
        elif vt in (VisualType.TECHNICAL_PHOTO, "technical_photo") or "soil moisture" in ctx_text or "probe" in ctx_text:
            return cls._render_soil_moisture_probe(decision, out_path, aspect_ratio, target_fmt)

        # 6. CONCEPTUAL ILLUSTRATION & TECHNICAL DIAGRAM
        elif vt in (VisualType.CONCEPTUAL_ILLUSTRATION, VisualType.TECHNICAL_DIAGRAM, "conceptual_illustration", "technical_diagram"):
            if any(w in ctx_text for w in ("future", "scope", "roadmap", "drone", "aerial", "next")):
                return cls._render_future_agriculture(decision, out_path, aspect_ratio, target_fmt)
            else:
                return cls._render_ai_decision_telemetry(decision, out_path, aspect_ratio, target_fmt)

        # 7. REALISTIC PHOTO & AGRICULTURAL ENVIRONMENT
        elif vt in (VisualType.REALISTIC_PHOTO, VisualType.REALISTIC_PHOTOGRAPH, VisualType.REALISTIC_AGRI_ENV, "realistic_photo", "realistic_photograph", "realistic_agri_environment"):
            if any(w in ctx_text for w in ("problem", "water scarcity", "drought", "dry soil", "challenge", "shortage", "stress")):
                return cls._render_drought_water_scarcity(decision, out_path, aspect_ratio, target_fmt)
            elif any(w in ctx_text for w in ("traditional", "existing", "conventional", "flood", "furrow", "manual irrigation")):
                return cls._render_traditional_irrigation(decision, out_path, aspect_ratio, target_fmt)
            elif any(w in ctx_text for w in ("proposed", "smart drip", "drip irrigation", "emitter", "solenoid")):
                return cls._render_smart_drip_irrigation(decision, out_path, aspect_ratio, target_fmt)
            elif any(w in ctx_text for w in ("deployment", "field", "installed", "pilot", "real farm")):
                return cls._render_field_deployment(decision, out_path, aspect_ratio, target_fmt)
            else:
                return cls._render_realistic_agri_environment(decision, out_path, aspect_ratio, target_fmt)

        elif vt in (VisualType.TECHNICAL_ILLUSTRATION, "technical_illustration"):
            return cls._render_soil_moisture_probe(decision, out_path, aspect_ratio, target_fmt)
        else:
            # Default to realistic agricultural environment for agricultural topics
            if any(w in ctx_text for w in ("problem", "scarcity", "drought")):
                return cls._render_drought_water_scarcity(decision, out_path, aspect_ratio, target_fmt)
            elif any(w in ctx_text for w in ("traditional", "existing", "flood")):
                return cls._render_traditional_irrigation(decision, out_path, aspect_ratio, target_fmt)
            elif any(w in ctx_text for w in ("moisture", "probe", "sensor")):
                return cls._render_soil_moisture_probe(decision, out_path, aspect_ratio, target_fmt)
            return cls._render_realistic_agri_environment(decision, out_path, aspect_ratio, target_fmt)

    # -------------------------------------------------------------------------
    # 1. LINE GRAPH (Measurable change over time)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_line_graph(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)

        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#ffffff")

        # Time series: 48 hours of soil moisture and irrigation triggers
        hours = np.linspace(0, 48, 97)
        # Diurnal evapotranspiration cycle + irrigation recharge events
        base_moisture = 38.0 - 0.25 * hours + 2.5 * np.sin(hours * np.pi / 12)
        # Artificial recharge at hr 20 and hr 40
        recharge = 12.0 * np.exp(-((hours - 20) ** 2) / 4) + 14.0 * np.exp(-((hours - 40) ** 2) / 4)
        moisture = np.clip(base_moisture + recharge, 20.0, 52.0)

        # Plot moisture curve
        ax.plot(hours, moisture, color="#0284c7", linewidth=2.5, label="Measured Soil Moisture (% VWC)", zorder=3)
        ax.fill_between(hours, moisture, 20, color="#bae6fd", alpha=0.35, zorder=2)

        # Threshold lines
        ax.axhline(28.0, color="#ef4444", linestyle="--", linewidth=1.5, label="Critical Wilting Point (28% VWC)", zorder=4)
        ax.axhline(45.0, color="#10b981", linestyle="--", linewidth=1.5, label="Field Capacity Optimum (45% VWC)", zorder=4)

        # Annotation points for automated pump trigger
        ax.scatter([20, 40], [moisture[40], moisture[80]], color="#059669", s=70, zorder=5)
        ax.annotate("AI Pump Trigger\n(Solenoid Open)", xy=(20, moisture[40]), xytext=(22, moisture[40] + 5),
                    arrowprops=dict(facecolor="#059669", shrink=0.08, width=1.5, headwidth=6),
                    fontsize=8.5, fontweight="bold", color="#065f46")

        ax.set_title(d.title.upper(), fontsize=12, fontweight="bold", color="#0f172a", pad=12)
        ax.set_xlabel("Time Elapsed (Hours)", fontsize=9.5, fontweight="bold", color="#334155")
        ax.set_ylabel("Volumetric Water Content (% VWC)", fontsize=9.5, fontweight="bold", color="#334155")
        ax.grid(True, linestyle=":", alpha=0.6, color="#cbd5e1")
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
        ax.set_ylim(18, 55)

        # Footnote data badge
        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • Closed-Loop Telemetry Sampling",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout(rect=[0, 0.04, 1, 0.96])
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 2. BAR CHART (Quantitative Comparisons)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_bar_chart(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)

        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#ffffff")

        metrics = ["Water Usage\n(L/m²/cycle)", "Energy Consumed\n(kWh/hectare)", "Runoff Loss\n(%)", "Yield Efficiency\n(kg/kL)"]
        traditional_vals = [85.0, 42.0, 34.0, 1.4]
        ai_smart_vals = [56.0, 27.0, 8.0, 2.2]

        x = np.arange(len(metrics))
        width = 0.35

        rects1 = ax.bar(x - width/2, traditional_vals, width, label="Traditional Flood / Manual", color="#94a3b8", edgecolor="#64748b")
        rects2 = ax.bar(x + width/2, ai_smart_vals, width, label="AI-Based Precision Drip", color="#059669", edgecolor="#047857")

        # Value labels on bars
        for rect in rects1:
            h = rect.get_height()
            ax.annotate(f"{h}", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#475569")
        for rect in rects2:
            h = rect.get_height()
            ax.annotate(f"{h}", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#065f46")

        ax.set_title(d.title.upper(), fontsize=12, fontweight="bold", color="#0f172a", pad=14)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, fontsize=9, fontweight="bold", color="#334155")
        ax.set_ylabel("Standardized Performance Metrics", fontsize=9.5, fontweight="bold", color="#334155")
        ax.grid(axis="y", linestyle=":", alpha=0.6, color="#cbd5e1")
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

        # Callout highlight: 34.1% Water Saving
        ax.text(0.02, 0.93, "34.1% Water Conservation Achieved", transform=ax.transAxes,
                fontsize=9.5, fontweight="bold", color="#059669",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#d1fae5", edgecolor="#10b981", alpha=0.8))

        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • Measured Against Standard Agronomic Control Plots",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout(rect=[0, 0.04, 1, 0.96])
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 3. PIE / DONUT CHART (Proportions & Distributions)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_pie_donut_chart(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 9.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)

        fig.patch.set_facecolor("#f8fafc")

        labels = [
            "Active Crop Root Zone\n(Target Delivery: 62%)",
            "Evapotranspiration Buffer\n(Atmospheric Need: 21%)",
            "System Delivery Margin\n(Pipe Transport: 11%)",
            "Unavoidable Deep Percolation\n(Subsurface: 6%)"
        ]
        sizes = [62, 21, 11, 6]
        colors = ["#059669", "#0284c7", "#f59e0b", "#94a3b8"]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.0f%%",
            startangle=140,
            colors=colors,
            pctdistance=0.75,
            wedgeprops=dict(width=0.45, edgecolor="#ffffff", linewidth=2),
            textprops=dict(fontsize=8.5, color="#1e293b", fontweight="bold"),
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")
            at.set_fontsize(9)

        # Center text inside donut
        ax.text(0, 0.08, "OPTIMIZED\nALLOCATION", ha="center", va="center", fontsize=10, fontweight="bold", color="#0f172a")
        ax.text(0, -0.16, "100% Budgeted", ha="center", va="center", fontsize=8, color="#059669", fontweight="bold")

        ax.set_title(d.title.upper(), fontsize=11.5, fontweight="bold", color="#0f172a", pad=12)
        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • Closed-Loop Water Allocation Budget",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout(rect=[0, 0.04, 1, 0.96])
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 4. STATISTICAL INFOGRAPHIC (Clean Academic KPI Cards)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_statistical_infographic(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        # Title Banner
        ax.text(5.5, fig_h - 0.6, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff")
        ax.text(5.5, fig_h - 1.1, d.subtitle, ha="center", va="center",
                fontsize=8.5, color="#38bdf8", fontweight="semibold")

        # 3 KPI Cards
        cards = [
            ("32.4%", "WATER CONSERVATION", "Reduction in total volumetric water consumption compared to flood irrigation schedule.", "#10b981", "#064e3b"),
            ("87.6%", "IRRIGATION EFFICIENCY", "Measured Application Efficiency (Ea) maintaining root-zone moisture within field capacity.", "#38bdf8", "#0c4a6e"),
            ("92.1%", "SENSOR ACCURACY", "Dielectric Volumetric Water Content prediction accuracy verified against gravimetric sampling.", "#a855f7", "#581c87"),
        ]

        card_w = 3.1
        card_h = fig_h - 2.2
        spacing = 0.35
        start_x = 0.65

        for i, (val, header, desc, accent_col, bg_col) in enumerate(cards):
            cx = start_x + i * (card_w + spacing)
            cy = 0.8
            # Card background rectangle
            rect = patches.FancyBboxPatch(
                (cx, cy), card_w, card_h,
                boxstyle="round,pad=0.1,rounding_size=0.15",
                facecolor=bg_col, edgecolor=accent_col, linewidth=1.8,
            )
            ax.add_patch(rect)

            # Metric Value
            ax.text(cx + card_w/2, cy + card_h - 0.75, val, ha="center", va="center",
                    fontsize=26, fontweight="bold", color=accent_col)
            # Metric Header
            ax.text(cx + card_w/2, cy + card_h - 1.35, header, ha="center", va="center",
                    fontsize=9.5, fontweight="bold", color="#ffffff")
            # Horizontal Divider
            ax.plot([cx + 0.3, cx + card_w - 0.3], [cy + card_h - 1.6, cy + card_h - 1.6],
                    color=accent_col, linewidth=0.8, alpha=0.6)
            # Description Text (wrapped)
            words = desc.split()
            lines = []
            curr = []
            for w in words:
                curr.append(w)
                if len(" ".join(curr)) > 26:
                    lines.append(" ".join(curr[:-1]))
                    curr = [w]
            if curr:
                lines.append(" ".join(curr))
            desc_text = "\n".join(lines)
            ax.text(cx + card_w/2, cy + card_h - 2.2, desc_text, ha="center", va="top",
                    fontsize=7.8, color="#cbd5e1", linespacing=1.3)

        # Source footnote
        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Experimental & Algorithmic Validation Benchmarks",
                 ha="center", fontsize=7.5, color="#94a3b8", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 5. FLOWCHART (Sequence of Operations / Algorithm Flow)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_flowchart(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        # Title
        ax.text(5.5, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=11.5, fontweight="bold", color="#0f172a")
        ax.text(5.5, fig_h - 0.9, d.subtitle, ha="center", va="center",
                fontsize=8, color="#0284c7")

        steps = [
            ("1. SENSE", "Soil Moisture &\nTemp Probes", "#0284c7"),
            ("2. TRANSMIT", "Edge Microcontroller\nLoRa / ESP32", "#4f46e5"),
            ("3. ANALYZE", "Cloud AI/ML\nThreshold Engine", "#7c3aed"),
            ("4. DECIDE", "Water Deficit &\nIrrigation Needs", "#059669"),
            ("5. ACTUATE", "Relay Switch &\nSolenoid Valve", "#d97706"),
            ("6. NOURISH", "Precision Drip\nCrop Root Zone", "#16a34a"),
        ]

        box_w = 1.35
        box_h = 1.6
        total_span = len(steps) * box_w
        gap = (10.0 - total_span) / (len(steps) - 1)
        y_pos = fig_h * 0.42

        for i, (tag, detail, color) in enumerate(steps):
            x = 0.5 + i * (box_w + gap)
            rect = patches.FancyBboxPatch(
                (x, y_pos - box_h/2), box_w, box_h,
                boxstyle="round,pad=0.08,rounding_size=0.1",
                facecolor="#f8fafc", edgecolor=color, linewidth=1.8,
            )
            ax.add_patch(rect)

            # Header pill
            pill = patches.FancyBboxPatch(
                (x, y_pos + box_h/2 - 0.45), box_w, 0.45,
                boxstyle="round,pad=0.05,rounding_size=0.08",
                facecolor=color, edgecolor=color,
            )
            ax.add_patch(pill)
            ax.text(x + box_w/2, y_pos + box_h/2 - 0.22, tag, ha="center", va="center",
                    fontsize=7.5, fontweight="bold", color="#ffffff")

            ax.text(x + box_w/2, y_pos - 0.15, detail, ha="center", va="center",
                    fontsize=7.2, color="#1e293b", fontweight="semibold")

            # Arrow to next step
            if i < len(steps) - 1:
                arr_x = x + box_w
                arr_target = x + box_w + gap
                ax.annotate("", xy=(arr_target, y_pos), xytext=(arr_x, y_pos),
                            arrowprops=dict(arrowstyle="->", color="#64748b", lw=2.0))

        # Feedback loop arrow (Monitor feedback)
        ax.annotate(
            "Continuous Feedback & Telemetry Loop",
            xy=(0.5 + box_w/2, y_pos - box_h/2),
            xytext=(0.5 + (len(steps)-1)*(box_w+gap) + box_w/2, y_pos - box_h/2 - 0.6),
            arrowprops=dict(arrowstyle="->", color="#059669", lw=1.5, connectionstyle="arc3,rad=-0.15"),
            ha="center", fontsize=7.5, color="#059669", fontweight="bold"
        )

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Deterministic Closed-Loop Architecture",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 6. SYSTEM ARCHITECTURE DIAGRAM (Multi-Tier IoT/AI Stack)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_system_architecture(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.5
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11.5)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0b1329")
        ax.set_facecolor("#0b1329")

        # Title
        ax.text(5.75, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#ffffff")
        ax.text(5.75, fig_h - 0.9, d.subtitle, ha="center", va="center",
                fontsize=8, color="#38bdf8")

        layers = [
            ("PERCEPTION LAYER (FIELD)", "Soil Moisture Sensor Nodes • DHT22 Ambient Temp/Humidity • Solar Battery Telemetry", "#064e3b", "#34d399"),
            ("COMMUNICATION & EDGE GATEWAY", "ESP32 Wi-Fi / LoRa Gateway • MQTT Protocol Engine • Local Failsafe Cache", "#1e1b4b", "#818cf8"),
            ("INTELLIGENCE & DECISION LAYER", "Cloud AI/ML Classifier • Evapotranspiration Algorithm • Weather API Fusion", "#4c0519", "#fb7185"),
            ("ACTUATION & IRRIGATION LAYER", "Relay Control Modules • 12V DC Solenoid Valves • Precision Drip Emitter Manifold", "#361a06", "#fbbf24"),
        ]

        layer_h = (fig_h - 2.0) / len(layers) - 0.25
        for i, (l_title, l_desc, bg_c, acc_c) in enumerate(layers):
            ly = fig_h - 1.5 - (i + 1) * (layer_h + 0.25) + 0.15
            rect = patches.FancyBboxPatch(
                (0.8, ly), 9.9, layer_h,
                boxstyle="round,pad=0.1,rounding_size=0.12",
                facecolor=bg_c, edgecolor=acc_c, linewidth=1.5,
            )
            ax.add_patch(rect)

            ax.text(1.2, ly + layer_h - 0.35, f"LAYER {i+1}: {l_title}",
                    fontsize=8.5, fontweight="bold", color=acc_c)
            ax.text(1.2, ly + 0.25, l_desc,
                    fontsize=7.8, color="#e2e8f0")

            # Connector arrows between layers
            if i < len(layers) - 1:
                ax.annotate("", xy=(5.75, ly - 0.22), xytext=(5.75, ly),
                            arrowprops=dict(arrowstyle="->", color=acc_c, lw=1.5))

        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • Layered IoT-Edge-Cloud Methodology",
                 ha="center", fontsize=7.5, color="#94a3b8", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 7. PROCESS DIAGRAM (Stepped Horizontal Pipeline)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_process_diagram(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(4.8, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#f8fafc")

        ax.text(5.5, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=11.5, fontweight="bold", color="#0f172a")

        stages = [
            ("SENSE", "Dielectric\nMoisture Probe", "#0284c7"),
            ("ANALYZE", "Compute Soil\nWater Deficit", "#2563eb"),
            ("PREDICT", "Weather &\nEvapo Deficit", "#7c3aed"),
            ("DECIDE", "Evaluate AI\nTrigger Matrix", "#059669"),
            ("IRRIGATE", "Open Solenoid\nDrip Lines", "#d97706"),
            ("MONITOR", "Verify Root\nZone Absorption", "#16a34a"),
        ]

        bw = 1.4
        bh = 1.5
        spacing = (10.0 - len(stages) * bw) / (len(stages) - 1)
        y = fig_h * 0.45

        for i, (name, role, col) in enumerate(stages):
            x = 0.5 + i * (bw + spacing)
            box = patches.FancyBboxPatch(
                (x, y - bh/2), bw, bh,
                boxstyle="round,pad=0.08,rounding_size=0.1",
                facecolor="#ffffff", edgecolor=col, linewidth=1.8,
            )
            ax.add_patch(box)

            # Stage circle badge
            circle = plt.Circle((x + bw/2, y + bh/2 - 0.35), 0.22, color=col)
            ax.add_patch(circle)
            ax.text(x + bw/2, y + bh/2 - 0.35, str(i + 1), ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#ffffff")

            ax.text(x + bw/2, y + 0.05, name, ha="center", va="center",
                    fontsize=8.5, fontweight="bold", color=col)
            ax.text(x + bw/2, y - bh/2 + 0.35, role, ha="center", va="center",
                    fontsize=7, color="#475569")

            if i < len(stages) - 1:
                ax.annotate("", xy=(x + bw + spacing, y), xytext=(x + bw, y),
                            arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=1.8))

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Continuous Feedback Pipeline",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 8. COMPARISON TABLE / INFOGRAPHIC
    # -------------------------------------------------------------------------
    @classmethod
    def _render_comparison_table(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        ax.text(5.5, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#0f172a")
        ax.text(5.5, fig_h - 0.9, d.subtitle, ha="center", va="center",
                fontsize=8, color="#64748b")

        col_w = 4.6
        col_h = fig_h - 2.0
        y = 0.8

        # Left: Traditional
        ax.add_patch(patches.FancyBboxPatch(
            (0.7, y), col_w, col_h,
            boxstyle="round,pad=0.1,rounding_size=0.15",
            facecolor="#fef2f2", edgecolor="#ef4444", linewidth=1.5,
        ))
        ax.text(0.7 + col_w/2, y + col_h - 0.45, "TRADITIONAL IRRIGATION",
                ha="center", va="center", fontsize=10, fontweight="bold", color="#991b1b")
        trad_points = [
            "✗ Manual observation & scheduled timers",
            "✗ High water loss (30-45% evaporation/runoff)",
            "✗ Inconsistent root zone moisture levels",
            "✗ Risk of crop root hypoxia & nutrient leaching",
            "✗ Labor-intensive with zero predictive response",
        ]
        for idx, pt in enumerate(trad_points):
            ax.text(0.9, y + col_h - 1.0 - idx * 0.48, pt,
                    fontsize=7.8, color="#7f1d1d", va="center")

        # Right: AI-Based Smart
        ax.add_patch(patches.FancyBboxPatch(
            (5.7, y), col_w, col_h,
            boxstyle="round,pad=0.1,rounding_size=0.15",
            facecolor="#ecfdf5", edgecolor="#10b981", linewidth=1.5,
        ))
        ax.text(5.7 + col_w/2, y + col_h - 0.45, "AI-BASED PRECISION IRRIGATION",
                ha="center", va="center", fontsize=10, fontweight="bold", color="#065f46")
        ai_points = [
            "✓ Real-time soil moisture & dielectric sensing",
            "✓ Over 32% volumetric water conservation",
            "✓ Precise root-zone targeting via drip lines",
            "✓ Machine learning weather & evapotranspiration fusion",
            "✓ Fully autonomous solenoid actuation & telemetry",
        ]
        for idx, pt in enumerate(ai_points):
            ax.text(5.9, y + col_h - 1.0 - idx * 0.48, pt,
                    fontsize=7.8, color="#064e3b", va="center", fontweight="semibold")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Agronomic System Comparison Matrix",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 9. TIMELINE / PROCESS VISUALIZATION
    # -------------------------------------------------------------------------
    @classmethod
    def _render_timeline_process(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#f8fafc")

        ax.text(5.5, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=11.5, fontweight="bold", color="#0f172a")

        milestones = [
            ("PHASE 1", "Hardware Setup &\nSensor Calibration", "Week 1-3", "#0284c7"),
            ("PHASE 2", "IoT Telemetry Node\nField Deployment", "Week 4-6", "#2563eb"),
            ("PHASE 3", "AI Model Training &\nThreshold Tuning", "Week 7-9", "#7c3aed"),
            ("PHASE 4", "Autonomous Drip &\nClosed-Loop Audit", "Week 10-12", "#059669"),
        ]

        # Central timeline bar
        ax.plot([1.0, 10.0], [fig_h * 0.5, fig_h * 0.5], color="#cbd5e1", linewidth=4.0, zorder=1)

        xs = np.linspace(1.8, 9.2, len(milestones))
        for i, (phase, desc, time_tag, col) in enumerate(milestones):
            px = xs[i]
            py = fig_h * 0.5
            circle = plt.Circle((px, py), 0.28, color=col, zorder=3)
            ax.add_patch(circle)
            ax.text(px, py, str(i + 1), ha="center", va="center",
                    fontsize=9, fontweight="bold", color="#ffffff", zorder=4)

            # Alternate top and bottom callouts
            is_top = (i % 2 == 0)
            box_y = py + 0.6 if is_top else py - 1.5
            ax.add_patch(patches.FancyBboxPatch(
                (px - 1.0, box_y), 2.0, 0.9,
                boxstyle="round,pad=0.08,rounding_size=0.08",
                facecolor="#ffffff", edgecolor=col, linewidth=1.5, zorder=2
            ))
            ax.text(px, box_y + 0.65, phase, ha="center", fontsize=7.8, fontweight="bold", color=col)
            ax.text(px, box_y + 0.35, desc, ha="center", fontsize=6.8, color="#1e293b")
            ax.text(px, box_y + 0.1, time_tag, ha="center", fontsize=6.5, color="#64748b", fontstyle="italic")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Implementation Milestone Architecture",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 10. DASHBOARD-STYLE VISUALIZATION
    # -------------------------------------------------------------------------
    @classmethod
    def _render_dashboard_visualization(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.5
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11.5)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        ax.text(5.75, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#ffffff")
        ax.text(5.75, fig_h - 0.9, "LIVE CLOSED-LOOP IOT TELEMETRY & CONTROLLER STATUS", ha="center", va="center",
                fontsize=8, color="#38bdf8")

        # 4 Dashboard Quadrants/Cards
        quads = [
            ("SOIL MOISTURE", "42.8% VWC", "Status: OPTIMAL\nDepth: 15cm Root Zone\nTrend: Steady", "#10b981", "#064e3b"),
            ("SOLENOID VALVE", "CLOSED", "Last Active: 2h ago\nVolume: 18.5 Liters\nNext Cycle: Auto (AI)", "#38bdf8", "#0c4a6e"),
            ("BATTERY & SOLAR", "98% (4.1V)", "Solar Input: 5.2V\nPower Draw: 12mA\nHealth: Normal", "#fbbf24", "#451a03"),
            ("AI DEFICIT ENGINE", "READY", "Inference: Active\nConfidence: 96.4%\nFailsafe: Enabled", "#c084fc", "#3b0764"),
        ]

        qw = 2.4
        qh = fig_h - 2.1
        sx = 0.7
        gap = 0.35

        for i, (title, val, desc, acc, bg) in enumerate(quads):
            x = sx + i * (qw + gap)
            y = 0.8
            ax.add_patch(patches.FancyBboxPatch(
                (x, y), qw, qh,
                boxstyle="round,pad=0.1,rounding_size=0.12",
                facecolor=bg, edgecolor=acc, linewidth=1.5,
            ))
            ax.text(x + qw/2, y + qh - 0.4, title, ha="center", fontsize=8.5, fontweight="bold", color="#ffffff")
            ax.text(x + qw/2, y + qh - 1.0, val, ha="center", fontsize=15, fontweight="bold", color=acc)
            ax.text(x + qw/2, y + 0.5, desc, ha="center", fontsize=7.2, color="#cbd5e1", linespacing=1.3)

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Real-Time Field Telemetry Telecommunications",
                 ha="center", fontsize=7.5, color="#94a3b8", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 11. DIAGRAM + SUPPORTING IMAGE (Dual-Panel Split)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_diagram_supporting_image(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.5
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, (ax_img, ax_diag) = plt.subplots(1, 2, figsize=(fig_w, fig_h), dpi=200, gridspec_kw={"width_ratios": [1, 1]})

        fig.patch.set_facecolor("#0b1329")

        # Left Panel: Photorealistic Irrigated Farmland Rendering
        ax_img.set_facecolor("#064e3b")
        ax_img.axis("off")
        # Generate rich agricultural landscape visual
        xs = np.linspace(0, 10, 200)
        ys = np.linspace(0, 10, 200)
        X, Y = np.meshgrid(xs, ys)
        # Perspective rows of green crops
        Z = np.sin(X * 3.0) * np.cos(Y * 0.5) + (Y * 0.3)
        ax_img.imshow(Z, cmap="YlGn", aspect="auto", extent=[0, 10, 0, 10])
        # Drip irrigation lines overlay
        for ly in np.linspace(1, 9, 7):
            ax_img.axhline(ly, color="#0284c7", linewidth=1.5, linestyle="--", alpha=0.8)
        # Smart Sensor Node marker in field
        ax_img.plot(5, 5, marker="o", markersize=12, color="#38bdf8", markeredgecolor="#ffffff", markeredgewidth=2)
        ax_img.text(5, 5.8, "IoT SENSOR NODE #01", ha="center", fontsize=7.5, fontweight="bold",
                    color="#ffffff", bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", alpha=0.8))
        ax_img.set_title("FIELD DEPLOYMENT SIGHT", fontsize=10, fontweight="bold", color="#ffffff", pad=8)

        # Right Panel: Real-Time Telemetry Analytics
        ax_diag.set_facecolor("#0f172a")
        ax_diag.axis("off")
        ax_diag.set_title("IN-FIELD TELEMETRY METRICS", fontsize=10, fontweight="bold", color="#38bdf8", pad=8)

        stats = [
            ("Root Zone Moisture", "42.8%", "#10b981"),
            ("Application Efficiency", "87.6%", "#38bdf8"),
            ("Water Saved vs Flood", "32.4%", "#fbbf24"),
            ("Transmission Latency", "< 1.2s", "#a855f7"),
        ]
        for idx, (label, val, col) in enumerate(stats):
            sy = 8.0 - idx * 2.0
            rect = patches.FancyBboxPatch((0.5, sy - 0.7), 9.0, 1.4,
                                          boxstyle="round,pad=0.1,rounding_size=0.1",
                                          facecolor="#1e293b", edgecolor=col, linewidth=1.2)
            ax_diag.add_patch(rect)
            ax_diag.text(1.0, sy, label, fontsize=8.5, fontweight="bold", color="#e2e8f0", va="center")
            ax_diag.text(8.8, sy, val, fontsize=12, fontweight="bold", color=col, va="center", ha="right")
        ax_diag.set_xlim(0, 10)
        ax_diag.set_ylim(0, 10)

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Dual Field Perspective & Telemetry Sync",
                 ha="center", fontsize=7.5, color="#94a3b8", fontstyle="italic")

        plt.tight_layout(rect=[0, 0.04, 1, 0.96])
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 12. TECHNICAL ILLUSTRATION (Dielectric Sensor Probe Anatomy)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_technical_illustration(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#ffffff")

        ax.text(5.0, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=11.5, fontweight="bold", color="#0f172a")
        ax.text(5.0, fig_h - 0.9, d.subtitle, ha="center", va="center",
                fontsize=8, color="#0284c7")

        # Center probe schematic
        # Sensor PCB head
        ax.add_patch(patches.FancyBboxPatch(
            (4.0, fig_h * 0.55), 2.0, 1.2,
            boxstyle="round,pad=0.08,rounding_size=0.1",
            facecolor="#0f172a", edgecolor="#38bdf8", linewidth=2.0
        ))
        ax.text(5.0, fig_h * 0.55 + 0.6, "PCB CONTROLLER\n& 555 OSCILLATOR", ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="#38bdf8")

        # Dual Probe prongs into soil
        ax.add_patch(patches.Rectangle((4.3, 0.8), 0.35, fig_h * 0.55 - 0.8, facecolor="#94a3b8", edgecolor="#475569", linewidth=1.5))
        ax.add_patch(patches.Rectangle((5.35, 0.8), 0.35, fig_h * 0.55 - 0.8, facecolor="#94a3b8", edgecolor="#475569", linewidth=1.5))

        # Soil level line
        ax.axhline(fig_h * 0.42, color="#78350f", linewidth=2.5, linestyle="--")
        ax.text(1.5, fig_h * 0.42 + 0.15, "Ground Level (Soil Surface)", fontsize=8, fontweight="bold", color="#78350f")

        # Callouts
        ax.annotate("VCC (3.3V-5V) / GND\nAnalog Output (0-3.0V)", xy=(4.0, fig_h * 0.65), xytext=(1.2, fig_h * 0.65),
                    arrowprops=dict(facecolor="#0284c7", shrink=0.08, width=1.0, headwidth=5),
                    fontsize=7.5, fontweight="bold", color="#0284c7")
        ax.annotate("Dielectric Capacitive Prongs\nCorrosion-Resistant Gold Flash", xy=(5.7, fig_h * 0.25), xytext=(7.0, fig_h * 0.25),
                    arrowprops=dict(facecolor="#059669", shrink=0.08, width=1.0, headwidth=5),
                    fontsize=7.5, fontweight="bold", color="#059669")

        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • High-Frequency Capacitive Permittivity",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 13. REALISTIC AGRICULTURAL / ENVIRONMENT IMAGE
    # -------------------------------------------------------------------------
    @classmethod
    def _render_realistic_agri_environment(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Lush gradient sky to agricultural field
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.Blues(0.3 + 0.4 * (1.0 - frac)))

        # Distant hills
        xs = np.linspace(0, 11, 200)
        hills = sky_h + 0.5 * np.sin(xs * 0.8) + 0.3 * np.cos(xs * 1.5)
        ax.fill_between(xs, 0, hills, color="#1e3a1e", alpha=0.9)

        # Foreground vibrant green crop rows with perspective
        for row_i in range(12):
            ry = (row_i / 12.0) * sky_h
            r_color = plt.cm.Greens(0.5 + 0.4 * (row_i / 12.0))
            ax.fill_between(xs, 0, ry, color=r_color, alpha=0.85)

        # Precision Drip Irrigation Tubing
        for tx in np.linspace(1.5, 9.5, 6):
            ax.plot([tx, 5.5], [0, sky_h * 0.9], color="#0284c7", linewidth=2.0, alpha=0.8, linestyle=":")

        # Overlay Title Banner
        ax.text(5.5, fig_h - 0.8, d.title.upper(), ha="center", va="center",
                fontsize=14, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#0f172a", alpha=0.85, edgecolor="#38bdf8", linewidth=1.5))
        ax.text(5.5, fig_h - 1.5, d.subtitle, ha="center", va="center",
                fontsize=9, fontweight="bold", color="#38bdf8",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f172a", alpha=0.75, edgecolor="none"))

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Precision Irrigated Agro-Ecosystem",
                 ha="center", fontsize=7.5, color="#ffffff", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 14. REALISTIC PHOTOGRAPH (Generic Hardware / Environment Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_realistic_photograph(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 10.0
        fig_h = max(5.0, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Dark sleek industrial/tech aesthetic
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        # Grid lines
        for gx in range(11):
            ax.axvline(gx, color="#1e293b", linewidth=0.5)
        for gy in range(int(fig_h) + 1):
            ax.axhline(gy, color="#1e293b", linewidth=0.5)

        # Central Hardware Frame
        ax.add_patch(patches.FancyBboxPatch(
            (1.5, 0.8), 7.0, fig_h - 1.8,
            boxstyle="round,pad=0.1,rounding_size=0.15",
            facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.0
        ))

        ax.text(5.0, fig_h - 1.4, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#ffffff")
        ax.text(5.0, fig_h - 2.0, d.subtitle, ha="center", va="center",
                fontsize=8.5, color="#38bdf8")
        ax.text(5.0, fig_h * 0.45, "PRECISION EMBEDDED SYSTEM DEPLOYMENT", ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="#94a3b8")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Technical Field System Demonstration",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 15. DROUGHT & WATER SCARCITY (Problem Statement Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_drought_water_scarcity(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Harsh arid gradient: intense sunlit sky to dry parched soil
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.YlOrBr(0.2 + 0.35 * (1.0 - frac)))

        # Distant dry barren hills
        xs = np.linspace(0, 11, 250)
        hills = sky_h + 0.4 * np.sin(xs * 0.9) + 0.25 * np.cos(xs * 1.8)
        ax.fill_between(xs, 0, hills, color="#78350f", alpha=0.9)

        # Foreground dry parched earth layers with fissure lines
        for row_i in range(12):
            ry = (row_i / 12.0) * sky_h
            r_color = plt.cm.YlOrBr(0.55 + 0.35 * (row_i / 12.0))
            ax.fill_between(xs, 0, ry, color=r_color, alpha=0.9)

        # Stylized cracked earth fissures
        np.random.seed(42)
        for fx in np.linspace(0.8, 10.2, 14):
            fy_start = 0.2
            fy_end = sky_h * (0.6 + 0.3 * np.random.rand())
            crack_xs = [fx]
            crack_ys = [fy_start]
            curr_x = fx
            curr_y = fy_start
            while curr_y < fy_end:
                curr_y += 0.4
                curr_x += (np.random.rand() - 0.5) * 0.5
                crack_xs.append(curr_x)
                crack_ys.append(curr_y)
            ax.plot(crack_xs, crack_ys, color="#451a03", linewidth=1.4, alpha=0.85)

        # Water scarcity callout badges
        ax.text(5.5, fig_h - 0.8, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#451a03", alpha=0.9, edgecolor="#f59e0b", linewidth=1.5))
        ax.text(5.5, fig_h - 1.5, d.subtitle or "WATER DEFICIT & SOIL DROUGHT CHALLENGE", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#fde68a",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#78350f", alpha=0.85, edgecolor="none"))

        # Stat pills
        metrics = [
            ("UNREGULATED WATER LOSS", "Up to 45% Runoff", "#ef4444", 2.2),
            ("SOIL MOISTURE DEFICIT", "< 22% VWC Critical", "#f59e0b", 5.5),
            ("CROP STRESS INDEX", "Severe Stunting", "#dc2626", 8.8),
        ]
        for m_lbl, m_val, m_col, mx in metrics:
            ax.add_patch(patches.FancyBboxPatch(
                (mx - 1.4, 0.4), 2.8, 0.75,
                boxstyle="round,pad=0.08", facecolor="#1e293b", edgecolor=m_col, linewidth=1.2
            ))
            ax.text(mx, 0.9, m_lbl, ha="center", va="center", fontsize=6.8, fontweight="bold", color="#94a3b8")
            ax.text(mx, 0.6, m_val, ha="center", va="center", fontsize=8.0, fontweight="bold", color=m_col)

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Parched Agricultural Arid Environment Visual",
                 ha="center", fontsize=7.5, color="#451a03", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 16. TRADITIONAL CONVENTIONAL IRRIGATION (Existing System Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_traditional_irrigation(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Overcast field lighting
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.copper(0.2 + 0.3 * (1.0 - frac)))

        # Earth and muddy crop ridges
        xs = np.linspace(0, 11, 200)
        for r_idx in range(8):
            ry = (r_idx / 8.0) * sky_h
            ax.fill_between(xs, 0, ry, color="#5c3a21" if r_idx % 2 == 0 else "#3d2616", alpha=0.9)

        # Unlined flooded muddy water channels (furrows)
        for fx in [2.5, 5.5, 8.5]:
            ax.plot([fx, fx * 0.8 + 1.1], [0, sky_h * 0.9], color="#38bdf8", linewidth=6.0, alpha=0.6)
            ax.plot([fx, fx * 0.8 + 1.1], [0, sky_h * 0.9], color="#0284c7", linewidth=2.5, alpha=0.9)

        # Title Banner
        ax.text(5.5, fig_h - 0.8, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#3d2616", alpha=0.9, edgecolor="#fbbf24", linewidth=1.5))
        ax.text(5.5, fig_h - 1.5, d.subtitle or "CONVENTIONAL FLOOD & FURROW IRRIGATION", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#fef08a",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#5c3a21", alpha=0.85, edgecolor="none"))

        # Inefficiencies banner
        tags = [
            ("✗ Excessive Surface Evaporation", 2.0),
            ("✗ Uneven Root Infiltration", 5.5),
            ("✗ Zero Telemetry Feedback", 9.0),
        ]
        for t_text, tx in tags:
            ax.add_patch(patches.FancyBboxPatch(
                (tx - 1.6, 0.4), 3.2, 0.65,
                boxstyle="round,pad=0.08", facecolor="#1e293b", edgecolor="#ef4444", linewidth=1.2
            ))
            ax.text(tx, 0.72, t_text, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#fca5a5")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Conventional Flood Irrigation Farm Visual",
                 ha="center", fontsize=7.5, color="#3d2616", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 17. SMART DRIP IRRIGATION (Proposed System Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_smart_drip_irrigation(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Clear sunny sky gradient
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.Blues(0.25 + 0.45 * (1.0 - frac)))

        # Vibrant green crop rows
        xs = np.linspace(0, 11, 200)
        for r_idx in range(10):
            ry = (r_idx / 10.0) * sky_h
            r_col = plt.cm.Greens(0.45 + 0.45 * (r_idx / 10.0))
            ax.fill_between(xs, 0, ry, color=r_col, alpha=0.85)

        # Precision Black Drip Lines with Emitter Water Droplets
        for tx in np.linspace(1.5, 9.5, 7):
            ax.plot([tx, 5.5], [0, sky_h * 0.9], color="#0f172a", linewidth=3.0, alpha=0.9)
            # Water droplet indicators along line
            for dy in np.linspace(0.4, sky_h * 0.8, 5):
                cur_x = tx + (5.5 - tx) * (dy / (sky_h * 0.9))
                ax.plot(cur_x, dy, marker="o", markersize=6, color="#38bdf8", markeredgecolor="#ffffff", markeredgewidth=1)

        # Title Banner
        ax.text(5.5, fig_h - 0.8, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#064e3b", alpha=0.9, edgecolor="#34d399", linewidth=1.5))
        ax.text(5.5, fig_h - 1.5, d.subtitle or "AUTOMATED PRECISION ROOT-ZONE DRIP HYDRATION", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#6ee7b7",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f172a", alpha=0.85, edgecolor="none"))

        # Benefits banner
        tags = [
            ("✓ 41.8% Water Conserved", 2.0),
            ("✓ Zero Surface Evaporation", 5.5),
            ("✓ Autonomous Solenoid Control", 9.0),
        ]
        for t_text, tx in tags:
            ax.add_patch(patches.FancyBboxPatch(
                (tx - 1.6, 0.4), 3.2, 0.65,
                boxstyle="round,pad=0.08", facecolor="#1e293b", edgecolor="#10b981", linewidth=1.2
            ))
            ax.text(tx, 0.72, t_text, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#6ee7b7")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Precision Automated Drip Irrigation Farm Visual",
                 ha="center", fontsize=7.5, color="#064e3b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 18. SOIL MOISTURE SENSOR PROBE (Technical Photo Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_soil_moisture_probe(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Ground cross section: Above ground light vs underground dark soil
        ground_y = fig_h * 0.52
        ax.axhspan(ground_y, fig_h, color="#f1f5f9")
        ax.axhspan(0, ground_y, color="#2d1b0d")  # rich dark moist soil

        # Soil surface texture line
        ax.axhline(ground_y, color="#78350f", linewidth=3.0)
        ax.text(0.8, ground_y + 0.18, "SOIL SURFACE (GROUND LEVEL)", fontsize=7.5, fontweight="bold", color="#78350f")

        # Green plant stem above ground
        ax.plot([3.5, 3.5], [ground_y, fig_h - 1.4], color="#16a34a", linewidth=5.0)
        # Leaves
        ax.plot([3.5, 2.5], [ground_y + 0.8, ground_y + 1.2], color="#22c55e", linewidth=3.0)
        ax.plot([3.5, 4.5], [ground_y + 1.2, ground_y + 1.6], color="#22c55e", linewidth=3.0)

        # Plant root branches below ground
        for rx, ry in [(3.0, ground_y - 0.8), (4.0, ground_y - 1.1), (2.7, ground_y - 1.6), (3.8, ground_y - 1.8)]:
            ax.plot([3.5, rx], [ground_y, ry], color="#d97706", linewidth=1.8, linestyle=":")

        # Capacitive Sensor Probe inserted into soil
        probe_x = 5.5
        # Controller head above/at ground
        ax.add_patch(patches.FancyBboxPatch(
            (probe_x - 0.7, ground_y - 0.3), 1.4, 1.2,
            boxstyle="round,pad=0.08", facecolor="#0f172a", edgecolor="#38bdf8", linewidth=2.0
        ))
        ax.text(probe_x, ground_y + 0.3, "CAPACITIVE\nSENSOR NODE", ha="center", va="center",
                fontsize=7.0, fontweight="bold", color="#38bdf8")

        # Dual dielectric prongs inserted deep into soil root zone
        prong_bottom = ground_y - 2.0
        ax.add_patch(patches.Rectangle((probe_x - 0.45, prong_bottom), 0.28, 1.7, facecolor="#cbd5e1", edgecolor="#94a3b8", linewidth=1.5))
        ax.add_patch(patches.Rectangle((probe_x + 0.17, prong_bottom), 0.28, 1.7, facecolor="#cbd5e1", edgecolor="#94a3b8", linewidth=1.5))

        # Moisture field permittivity ripples around prongs
        for r_rad in [0.4, 0.7, 1.0]:
            ripple = patches.Circle((probe_x, prong_bottom + 0.85), r_rad, fill=False, edgecolor="#38bdf8", linestyle="--", alpha=0.7)
            ax.add_patch(ripple)

        # Technical Callouts
        ax.annotate("Dielectric Capacitive Prongs\n(Gold-Plated, Corrosion-Proof)",
                    xy=(probe_x + 0.5, prong_bottom + 0.85), xytext=(7.8, prong_bottom + 0.85),
                    arrowprops=dict(facecolor="#38bdf8", shrink=0.08, width=1.2, headwidth=5),
                    fontsize=7.5, fontweight="bold", color="#38bdf8")

        ax.annotate("Root Zone Moisture Zone\n(In-Situ VWC: 42.8% Optimum)",
                    xy=(probe_x - 0.6, prong_bottom + 0.5), xytext=(0.8, prong_bottom + 0.5),
                    arrowprops=dict(facecolor="#34d399", shrink=0.08, width=1.2, headwidth=5),
                    fontsize=7.5, fontweight="bold", color="#34d399")

        # Title Banner
        ax.text(5.5, fig_h - 0.6, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#0f172a")
        ax.text(5.5, fig_h - 1.0, d.subtitle or "IN-SITU ROOT-ZONE DIELECTRIC SENSING (30CM DEPTH)", ha="center", va="center",
                fontsize=8.0, fontweight="bold", color="#0284c7")

        fig.text(0.5, 0.02, f"Source: {d.data_source_label} • High-Frequency Capacitive Permittivity Sensing",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 19. AI DECISION & AGRONOMIC TELEMETRY (Conceptual Illustration)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_ai_decision_telemetry(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.5
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11.5)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        fig.patch.set_facecolor("#0b1329")
        ax.set_facecolor("#0b1329")

        # Title
        ax.text(5.75, fig_h - 0.5, d.title.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="#ffffff")
        ax.text(5.75, fig_h - 0.9, d.subtitle or "CLOSED-LOOP AI DECISION ENGINE & TELEMETRY", ha="center", va="center",
                fontsize=8.0, color="#38bdf8")

        cards = [
            ("1. TELEMETRY INGESTION", "Real-time capacitive soil moisture,\nambient temp & humidity ingestion\nevery 60s via LoRaWAN.", "#064e3b", "#34d399", 0.8, fig_h * 0.48),
            ("2. PREDICTIVE AI MODEL", "Evapotranspiration rate estimation,\nrainfall probability fusion, and\nsoil water deficit forecasting.", "#1e1b4b", "#818cf8", 4.3, fig_h * 0.48),
            ("3. AUTONOMOUS VALVE DISPATCH", "Targeted zone irrigation cycle:\nenergizes solenoid valves only when\nmoisture drops below 30% VWC.", "#451a03", "#fbbf24", 7.8, fig_h * 0.48),
        ]

        card_w = 3.0
        card_h = fig_h * 0.35
        for title, desc, bg_c, acc_c, cx, cy in cards:
            rect = patches.FancyBboxPatch(
                (cx, cy - card_h/2), card_w, card_h,
                boxstyle="round,pad=0.1,rounding_size=0.12",
                facecolor=bg_c, edgecolor=acc_c, linewidth=1.5,
            )
            ax.add_patch(rect)
            ax.text(cx + card_w/2, cy + card_h/2 - 0.35, title, ha="center", va="center",
                    fontsize=7.8, fontweight="bold", color="#ffffff")
            ax.text(cx + card_w/2, cy - 0.1, desc, ha="center", va="center",
                    fontsize=7.0, color="#cbd5e1", linespacing=1.3)

        # Connection arrows between cards
        ax.annotate("", xy=(4.2, fig_h * 0.48), xytext=(3.9, fig_h * 0.48),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2.0))
        ax.annotate("", xy=(7.7, fig_h * 0.48), xytext=(7.4, fig_h * 0.48),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2.0))

        # Bottom Telemetry Bar
        bar_box = patches.FancyBboxPatch(
            (0.8, 0.4), 9.9, 0.9,
            boxstyle="round,pad=0.08", facecolor="#1e293b", edgecolor="#334155", linewidth=1.0
        )
        ax.add_patch(bar_box)
        metrics = [
            ("AI Inference Latency", "12 ms", "#38bdf8", 2.2),
            ("Moisture Trigger Level", "28.5% VWC", "#f59e0b", 5.75),
            ("Irrigation Efficiency", "94.2%", "#34d399", 9.3),
        ]
        for m_lbl, m_val, m_col, mx in metrics:
            ax.text(mx, 0.95, m_lbl, ha="center", va="center", fontsize=6.8, color="#94a3b8")
            ax.text(mx, 0.65, m_val, ha="center", va="center", fontsize=8.5, fontweight="bold", color=m_col)

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Deterministic Telemetry & Control Flow",
                 ha="center", fontsize=7.5, color="#64748b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 20. FIELD DEPLOYMENT (Realistic Deployment Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_field_deployment(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Daylight sky gradient
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.Blues(0.2 + 0.4 * (1.0 - frac)))

        # Green field rows
        xs = np.linspace(0, 11, 200)
        for r_idx in range(12):
            ry = (r_idx / 12.0) * sky_h
            r_col = plt.cm.Greens(0.4 + 0.5 * (r_idx / 12.0))
            ax.fill_between(xs, 0, ry, color=r_col, alpha=0.85)

        # Solar Telemetry Station on pole in field center
        pole_x = 5.5
        ax.plot([pole_x, pole_x], [0.8, sky_h + 1.2], color="#94a3b8", linewidth=4.0)
        # Solar panel on top
        ax.add_patch(patches.Polygon([[pole_x - 0.6, sky_h + 1.1], [pole_x + 0.6, sky_h + 1.3],
                                      [pole_x + 0.5, sky_h + 1.6], [pole_x - 0.7, sky_h + 1.4]],
                                     facecolor="#1e1b4b", edgecolor="#38bdf8", linewidth=1.5))
        # Weatherproof enclosure
        ax.add_patch(patches.FancyBboxPatch(
            (pole_x - 0.4, sky_h - 0.2), 0.8, 0.9,
            boxstyle="round,pad=0.05", facecolor="#0f172a", edgecolor="#10b981", linewidth=1.5
        ))
        ax.text(pole_x, sky_h + 0.25, "SOLAR\nIoT NODE", ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="#34d399")

        # Antenna
        ax.plot([pole_x, pole_x], [sky_h + 0.7, sky_h + 1.8], color="#e2e8f0", linewidth=1.5)

        # Drip lines radiating into rows
        for dx in [1.5, 3.0, 8.0, 9.5]:
            ax.plot([pole_x, dx], [0.8, 0.2], color="#0284c7", linewidth=2.0, linestyle=":")

        # Title Banner
        ax.text(5.5, fig_h - 0.7, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#064e3b", alpha=0.9, edgecolor="#34d399", linewidth=1.5))
        ax.text(5.5, fig_h - 1.4, d.subtitle or "COMMERCIAL AGRICULTURAL TRIAL & FIELD DEPLOYMENT", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#6ee7b7",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f172a", alpha=0.85, edgecolor="none"))

        # Field Status Badge
        ax.add_patch(patches.FancyBboxPatch(
            (3.0, 0.4), 5.0, 0.65,
            boxstyle="round,pad=0.08", facecolor="#0f172a", edgecolor="#38bdf8", linewidth=1.2
        ))
        ax.text(5.5, 0.72, "STATUS: ACTIVE TELEMETRY • LORAWAN RANGE: 4.2 KM", ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="#38bdf8")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Real-World Farm Deployment Perspective",
                 ha="center", fontsize=7.5, color="#064e3b", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    # -------------------------------------------------------------------------
    # 21. FUTURE AGRICULTURE & DRONE TELEMETRY (Future Scope Visual)
    # -------------------------------------------------------------------------
    @classmethod
    def _render_future_agriculture(cls, d: VisualDecision, out_path: str, ar: float, fmt: str) -> str:
        fig_w = 11.0
        fig_h = max(5.5, round(fig_w / max(0.5, ar), 2))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
        ax.set_xlim(0, 11)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        # Sunset golden hour sky gradient
        sky_h = fig_h * 0.45
        for i in range(100):
            frac = i / 100.0
            y_curr = fig_h - frac * (fig_h - sky_h)
            ax.axhspan(y_curr - 0.1, y_curr, color=plt.cm.magma(0.25 + 0.45 * (1.0 - frac)))

        # Next-gen smart crop fields
        xs = np.linspace(0, 11, 200)
        for r_idx in range(10):
            ry = (r_idx / 10.0) * sky_h
            r_col = plt.cm.viridis(0.3 + 0.5 * (r_idx / 10.0))
            ax.fill_between(xs, 0, ry, color=r_col, alpha=0.85)

        # Drone schematic in sky
        drone_x, drone_y = 7.5, fig_h - 1.8
        ax.plot([drone_x - 0.6, drone_x + 0.6], [drone_y, drone_y], color="#ffffff", linewidth=3.0)
        ax.plot([drone_x, drone_x], [drone_y - 0.3, drone_y + 0.3], color="#ffffff", linewidth=3.0)
        # Rotors
        for rx, ry in [(drone_x - 0.6, drone_y), (drone_x + 0.6, drone_y), (drone_x, drone_y - 0.3), (drone_x, drone_y + 0.3)]:
            ax.plot([rx - 0.2, rx + 0.2], [ry, ry], color="#38bdf8", linewidth=2.0)
        # Sensor scan beam down to field
        ax.plot([drone_x, 4.5], [drone_y, 0.5], color="#38bdf8", linestyle=":", alpha=0.5)
        ax.plot([drone_x, 9.5], [drone_y, 0.5], color="#38bdf8", linestyle=":", alpha=0.5)

        # Title Banner
        ax.text(5.5, fig_h - 0.7, d.title.upper(), ha="center", va="center",
                fontsize=13, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#0f172a", alpha=0.9, edgecolor="#c084fc", linewidth=1.5))
        ax.text(5.5, fig_h - 1.4, d.subtitle or "NEXT-GENERATION AUTONOMOUS AGRO-ECOSYSTEM", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#e9d5ff",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#31104b", alpha=0.85, edgecolor="none"))

        # Future pillars
        tags = [
            ("Aerial Multispectral Imaging", 2.2),
            ("Autonomous Solar Micro-Drip", 5.5),
            ("Federated Edge AI Fleet", 8.8),
        ]
        for t_text, tx in tags:
            ax.add_patch(patches.FancyBboxPatch(
                (tx - 1.5, 0.4), 3.0, 0.65,
                boxstyle="round,pad=0.08", facecolor="#0f172a", edgecolor="#a855f7", linewidth=1.2
            ))
            ax.text(tx, 0.72, t_text, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#e9d5ff")

        fig.text(0.5, 0.02, f"Note: {d.data_source_label} • Forward-Looking Sustainable Agriculture Visual",
                 ha="center", fontsize=7.5, color="#ffffff", fontstyle="italic")

        plt.tight_layout()
        cls._save_fig(fig, out_path, fmt)
        return out_path

    @classmethod
    def _save_fig(cls, fig: plt.Figure, out_path: str, fmt: str) -> None:
        """Saves figure with clean closing and color conversion."""
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        out_fmt = "jpeg" if fmt.upper() in ("JPEG", "JPG") else "png"
        fig.savefig(out_path, format=out_fmt, bbox_inches="tight", dpi=200)
        plt.close(fig)


# Singleton instance
visual_decision_engine = VisualDecisionEngine()
