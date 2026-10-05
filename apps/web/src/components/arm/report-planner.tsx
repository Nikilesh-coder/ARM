"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  Lock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  RotateCcw,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Search,
  BookOpen,
  FolderArchive,
  GraduationCap,
  Layers,
  ArrowRight,
  ThumbsUp,
  Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  apiClient,
  ReportPlanDTO,
  SectionPlanItemDTO,
  ProjectReadinessDTO,
  VerificationStatus,
  ConfidenceLevel
} from "@/lib/api-client";

interface ReportPlannerProps {
  projectId: string;
  onPlanApproved?: () => void;
}

export function ReportPlanner({ projectId, onPlanApproved }: ReportPlannerProps) {
  const [loading, setLoading] = useState(true);
  const [planning, setPlanning] = useState(false);
  const [approving, setApproving] = useState(false);
  const [plan, setPlan] = useState<ReportPlanDTO | null>(null);
  const [readiness, setReadiness] = useState<ProjectReadinessDTO | null>(null);
  const [agentStatus, setAgentStatus] = useState<string>("Ready");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg(null);

      const [read, existingPlan] = await Promise.all([
        apiClient.getProjectReadiness(projectId).catch(() => null),
        apiClient.getProjectReportPlan(projectId).catch(() => null),
      ]);

      setReadiness(read);
      setPlan(existingPlan);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load report plan.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGeneratePlan = async (force: boolean = false) => {
    try {
      setPlanning(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      setAgentStatus("ARM is analyzing locked college template structure...");
      await new Promise((r) => setTimeout(r, 400));

      setAgentStatus("ARM is grounding against verified project facts and evidence...");
      await new Promise((r) => setTimeout(r, 400));

      setAgentStatus("ARM is executing deterministic template constraint validation...");

      const newPlan = await apiClient.planProjectReport(projectId, { force });
      setPlan(newPlan);
      setAgentStatus("ARM Report Plan Verified.");
      setSuccessMsg("Structured report plan successfully generated and verified against template constraints.");
    } catch (err: any) {
      setErrorMsg(err.message || "Report planning failed.");
      setAgentStatus("Planning halted due to validation or configuration issue.");
    } finally {
      setPlanning(false);
    }
  };

  const handleApprovePlan = async () => {
    if (!plan) return;
    try {
      setApproving(true);
      setErrorMsg(null);
      const approved = await apiClient.approveProjectReportPlan(projectId, plan.plan_id);
      setPlan(approved);
      setSuccessMsg("Report plan approved by student. Ready for downstream report generation.");
      if (onPlanApproved) onPlanApproved();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to approve plan.");
    } finally {
      setApproving(false);
    }
  };

  const toggleSection = (secId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [secId]: !prev[secId],
    }));
  };

  const getStatusBadge = (status: VerificationStatus) => {
    switch (status) {
      case "READY":
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300">Ready</Badge>;
      case "PARTIALLY_VERIFIED":
        return <Badge className="bg-blue-100 text-blue-800 border-blue-300">Partially Grounded</Badge>;
      case "MISSING_INFORMATION":
        return <Badge className="bg-amber-100 text-amber-800 border-amber-300">Missing Information</Badge>;
      case "RESEARCH_REQUIRED":
        return <Badge className="bg-purple-100 text-purple-800 border-purple-300">Research Required</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        <Clock className="w-5 h-5 mr-2 animate-spin text-blue-600" />
        Loading AI Report Planner...
      </div>
    );
  }

  // Pre-requisite check: template must be locked
  const isTemplateLocked = readiness?.template_locked;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-xl shadow-sm">
        <div className="flex items-start gap-3">
          <div className="p-2.5 bg-blue-600/30 border border-blue-400/30 text-blue-300 rounded-lg shadow-sm">
            <Sparkles className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold">AI Report Planner</h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30">
                Stage 6
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Transforms locked template structure and student ground truth into an authoritative, section-by-section outline.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {plan ? (
            <Button
              onClick={() => handleGeneratePlan(true)}
              disabled={planning || !isTemplateLocked}
              variant="outline"
              size="sm"
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Re-plan Outline
            </Button>
          ) : (
            <Button
              onClick={() => handleGeneratePlan(false)}
              disabled={planning || !isTemplateLocked}
              size="sm"
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm"
            >
              <Sparkles className="w-4 h-4 mr-1.5" /> Generate Report Plan
            </Button>
          )}
        </div>
      </div>

      {/* Warnings & Pre-requisite Alerts */}
      {!isTemplateLocked && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-amber-900">
          <Lock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <strong>Stage 4 Prerequisite Required:</strong> The college report template for this project has not been locked.
            The AI Report Planner requires an immutable authoritative template structure to prevent inventing sections.
            <div className="mt-2">
              <Link href="/templates">
                <Button size="sm" variant="outline" className="text-xs border-amber-300 text-amber-900 bg-white">
                  Review &amp; Lock Template <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}

      {plan?.is_stale && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-blue-900">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed flex-1">
            <strong>Project Data Modified:</strong> Project information was updated since this report plan was generated.
            Click <strong>Re-plan Outline</strong> to align citations, methodology, and facts with the latest edits.
          </div>
          <Button
            size="sm"
            onClick={() => handleGeneratePlan(true)}
            className="text-xs bg-blue-600 hover:bg-blue-700 text-white"
          >
            Re-plan
          </Button>
        </div>
      )}

      {/* Notifications */}
      {successMsg && (
        <div className="flex items-center gap-2 p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center gap-2 p-3.5 bg-red-50 border border-red-200 text-red-800 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* Agent Progress State */}
      {planning && (
        <div className="p-4 bg-white border border-blue-200 rounded-xl shadow-xs space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-blue-700 uppercase tracking-wider">
            <Clock className="w-4 h-4 animate-spin" />
            Agent Planning in Progress
          </div>
          <p className="text-sm text-slate-700 font-medium">{agentStatus}</p>
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div className="bg-blue-600 h-1.5 rounded-full animate-pulse w-3/4"></div>
          </div>
        </div>
      )}

      {/* Main Report Plan Display */}
      {plan ? (
        <div className="space-y-6">
          {/* Summary Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3.5 text-center">
              <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
                Planned Sections
              </span>
              <span className="text-xl font-bold text-slate-900 mt-1 block">
                {plan.summary_metrics.total_sections}
              </span>
            </Card>

            <Card className="p-3.5 text-center">
              <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
                Grounded &amp; Ready
              </span>
              <span className="text-xl font-bold text-emerald-600 mt-1 block">
                {plan.summary_metrics.ready_sections}
              </span>
            </Card>

            <Card className="p-3.5 text-center">
              <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
                Missing Facts
              </span>
              <span className="text-xl font-bold text-amber-600 mt-1 block">
                {plan.summary_metrics.missing_info_sections}
              </span>
            </Card>

            <Card className="p-3.5 text-center">
              <span className="text-[11px] uppercase tracking-wider text-slate-500 block font-semibold">
                Research Required
              </span>
              <span className="text-xl font-bold text-purple-600 mt-1 block">
                {plan.summary_metrics.research_required_sections}
              </span>
            </Card>
          </div>

          {/* Plan Header Info */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-lg font-bold text-slate-900">{plan.title}</CardTitle>
                  <CardDescription className="text-xs text-slate-500 mt-0.5">
                    Target Pages: ~{plan.target_page_count} &nbsp;|&nbsp; Locked Template Schema v{plan.template_schema_version} &nbsp;|&nbsp;
                    AI Provider: {plan.planner_metadata.ai_provider} ({plan.planner_metadata.ai_model})
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {plan.is_approved ? (
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Plan Approved
                    </Badge>
                  ) : (
                    <Button
                      size="sm"
                      onClick={handleApprovePlan}
                      disabled={approving}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
                    >
                      <ThumbsUp className="w-3.5 h-3.5 mr-1" /> Approve Plan
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
                {plan.sections.map((sec, idx) => {
                  const isExpanded = expandedSections[sec.section_id] ?? (idx < 4);
                  return (
                    <div key={sec.section_id} className="bg-white">
                      {/* Section Header */}
                      <div
                        onClick={() => toggleSection(sec.section_id)}
                        className="p-4 flex items-center justify-between hover:bg-slate-50 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-xs font-mono font-bold text-slate-400 w-6">
                            {String(sec.order).padStart(2, "0")}
                          </span>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-bold text-slate-900 truncate">
                                {sec.title}
                              </h4>
                              {sec.required && (
                                <span className="text-[10px] text-slate-400 font-semibold uppercase">
                                  Mandatory
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-500 truncate max-w-xl mt-0.5">
                              {sec.purpose}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {getStatusBadge(sec.verification_status)}
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </div>

                      {/* Section Details (Expanded) */}
                      {isExpanded && (
                        <div className="px-4 pb-4 pt-1 bg-slate-50/70 border-t border-slate-100 text-xs space-y-3">
                          {/* Grounded Project Facts */}
                          {sec.project_fact_references.length > 0 && (
                            <div>
                              <span className="font-semibold text-slate-700 block mb-1">
                                Grounded Project Facts:
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {sec.project_fact_references.map((fact) => (
                                  <span
                                    key={fact}
                                    className="px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-700 rounded text-[11px] font-mono"
                                  >
                                    ✓ {fact}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Evidence References */}
                          {sec.evidence_references.length > 0 && (
                            <div>
                              <span className="font-semibold text-slate-700 block mb-1">
                                Mapped Evidence Files:
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {sec.evidence_references.map((ev) => (
                                  <span
                                    key={ev}
                                    className="px-2 py-0.5 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded text-[11px] font-mono flex items-center gap-1"
                                  >
                                    <FolderArchive className="w-3 h-3 text-emerald-600" /> {ev}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Missing Information Alerts */}
                          {sec.missing_information.length > 0 && (
                            <div className="p-2.5 bg-amber-50/80 border border-amber-200 rounded-md text-amber-900 space-y-1">
                              <span className="font-bold flex items-center gap-1 text-[11px]">
                                <AlertCircle className="w-3.5 h-3.5 text-amber-600" /> Missing Information (Must Not Be Invented):
                              </span>
                              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
                                {sec.missing_information.map((miss, mIdx) => (
                                  <li key={mIdx}>{miss}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Research Required Marker */}
                          {sec.research_required && (
                            <div className="p-2.5 bg-purple-50/80 border border-purple-200 rounded-md text-purple-900 space-y-1">
                              <span className="font-bold flex items-center gap-1 text-[11px]">
                                <BookOpen className="w-3.5 h-3.5 text-purple-600" /> External Research Required:
                              </span>
                              <p className="text-[11px] text-purple-800">
                                {sec.research_notes || "Requires external academic literature survey and citations."}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        /* Empty State */
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-3">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-800 text-base">No Report Plan Generated Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              The AI Report Planner will synthesize the Stage 4 locked template structure, Stage 5 academic facts,
              and Evidence Locker to produce a verified report outline with zero hallucinations.
            </p>
            {isTemplateLocked ? (
              <Button
                onClick={() => handleGeneratePlan(false)}
                disabled={planning}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
              >
                <Sparkles className="w-4 h-4 mr-1.5" /> Start Report Planning
              </Button>
            ) : (
              <p className="text-xs text-amber-600 font-medium">
                Please complete and lock the college report template to enable planning.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
