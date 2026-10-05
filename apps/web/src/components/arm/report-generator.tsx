"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Layers,
  ChevronRight,
  BookOpen,
  RefreshCw,
  Eye,
  CheckSquare,
  AlertCircle,
  FileCheck2,
  BookmarkCheck,
  ImageIcon,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  apiClient,
  GeneratedReportDTO,
  SectionGenerationOutputDTO,
  ContentBlockDTO,
  ReportPlanDTO,
  GroundingStatus,
  ReplacementJobResponseDTO,
} from "@/lib/api-client";
import { AgentStatus, AgentStage } from "./agent-status";
import { ReportPreviewModal } from "./report-preview-modal";

interface ReportGeneratorProps {
  projectId: string;
}

export function ReportGenerator({ projectId }: ReportGeneratorProps) {
  const [report, setReport] = useState<GeneratedReportDTO | null>(null);
  const [plan, setPlan] = useState<ReportPlanDTO | null>(null);
  const [agentStage, setAgentStage] = useState<AgentStage>("thinking");
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedSectionIdx, setSelectedSectionIdx] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [currentStepText, setCurrentStepText] = useState<string>("");
  const [progressPct, setProgressPct] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isReplacing, setIsReplacing] = useState<boolean>(false);
  const [replacementJob, setReplacementJob] = useState<ReplacementJobResponseDTO | null>(null);
  const [showReplacementPreview, setShowReplacementPreview] = useState<boolean>(false);

  const fetchState = useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setErrorMsg(null);

      // 1. Fetch Plan to check if approved
      try {
        const p = await apiClient.getProjectReportPlan(projectId);
        setPlan(p);
      } catch {
        setPlan(null);
      }

      // 2. Fetch Latest Report
      try {
        const r = await apiClient.getLatestProjectReport(projectId);
        setReport(r);
      } catch {
        setReport(null);
      }

      // 3. Fetch Versions
      try {
        const vList = await apiClient.getProjectReportVersions(projectId);
        setVersions(vList || []);
      } catch {
        setVersions([]);
      }
    } catch (err: any) {
      console.error("Error fetching report generation state:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  const handleGenerate = async (force: boolean = false) => {
    if (!projectId) return;
    setGenerating(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setAgentStage("thinking");
    setCurrentStepText("ARM is thinking... Parsing query intents and extracting requirements");
    setProgressPct(20);

    const thinkTimer = setTimeout(() => {
      setAgentStage("creating");
      setCurrentStepText("ARM is creating... Drafting technical prose and methodology sections");
      setProgressPct(65);
    }, 1400);

    try {
      const generated = await apiClient.generateProjectReport(projectId, { force });
      clearTimeout(thinkTimer);
      setAgentStage("creating");
      setReport(generated);
      setSelectedSectionIdx(0);
      setSuccessMsg(`Report Draft Version ${generated.version_number} generated successfully with ${generated.sections.length} sections!`);
      setProgressPct(100);

      // Refresh versions
      try {
        const vList = await apiClient.getProjectReportVersions(projectId);
        setVersions(vList || []);
      } catch {}
    } catch (err: any) {
      clearTimeout(thinkTimer);
      console.error("Generation error:", err);
      setErrorMsg(err.message || "Failed to generate report draft.");
    } finally {
      setGenerating(false);
    }
  };

  const handleExecuteTemplateReplacement = async () => {
    if (!projectId) return;
    setIsReplacing(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setReplacementJob(null);
    setAgentStage("thinking");
    setCurrentStepText("ARM is thinking... Loading Master College Template");
    setProgressPct(20);

    const thinkTimer = setTimeout(() => {
      setAgentStage("creating");
      setCurrentStepText("ARM is creating... Substituting text & images in college template");
      setProgressPct(70);
    }, 1500);

    try {
      const job = await apiClient.executeTemplateReplacement({
        project_id: projectId,
      });
      clearTimeout(thinkTimer);

      if (job.state === "FAILED" && job.errors?.length) {
        setErrorMsg(
          `Template Replacement Error: ${job.errors.map((e) => `${e.field}: ${e.reason}`).join("; ")}`
        );
      } else {
        setAgentStage("completed");
        setSuccessMsg(
          "College Template Replacement Complete! Original layout, fonts, colors, and margins 100% preserved."
        );
        setProgressPct(100);
        setReplacementJob(job);
      }
    } catch (err: any) {
      clearTimeout(thinkTimer);
      console.error("Replacement error:", err);
      setErrorMsg(err.message || "Failed to execute template replacement.");
    } finally {
      setIsReplacing(false);
    }
  };

  const handleSelectVersion = async (vNum: number) => {
    try {
      setLoading(true);
      const rep = await apiClient.getProjectReportVersion(projectId, vNum);
      setReport(rep);
      setSelectedSectionIdx(0);
    } catch (err: any) {
      setErrorMsg(`Failed to load version ${vNum}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getGroundingBadge = (status: GroundingStatus) => {
    switch (status) {
      case "grounded":
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold">Grounded</Badge>;
      case "partially_grounded":
        return <Badge className="bg-amber-100 text-amber-800 border-amber-300 font-semibold">Partially Grounded</Badge>;
      case "requires_review":
        return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300 font-semibold">Requires Review</Badge>;
      case "missing_information":
        return <Badge className="bg-purple-100 text-purple-800 border-purple-300 font-semibold">Missing Info Flagged</Badge>;
      case "validation_failed":
        return <Badge className="bg-rose-100 text-rose-800 border-rose-300 font-semibold">Validation Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="p-8 bg-white border border-slate-200 rounded-xl text-center text-slate-500 text-sm flex items-center justify-center space-x-2">
        <Clock className="w-4 h-4 animate-spin text-indigo-600" />
        <span>Loading report generation state...</span>
      </div>
    );
  }

  const isPlanApproved = plan?.is_approved === true;
  const isPlanStale = plan?.is_stale === true;
  const activeSection: SectionGenerationOutputDTO | undefined = report?.sections?.[selectedSectionIdx];

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <Card className="border-slate-200 shadow-xs">
        <CardHeader className="pb-3 border-b border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <CardTitle className="text-lg font-bold text-slate-900">
                  Stage 7: Section-by-Section Report Generation
                </CardTitle>
                <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 font-mono text-[10px]">
                  Gemini Flash-Lite
                </Badge>
              </div>
              <CardDescription className="text-xs text-slate-500 mt-1">
                Grounded in Locked College Template + Approved Plan + Project Facts + Evidence Locker.
              </CardDescription>
            </div>

            <div className="flex items-center space-x-2">
              {versions.length > 1 && (
                <div className="flex items-center space-x-1.5 text-xs text-slate-600">
                  <span className="font-semibold">Version:</span>
                  <select
                    value={report?.version_number || 1}
                    onChange={(e) => handleSelectVersion(Number(e.target.value))}
                    className="px-2 py-1 border border-slate-200 rounded bg-white text-xs font-semibold focus:outline-none"
                  >
                    {versions.map((v) => (
                      <option key={v.version_number} value={v.version_number}>
                        v{v.version_number}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <Button
                onClick={() => handleGenerate(report !== null)}
                disabled={generating || isReplacing || !isPlanApproved || isPlanStale}
                variant="primary"
                size="sm"
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {generating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Generating Draft...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                    {report ? "Regenerate Draft" : "Generate Report Draft"}
                  </>
                )}
              </Button>

              <Button
                onClick={handleExecuteTemplateReplacement}
                disabled={generating || isReplacing}
                variant="primary"
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                {isReplacing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Compiling Template...
                  </>
                ) : (
                  <>
                    <FileCheck2 className="w-3.5 h-3.5 mr-1.5" />
                    One-Click: Replace into College Template
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-4 space-y-4">
          {/* Status banners */}
          {!isPlanApproved && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start space-x-2 text-xs text-amber-900">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Plan Approval Required:</span> The Stage 6 Report Plan must be approved before generating report sections. Please approve the plan above.
              </div>
            </div>
          )}

          {isPlanStale && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start space-x-2 text-xs text-rose-900">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Stale Plan Warning:</span> Project details or evidence have changed since the report plan was approved. Please regenerate and re-approve the plan.
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start space-x-2 text-xs text-rose-900">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Generation Error:</span> {errorMsg}
              </div>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start space-x-2 text-xs text-emerald-900">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>{successMsg}</div>
            </div>
          )}

          {/* Progress Indicator with Section 10 ARM Brain Visual */}
          {(generating || isReplacing) && (
            <div className="py-2 animate-in fade-in duration-200">
              <AgentStatus
                currentStage={agentStage}
                progressPercent={progressPct}
                customLabel={isReplacing ? (agentStage === "creating" ? "ARM is creating..." : "ARM is thinking...") : undefined}
                customDetail={currentStepText}
              />
            </div>
          )}

          {/* Replacement Result Presentation */}
          {replacementJob && (
            <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/50 space-y-3 animate-in zoom-in-95 duration-200">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-sm">
                    ✓
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      College Report Generated via In-Place Template Replacement
                    </h4>
                    <p className="text-xs text-slate-600">
                      {replacementJob.fields_replaced} fields & {replacementJob.images_replaced} images replaced • College layout, fonts, colors, and margins strictly preserved.
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <a
                    href={apiClient.getReplacementDownloadUrl(replacementJob.job_id, "docx")}
                    download
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs flex items-center space-x-1"
                  >
                    <Download className="w-3.5 h-3.5 mr-1" />
                    Download DOCX
                  </a>

                  <Button
                    onClick={() => setShowReplacementPreview(true)}
                    variant="outline"
                    size="sm"
                    className="text-xs bg-white text-indigo-700 border-indigo-200 hover:bg-indigo-50"
                  >
                    <Eye className="w-3.5 h-3.5 mr-1" />
                    Open Report Preview & Approval
                  </Button>
                </div>
              </div>

              <ReportPreviewModal
                job={replacementJob}
                isOpen={showReplacementPreview}
                onClose={() => setShowReplacementPreview(false)}
                onJobUpdated={(updated) => setReplacementJob(updated)}
              />
            </div>
          )}

          {/* Report Summary Cards */}
          {report && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[11px] text-slate-500 font-medium block">Report Title</span>
                <span className="text-xs font-bold text-slate-900 block truncate mt-0.5" title={report.title}>
                  {report.title}
                </span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[11px] text-slate-500 font-medium block">Draft Version</span>
                <span className="text-xs font-bold text-indigo-700 block mt-0.5">
                  Version {report.version_number}
                </span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[11px] text-slate-500 font-medium block">Total Words</span>
                <span className="text-xs font-bold text-slate-900 block mt-0.5">
                  {report.total_word_count.toLocaleString()} words
                </span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[11px] text-slate-500 font-medium block">Overall Grounding</span>
                <div className="mt-1">{getGroundingBadge(report.overall_grounding)}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Draft Section Viewer */}
      {report && report.sections.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Section Navigation Sidebar */}
          <div className="lg:col-span-4 space-y-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 px-1">
              Generated Sections ({report.sections.length})
            </div>
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 max-h-[600px] overflow-y-auto shadow-xs">
              {report.sections.map((sec, idx) => (
                <button
                  key={sec.section_id || idx}
                  onClick={() => setSelectedSectionIdx(idx)}
                  className={`w-full text-left p-3 text-xs transition flex items-start justify-between gap-2 ${
                    selectedSectionIdx === idx
                      ? "bg-indigo-50/80 border-l-4 border-indigo-600 text-indigo-950 font-semibold"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="flex items-start space-x-2 min-w-0">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {sec.section_order || idx + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate font-semibold">{sec.section_title}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {sec.word_count} words
                        {sec.missing_information.length > 0 && (
                          <span className="text-purple-600 font-medium ml-1">
                            &middot; {sec.missing_information.length} missing
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {getGroundingBadge(sec.grounding_status)}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Section Content Pane */}
          <div className="lg:col-span-8">
            {activeSection ? (
              <Card className="border-slate-200 shadow-xs">
                <CardHeader className="pb-3 border-b border-slate-100">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="text-xs font-semibold text-slate-500">
                        Section {activeSection.section_order} of {report.sections.length}
                      </div>
                      <CardTitle className="text-lg font-bold text-slate-900 mt-0.5">
                        {activeSection.section_title}
                      </CardTitle>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-slate-500">{activeSection.word_count} words</span>
                      {getGroundingBadge(activeSection.grounding_status)}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-4 space-y-4">
                  {/* Missing information alerts */}
                  {activeSection.missing_information.length > 0 && (
                    <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg space-y-1">
                      <div className="text-xs font-bold text-purple-900 flex items-center">
                        <Info className="w-3.5 h-3.5 mr-1 text-purple-600" />
                        Missing Information Callout (Zero Hallucination Guarantee)
                      </div>
                      <ul className="text-xs text-purple-800 list-disc list-inside space-y-0.5 pl-1">
                        {activeSection.missing_information.map((mi, mIdx) => (
                          <li key={mIdx}>
                            <span className="font-semibold">{mi.field}:</span> {mi.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Non-blocking warnings */}
                  {activeSection.warnings.length > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1">
                      <div className="text-xs font-bold text-amber-900 flex items-center">
                        <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
                        Section Warnings
                      </div>
                      <ul className="text-xs text-amber-800 list-disc list-inside space-y-0.5 pl-1">
                        {activeSection.warnings.map((w, wIdx) => (
                          <li key={wIdx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Research Marker Alert */}
                  {activeSection.research_marker_preserved && (
                    <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-center space-x-2">
                      <BookOpen className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      <span>
                        <b>Academic Research Marker Preserved:</b> External literature review and verified citations are deferred to later research stages.
                      </span>
                    </div>
                  )}

                  {/* Visual Requirement Alert */}
                  {activeSection.visual_requirements && activeSection.visual_requirements.length > 0 && (
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 space-y-1">
                      <div className="font-bold flex items-center text-slate-900">
                        <ImageIcon className="w-3.5 h-3.5 mr-1 text-slate-600" />
                        Visual Asset Requirements (Deferred to Visual Stage)
                      </div>
                      {activeSection.visual_requirements.map((vr, vIdx) => (
                        <div key={vIdx} className="text-[11px] text-slate-600 pl-4">
                          &bull; <b>{vr.visual_type}:</b> {vr.description} (status: {vr.status})
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Rendered Academic Content Blocks */}
                  <div className="pt-2 space-y-4 font-serif text-slate-800 leading-relaxed text-sm bg-slate-50/40 p-4 rounded-lg border border-slate-100">
                    {activeSection.content_blocks.map((block: ContentBlockDTO, bIdx: number) => {
                      switch (block.block_type) {
                        case "heading":
                          return (
                            <h3
                              key={bIdx}
                              className="font-sans font-bold text-slate-900 text-base border-b border-slate-200 pb-1 mt-3"
                            >
                              {block.text}
                            </h3>
                          );

                        case "paragraph":
                          return (
                            <p key={bIdx} className="text-justify text-slate-800">
                              {block.text}
                              {block.source_evidence_ids && block.source_evidence_ids.length > 0 && (
                                <span className="font-sans text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-mono ml-2 inline-block">
                                  [Evidence: {block.source_evidence_ids.join(", ")}]
                                </span>
                              )}
                            </p>
                          );

                        case "bullet_list":
                          return (
                            <div key={bIdx} className="space-y-1">
                              {block.text && <p className="font-sans font-semibold text-xs text-slate-700">{block.text}</p>}
                              <ul className="list-disc list-inside space-y-1 text-xs text-slate-700 pl-2 font-sans">
                                {block.items?.map((item, iIdx) => (
                                  <li key={iIdx}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          );

                        case "numbered_list":
                          return (
                            <div key={bIdx} className="space-y-1">
                              {block.text && <p className="font-sans font-semibold text-xs text-slate-700">{block.text}</p>}
                              <ol className="list-decimal list-inside space-y-1 text-xs text-slate-700 pl-2 font-sans">
                                {block.items?.map((item, iIdx) => (
                                  <li key={iIdx}>{item}</li>
                                ))}
                              </ol>
                            </div>
                          );

                        case "table":
                          return (
                            <div key={bIdx} className="overflow-x-auto my-2 font-sans">
                              {block.text && <p className="text-xs font-semibold text-slate-700 mb-1">{block.text}</p>}
                              <table className="min-w-full text-xs border border-slate-300">
                                {block.headers && (
                                  <thead className="bg-slate-100 font-bold">
                                    <tr>
                                      {block.headers.map((h, hIdx) => (
                                        <th key={hIdx} className="border border-slate-300 px-2 py-1 text-left">
                                          {h}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                )}
                                <tbody>
                                  {block.rows?.map((row, rIdx) => (
                                    <tr key={rIdx} className={rIdx % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                                      {row.map((cell, cIdx) => (
                                        <td key={cIdx} className="border border-slate-300 px-2 py-1">
                                          {cell}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          );

                        case "quote":
                          return (
                            <blockquote
                              key={bIdx}
                              className="border-l-4 border-indigo-300 pl-3 italic text-xs text-slate-600 my-2"
                            >
                              {block.text}
                            </blockquote>
                          );

                        case "note":
                          return (
                            <div key={bIdx} className="p-2.5 bg-slate-100 rounded text-xs text-slate-700 font-sans my-2">
                              {block.text}
                            </div>
                          );

                        default:
                          return (
                            <p key={bIdx} className="text-xs text-slate-700">
                              {block.text}
                            </p>
                          );
                      }
                    })}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="p-8 text-center text-slate-400 text-sm bg-white rounded-xl border border-slate-200">
                Select a section to inspect its generated academic content draft.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
