"use client";

import React, { useState, useEffect } from "react";
import { Brain, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type AgentStage =
  | "thinking"
  | "analyzing"
  | "reading_template"
  | "reviewing_evidence"
  | "planning"
  | "researching"
  | "creating"
  | "formatting"
  | "validating"
  | "finalizing"
  | "completed";

export interface AgentStageConfig {
  stage: AgentStage;
  label: string;
  detail: string;
}

export const AGENT_STAGES: AgentStageConfig[] = [
  {
    stage: "thinking",
    label: "ARM is thinking...",
    detail: "Parsing query intents and extracting document requirements",
  },
  {
    stage: "analyzing",
    label: "ARM is analyzing your project...",
    detail: "Evaluating domain scope, technical terminology, and parameters",
  },
  {
    stage: "reading_template",
    label: "ARM is analyzing your college template...",
    detail: "Extracting OpenXML styles, margins, typography, and heading policies",
  },
  {
    stage: "reviewing_evidence",
    label: "ARM is reviewing your uploaded evidence...",
    detail: "Correlating code commits, data outputs, and architecture assets",
  },
  {
    stage: "planning",
    label: "ARM is creating your report plan...",
    detail: "Assembling structured chapter sequence and word-count budgets",
  },
  {
    stage: "researching",
    label: "ARM is researching relevant information...",
    detail: "Formulating academic citations and literature background references",
  },
  {
    stage: "creating",
    label: "ARM is creating...",
    detail: "Drafting technical prose, methodology equations, and analysis sections",
  },
  {
    stage: "formatting",
    label: "ARM is applying your college format...",
    detail: "Executing deterministic OpenXML layout, spacing, and table borders",
  },
  {
    stage: "validating",
    label: "ARM is checking your report...",
    detail: "Verifying section completeness, heading hierarchy, and citation integrity",
  },
  {
    stage: "finalizing",
    label: "ARM is preparing your document...",
    detail: "Building clean PDF and DOCX binaries ready for inspection",
  },
];

export interface AgentStatusProps {
  currentStage: AgentStage;
  progressPercent?: number;
  className?: string;
  onCancel?: () => void;
  customLabel?: string;
  customDetail?: string;
}

export function mapReplacementStateToAgentStage(
  state: string,
  armUiState?: "thinking" | "creating" | "completed"
): { stage: AgentStage; label: string; detail: string } {
  switch (state) {
    case "QUEUED":
      return {
        stage: "thinking",
        label: "ARM is queued...",
        detail: "Initializing master template replacement pipeline",
      };
    case "ANALYZING":
      return {
        stage: "analyzing",
        label: "ARM is analyzing...",
        detail: "Loading Master College Template and matching 20 canonical fields",
      };
    case "GENERATING":
      return {
        stage: "thinking",
        label: "ARM is thinking...",
        detail: "Synthesizing structured academic matter and acquiring image assets",
      };
    case "REPLACING":
      return {
        stage: "creating",
        label: "ARM is creating...",
        detail: "Substituting text & images in college template without altering formatting",
      };
    case "VALIDATING":
      return {
        stage: "validating",
        label: "ARM is checking your report...",
        detail: "Auditing OpenXML layout, confirming zero unresolved placeholders, building PDF",
      };
    case "COMPLETED":
      return {
        stage: "completed",
        label: "Report Synthesis Complete",
        detail: "College template preserved with 100% fidelity. Ready for preview and download.",
      };
    case "FAILED":
      return {
        stage: "thinking",
        label: "Replacement Failed",
        detail: "Safety error detected during template replacement.",
      };
    default:
      return {
        stage: armUiState === "creating" ? "creating" : "thinking",
        label: armUiState === "creating" ? "ARM is creating..." : "ARM is thinking...",
        detail: "Processing academic report...",
      };
  }
}

export function AgentStatus({
  currentStage,
  progressPercent,
  className,
  onCancel,
  customLabel,
  customDetail,
}: AgentStatusProps) {
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setIsReducedMotion(mq.matches);
  }, []);

  const currentStageIndex = AGENT_STAGES.findIndex((s) => s.stage === currentStage);
  const activeConfig =
    AGENT_STAGES.find((s) => s.stage === currentStage) || AGENT_STAGES[0];

  const calculatedProgress =
    progressPercent !== undefined
      ? progressPercent
      : Math.round(((Math.max(0, currentStageIndex) + 1) / AGENT_STAGES.length) * 100);

  const isThinking = currentStage === "thinking";
  const isCreating = currentStage === "creating";

  return (
    <div
      className={cn(
        "w-full p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/90 text-zinc-900 dark:text-zinc-100 shadow-xl backdrop-blur-md",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3.5">
          {/* AI Brain Indicator as specified in Section 10 */}
          <div
            className={cn(
              "relative flex items-center justify-center w-11 h-11 rounded-xl bg-zinc-100 dark:bg-zinc-900 border transition-all duration-300",
              isThinking
                ? "border-blue-500/60 shadow-[0_0_15px_rgba(59,130,246,0.35)]"
                : isCreating
                ? "border-indigo-500/60 shadow-[0_0_15px_rgba(99,102,241,0.35)]"
                : "border-zinc-300 dark:border-zinc-750"
            )}
          >
            <Brain
              className={cn(
                "w-6 h-6 text-zinc-900 dark:text-white transition-all",
                !isReducedMotion && isThinking && "animate-pulse scale-105",
                !isReducedMotion && isCreating && "animate-bounce scale-105 text-indigo-600 dark:text-indigo-300",
                !isReducedMotion && !isThinking && !isCreating && "animate-pulse"
              )}
            />
            {/* Subtle glow / ping dot */}
            {!isReducedMotion && (
              <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
              </span>
            )}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">
                {customLabel || activeConfig.label}
              </h4>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 leading-normal">
              {customDetail || activeConfig.detail}
            </p>
          </div>
        </div>

        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300 font-mono underline underline-offset-4"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress Track */}
      <div className="mt-4 space-y-1.5">
        <div className="flex justify-between text-[10px] font-mono text-zinc-500">
          <span>Stage {Math.max(1, currentStageIndex + 1)} of {AGENT_STAGES.length}</span>
          <span>{calculatedProgress}%</span>
        </div>
        <div className="w-full h-1 bg-zinc-200 dark:bg-zinc-900 rounded-full overflow-hidden border border-zinc-300 dark:border-zinc-850">
          <div
            className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-zinc-900 dark:to-white transition-all duration-300 rounded-full"
            style={{ width: `${calculatedProgress}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export const ArmAgentStatus = AgentStatus;
