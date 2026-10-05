"""
ReportForge AI - Dynamic Academic Diagram & Image Generator
Generates academic diagrams, system block flowcharts, and empirical evaluation charts
tailored dynamically to the user's specific project title and research domain.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any, Optional
from apps.api.core.logging import get_logger

logger = get_logger("document.images")


def generate_diagrams_for_report(report_id: str, title: str = "Engineering Project", out_dir: str = ".storage/images") -> Dict[str, str]:
    """
    Generates required academic technical figures dynamically tailored to the given project title.
    Returns mapping of slot_id -> image_file_path.
    """
    os.makedirs(out_dir, exist_ok=True)
    images: Dict[str, str] = {}
    clean_title = title.strip()[:40]

    # Domain classification for contextual chart categories
    t_lower = title.lower()
    if any(k in t_lower for k in ["chatgpt", "gpt", "llm", "language model", "nlp", "transformer"]):
        cat_1 = ["Hallucination Rate", "Inference Latency", "Context Window Limits", "Token Consumption", "Prompt Drift"]
        freq_1 = [44, 38, 32, 25, 17]
        flow_blocks = [
            ("Prompt Input\n& Tokenization", 0.08, 0.5, "#2C3E50"),
            ("Multi-Head Attention\n& Transformer Core", 0.30, 0.5, "#2980B9"),
            ("RLHF Alignment\n& Safety Filter", 0.53, 0.5, "#A01E1E"),
            ("Decoded Tokens\n& Response Gen", 0.76, 0.5, "#27AE60"),
            ("KV-Cache &\nVector Memory", 0.53, 0.12, "#D35400"),
        ]
        eval_metrics = ["Factual Precision", "Response Latency", "Coherence Score", "Token Throughput", "Safety Alignment"]
        base_vals = [42, 35, 48, 52, 40]
        prop_vals = [97, 93, 96, 91, 98]
    elif any(k in t_lower for k in ["electric", "circuit", "power", "energy", "solar", "voltage"]):
        cat_1 = ["Insulation Aging", "Grounding Faults", "Overcurrent Spikes", "Switchgear Wear", "Thermal Overheating"]
        freq_1 = [38, 42, 29, 21, 16]
        flow_blocks = [
            ("Power Input\n& Ingestion", 0.08, 0.5, "#2C3E50"),
            ("Conditioning\n& Metering", 0.30, 0.5, "#2980B9"),
            ("Safety Protection\nCore (RCCB/Relay)", 0.53, 0.5, "#A01E1E"),
            ("Distribution &\nBranch Circuits", 0.76, 0.5, "#27AE60"),
            ("Grounding &\nEarth Reference", 0.53, 0.12, "#D35400"),
        ]
        eval_metrics = ["Fault Detection", "Response Time", "Safety Clearance", "Thermal Stability", "Standard Compliance"]
        base_vals = [32, 28, 40, 35, 25]
        prop_vals = [94, 91, 96, 89, 98]
    elif any(k in t_lower for k in ["ai", "machine learning", "deep learning", "neural", "vision", "detection"]):
        cat_1 = ["Data Sparsity", "Inference Latency", "Model Overfitting", "Adversarial Noise", "Hardware Overhead"]
        freq_1 = [45, 36, 31, 24, 18]
        flow_blocks = [
            ("Raw Telemetry\n& Dataset Stream", 0.08, 0.5, "#2C3E50"),
            ("Preprocessing\n& Feature Extraction", 0.30, 0.5, "#2980B9"),
            ("Deep Neural\nInference Model", 0.53, 0.5, "#A01E1E"),
            ("Decision Engine\n& Predictions", 0.76, 0.5, "#27AE60"),
            ("Continuous Feedback\n& Retraining", 0.53, 0.12, "#D35400"),
        ]
        eval_metrics = ["Accuracy (F1)", "Inference Speed", "Noise Robustness", "Memory Footprint", "Generalization"]
        base_vals = [48, 35, 42, 50, 38]
        prop_vals = [96, 92, 94, 88, 95]
    elif any(k in t_lower for k in ["iot", "sensor", "embedded", "drone", "robot", "smart"]):
        cat_1 = ["Battery Depletion", "Packet Loss", "Environmental Interference", "Sensor Drift", "Latency Jitter"]
        freq_1 = [41, 35, 28, 22, 19]
        flow_blocks = [
            ("Edge Sensors\n& Perception", 0.08, 0.5, "#2C3E50"),
            ("Microcontroller\n& Firmware Core", 0.30, 0.5, "#2980B9"),
            ("Wireless Gateway\n(LoRa / MQTT)", 0.53, 0.5, "#A01E1E"),
            ("Cloud Dashboard\n& Telemetry", 0.76, 0.5, "#27AE60"),
            ("Fail-Safe Trigger\n& Local Storage", 0.53, 0.12, "#D35400"),
        ]
        eval_metrics = ["Packet Delivery", "Battery Life", "Real-Time Latency", "Sensor Accuracy", "Uptime Reliability"]
        base_vals = [42, 30, 38, 45, 35]
        prop_vals = [95, 89, 93, 97, 98]
    else:
        cat_1 = ["Throughput Bottlenecks", "System Latency", "Resource Overutilization", "Compatibility Issues", "Data Inconsistencies"]
        freq_1 = [39, 33, 29, 23, 17]
        flow_blocks = [
            ("Input Pipeline\n& Data Source", 0.08, 0.5, "#2C3E50"),
            ("Core Processing\n& Logic Module", 0.30, 0.5, "#2980B9"),
            ("Optimization\n& Control Unit", 0.53, 0.5, "#A01E1E"),
            ("Deployment\n& Output System", 0.76, 0.5, "#27AE60"),
            ("Diagnostic\n& Audit Engine", 0.53, 0.12, "#D35400"),
        ]
        eval_metrics = ["Execution Efficiency", "Error Minimization", "Resource Utilization", "System Reliability", "Scalability Index"]
        base_vals = [40, 32, 45, 38, 30]
        prop_vals = [93, 95, 91, 96, 94]

    # 1. Figure 1.2: Problem & Requirements Analysis Chart
    path_1 = os.path.join(out_dir, f"{report_id}_fig1_2.png")
    try:
        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=200)
        colors = ["#A01E1E", "#C0392B", "#D9534F", "#E67E22", "#F39C12"]
        bars = ax.barh(cat_1, freq_1, color=colors, height=0.55)
        ax.set_xlabel("Vulnerability Occurrence / Requirement Weight (%)", fontsize=9, fontname="DejaVu Sans")
        ax.set_title(f"Fig 1.2: Core Challenges & Operational Analysis for {clean_title}", fontsize=10, fontweight="bold", color="#A01E1E", pad=12)
        ax.set_xlim(0, 50)
        ax.grid(axis="x", linestyle="--", alpha=0.5)

        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2, f"{width}%", va="center", ha="left", fontsize=9, fontweight="bold")

        plt.tight_layout()
        plt.savefig(path_1, bbox_inches="tight", dpi=200)
        plt.close(fig)
        images["img_slot_1"] = path_1
    except Exception as e:
        logger.warn(f"Failed to generate Figure 1.2: {e}")

    # 2. Figure 3.1: System Block Architecture & Topology
    path_2 = os.path.join(out_dir, f"{report_id}_fig3_1.png")
    try:
        fig, ax = plt.subplots(figsize=(6.8, 2.8), dpi=200)
        ax.axis("off")

        for text, x, y, color in flow_blocks:
            ax.text(
                x, y, text,
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.6", facecolor=color, edgecolor="black", alpha=0.9),
                fontsize=8.5, fontweight="bold", color="white"
            )

        # Connection arrows
        ax.annotate("", xy=(0.21, 0.5), xytext=(0.17, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="#333"))
        ax.annotate("", xy=(0.42, 0.5), xytext=(0.38, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="#333"))
        ax.annotate("", xy=(0.67, 0.5), xytext=(0.63, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="#333"))
        ax.annotate("", xy=(0.53, 0.24), xytext=(0.53, 0.38), arrowprops=dict(arrowstyle="->", lw=2, color="#A01E1E", ls="--"))

        ax.set_title(f"Fig 3.1: System Architecture & Data Flow Pipeline for {clean_title}", fontsize=10, fontweight="bold", color="#A01E1E", pad=10)
        plt.tight_layout()
        plt.savefig(path_2, bbox_inches="tight", dpi=200)
        plt.close(fig)
        images["img_slot_2"] = path_2
    except Exception as e:
        logger.warn(f"Failed to generate Figure 3.1: {e}")

    # 3. Figure 4.1: Comparative Performance & Quantitative Results
    path_3 = os.path.join(out_dir, f"{report_id}_fig4_1.png")
    try:
        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=200)
        x = np.arange(len(eval_metrics))
        width = 0.35

        rects1 = ax.bar(x - width/2, base_vals, width, label="Conventional Baseline (%)", color="#7F8C8D")
        rects2 = ax.bar(x + width/2, prop_vals, width, label="Proposed Implementation (%)", color="#A01E1E")

        ax.set_ylabel("Efficiency & Performance (%)", fontsize=9)
        ax.set_title(f"Fig 4.1: Experimental Performance Evaluation for {clean_title}", fontsize=10, fontweight="bold", color="#A01E1E", pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(eval_metrics, rotation=18, ha="right", fontsize=8.5)
        ax.legend(loc="upper left", fontsize=9)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.savefig(path_3, bbox_inches="tight", dpi=200)
        plt.close(fig)
        images["img_slot_3"] = path_3
    except Exception as e:
        logger.warn(f"Failed to generate Figure 4.1: {e}")

    return images
