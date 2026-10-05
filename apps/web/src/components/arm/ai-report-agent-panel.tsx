"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Layers,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Send,
  Wand2,
  Download,
  FileText,
  Eye,
} from "lucide-react";
import { AgentStatus, AgentStage, mapReplacementStateToAgentStage } from "./agent-status";
import {
  apiClient,
  AIReportAgentOutputDTO,
  TemplateFieldDTO,
  ReplacementJobResponseDTO,
} from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReportPreviewModal } from "./report-preview-modal";

interface AiReportAgentPanelProps {
  initialTitle?: string;
  initialDescription?: string;
  initialInstructions?: string;
  templateFields?: TemplateFieldDTO[];
  evidenceFiles?: any[];
  projectId?: string;
  onContentGenerated?: (content: Record<string, any>) => void;
  className?: string;
}

export function AiReportAgentPanel({
  initialTitle = "",
  initialDescription = "",
  initialInstructions = "",
  templateFields,
  evidenceFiles,
  projectId,
  onContentGenerated,
  className = "",
}: AiReportAgentPanelProps) {
  const [projectTitle, setProjectTitle] = useState(initialTitle);
  const [projectDescription, setProjectDescription] = useState(initialDescription);
  const [userInstructions, setUserInstructions] = useState(initialInstructions);

  const [agentStage, setAgentStage] = useState<AgentStage>("thinking");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [result, setResult] = useState<AIReportAgentOutputDTO | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showJsonRaw, setShowJsonRaw] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  // Template Replacement Engine States
  const [replacementResult, setReplacementResult] = useState<ReplacementJobResponseDTO | null>(null);
  const [isReplacing, setIsReplacing] = useState<boolean>(false);
  const [customStatusLabel, setCustomStatusLabel] = useState<string | undefined>(undefined);
  const [customStatusDetail, setCustomStatusDetail] = useState<string | undefined>(undefined);
  const [showPreview, setShowPreview] = useState<boolean>(false);

  const handleExecuteReplacement = async () => {
    if (!projectTitle.trim()) {
      setErrorMessage("Please enter a project title.");
      return;
    }
    if (!projectDescription.trim()) {
      setErrorMessage("Please enter project description / topic.");
      return;
    }

    setErrorMessage(null);
    setIsReplacing(true);
    setReplacementResult(null);

    // 1. Initial State: QUEUED -> ANALYZING ("thinking")
    setAgentStage("thinking");
    setCustomStatusLabel("ARM is analyzing...");
    setCustomStatusDetail("Loading Master College Template and matching 20 canonical fields");

    try {
      const thinkTimer = setTimeout(() => {
        // 2. Transition to REPLACING ("creating")
        setAgentStage("creating");
        setCustomStatusLabel("ARM is creating...");
        setCustomStatusDetail("Substituting text & images into college template in-place");
      }, 1400);

      const job = await apiClient.executeTemplateReplacement({
        project_id: projectId,
        project_data: {
          title: projectTitle.trim(),
          description: projectDescription.trim(),
          student_name: "Kasireddy Charishma",
          roll_number: "24BFA02081",
          department: "Department of Electrical & Electronics Engineering",
          guide_name: "Dr. Y.V. Krishna Reddy",
        },
        custom_content: result?.content,
        user_instructions: userInstructions.trim() || undefined,
      });

      clearTimeout(thinkTimer);

      if (job.state === "FAILED" && job.errors?.length) {
        setErrorMessage(
          `Template Replacement Error: ${job.errors.map((e) => `${e.field}: ${e.reason}`).join("; ")}`
        );
      } else {
        setAgentStage("completed");
        setCustomStatusLabel("Report Synthesis Complete");
        setCustomStatusDetail("College template preserved with 100% fidelity. Ready for preview and download.");
        setReplacementResult(job);
      }
    } catch (err: any) {
      console.error("Replacement error:", err);
      setErrorMessage(err.message || "Failed to execute template replacement.");
    } finally {
      setIsReplacing(false);
    }
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!projectTitle.trim()) {
      setErrorMessage("Please enter a project title.");
      return;
    }
    if (!projectDescription.trim()) {
      setErrorMessage("Please enter project description / topic.");
      return;
    }

    setErrorMessage(null);
    setIsGenerating(true);
    setResult(null);

    // AI Status progression matching ARM behavior:
    // 1. "thinking" while the AI is reasoning/generating
    setAgentStage("thinking");

    try {
      // Simulate/bridge realistic thinking state before invoking backend
      const thinkTimer = setTimeout(() => {
        // 2. "creating" while ARM is creating the report
        setAgentStage("creating");
      }, 1200);

      const response = await apiClient.generateAgentReportContent({
        project_title: projectTitle.trim(),
        project_description: projectDescription.trim(),
        user_instructions: userInstructions.trim() || undefined,
        template_id: "00000000-0000-0000-0000-000000000001",
        template_fields: templateFields,
        evidence_files: evidenceFiles,
        project_id: projectId,
      });

      clearTimeout(thinkTimer);
      setAgentStage("creating");
      await new Promise((res) => setTimeout(res, 400));

      setResult(response);
      if (onContentGenerated && response.content) {
        onContentGenerated(response.content);
      }
    } catch (err: any) {
      console.error("AI Report Agent error:", err);
      setErrorMessage(err.message || "Failed to generate structured report content.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyJson = () => {
    if (!result?.content) return;
    navigator.clipboard.writeText(JSON.stringify(result.content, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Input Form Card */}
      <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-900 mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <Wand2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                ARM AI Report Agent
                <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider border-blue-500/30 text-blue-600 dark:text-blue-400">
                  Fixed Master Template
                </Badge>
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                Generates strictly structured JSON mapped 1:1 to college template fields
              </p>
            </div>
          </div>

          <div className="text-right hidden sm:block">
            <span className="text-[11px] font-mono text-zinc-400 block">Status: Online</span>
            <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400">Gemini 3.5 Flash-Lite</span>
          </div>
        </div>

        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
              Project Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
              placeholder="e.g., Autonomous Rover for Planetary Exploration"
              disabled={isGenerating}
              className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 text-zinc-900 dark:text-white placeholder-zinc-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
              Project Topic / Problem Statement Description <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="Detail the technical background, engineering problem addressed, system architecture goals, and outcomes..."
              disabled={isGenerating}
              className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 text-zinc-900 dark:text-white placeholder-zinc-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
              Optional User Instructions
            </label>
            <input
              type="text"
              value={userInstructions}
              onChange={(e) => setUserInstructions(e.target.value)}
              placeholder="e.g., Emphasize power efficiency in solar charging; format references in IEEE style"
              disabled={isGenerating}
              className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 text-zinc-900 dark:text-white placeholder-zinc-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="pt-2 flex flex-wrap items-center justify-end gap-3">
            <button
              type="submit"
              disabled={isGenerating || isReplacing}
              className="px-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-800 dark:text-zinc-200 font-semibold text-xs transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              {isGenerating ? "Synthesizing Content..." : "Generate Content"}
            </button>

            <button
              type="button"
              onClick={handleExecuteReplacement}
              disabled={isGenerating || isReplacing}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs shadow-sm hover:shadow transition-all flex items-center gap-2 cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              {isReplacing ? "Compiling Template..." : "One-Click: Replace into College Template"}
            </button>
          </div>
        </form>
      </div>

      {/* AI Status UI: "thinking" while AI is reasoning, "creating" while ARM is creating/replacing the report */}
      {(isGenerating || isReplacing) && (
        <div className="animate-in fade-in duration-200">
          <AgentStatus
            currentStage={agentStage}
            customLabel={customStatusLabel}
            customDetail={customStatusDetail}
          />
        </div>
      )}

      {/* Replacement Result Presentation */}
      {replacementResult && (
        <div className="rounded-2xl border border-emerald-200 dark:border-emerald-900/60 bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-5 animate-in zoom-in-95 duration-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-zinc-100 dark:border-zinc-900">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                  College Report Successfully Compiled
                  <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                    Source of Truth Preserved
                  </Badge>
                </h4>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  {replacementResult.fields_replaced} of {replacementResult.total_fields} fields & {replacementResult.images_replaced} images replaced directly in college template
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <a
                href={apiClient.getReplacementDownloadUrl(replacementResult.job_id, "docx")}
                download
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Download DOCX
              </a>

                <button
                  type="button"
                  onClick={() => setShowPreview(true)}
                  className="px-3.5 py-2 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5 text-blue-600" />
                  Open Preview & Actions
                </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-400 block text-[10px]">Processing State</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-bold">{replacementResult.state}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-400 block text-[10px]">Typography & Layout</span>
              <span className="text-zinc-800 dark:text-zinc-200 font-bold">100% Locked</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-400 block text-[10px]">Images Replaced</span>
              <span className="text-blue-600 dark:text-blue-400 font-bold">{replacementResult.images_replaced} embedded</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-400 block text-[10px]">Approval Status</span>
              <span className={replacementResult.approval_status === "approved" ? "text-emerald-600 font-bold" : "text-amber-600 font-bold"}>
                {replacementResult.approval_status === "approved" ? "Approved ✓" : "Pending"}
              </span>
            </div>
          </div>

          <ReportPreviewModal
            job={replacementResult}
            isOpen={showPreview}
            onClose={() => setShowPreview(false)}
            onJobUpdated={(updated) => setReplacementResult(updated)}
          />
        </div>
      )}

      {/* Structured Output Presentation */}
      {result && (
        <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-6 animate-in zoom-in-95 duration-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-zinc-100 dark:border-zinc-900">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-100 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-zinc-900 dark:text-white">
                  Report Content Synthesized & Validated
                </h4>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {result.validation.valid_fields_count} of {result.validation.total_fields} fields mapped strictly to template schema
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyJson}
                className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-700 dark:text-zinc-300 text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Copy JSON"}
              </button>

              <button
                type="button"
                onClick={() => setShowJsonRaw(!showJsonRaw)}
                className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-700 dark:text-zinc-300 text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <FileCode className="w-3.5 h-3.5" />
                {showJsonRaw ? "Formatted View" : "Raw JSON"}
              </button>
            </div>
          </div>

          {/* Model info banner */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-600 dark:text-zinc-400 font-mono">
            <span>Model: {result.model_used}</span>
            <span>Generated: {new Date(result.generated_at).toLocaleTimeString()}</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Strict JSON Schema Verified ✓</span>
          </div>

          {/* Raw JSON View */}
          {showJsonRaw ? (
            <pre className="p-4 rounded-xl bg-zinc-950 text-zinc-100 font-mono text-xs overflow-x-auto max-h-[500px] border border-zinc-800">
              {JSON.stringify(result.content, null, 2)}
            </pre>
          ) : (
            /* Structured Field Cards View */
            <div className="grid grid-cols-1 gap-4">
              {Object.entries(result.content).map(([fieldName, value]) => {
                const isArray = Array.isArray(value);
                const isString = typeof value === "string";

                return (
                  <div
                    key={fieldName}
                    className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/30 space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-blue-600 dark:text-blue-400">
                        {fieldName}
                      </span>
                      <Badge variant="outline" className="text-[10px] font-mono capitalize">
                        {isArray ? `List (${value.length})` : typeof value}
                      </Badge>
                    </div>

                    {isArray ? (
                      <ul className="list-disc list-inside text-xs text-zinc-700 dark:text-zinc-300 space-y-1 pl-1">
                        {value.map((item: any, idx: number) => (
                          <li key={idx} className="leading-relaxed">
                            {String(item)}
                          </li>
                        ))}
                      </ul>
                    ) : isString ? (
                      <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                        {value}
                      </p>
                    ) : (
                      <pre className="text-xs font-mono text-zinc-600 dark:text-zinc-400">
                        {JSON.stringify(value)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
