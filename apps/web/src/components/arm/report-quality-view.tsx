"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
  FileCheck,
  ChevronDown,
  ChevronRight,
  Info,
  Layers,
  Lock,
  FileText
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  apiClient,
  ReportQualityResultDTO,
  QualityGateStatus,
  ValidationIssueDTO,
  ValidationCheckDTO
} from "@/lib/api-client";

interface ReportQualityViewProps {
  projectId: string;
}

export function ReportQualityView({ projectId }: ReportQualityViewProps) {
  const [validation, setValidation] = useState<ReportQualityResultDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  const loadValidation = useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await apiClient.getLatestProjectValidation(projectId);
      setValidation(res);
    } catch {
      // Validation not run yet
      setValidation(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadValidation();
  }, [loadValidation]);

  const handleRunValidation = async () => {
    try {
      setValidating(true);
      setErrorMsg(null);
      const res = await apiClient.validateProjectReport(projectId, { force_revalidate: true });
      setValidation(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute quality engine validation.");
    } finally {
      setValidating(false);
    }
  };

  const getStatusBadge = (status: QualityGateStatus) => {
    switch (status) {
      case "READY":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> READY FOR EXPORT
          </span>
        );
      case "READY_WITH_WARNINGS":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> READY (WITH WARNINGS)
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-700 border border-orange-200">
            <AlertCircle className="w-3.5 h-3.5 mr-1" /> REVIEW REQUIRED
          </span>
        );
      case "BLOCKED":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <ShieldAlert className="w-3.5 h-3.5 mr-1" /> SUBMISSION BLOCKED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "BLOCKING":
        return <Badge variant="danger">BLOCKING</Badge>;
      case "ERROR":
        return <Badge variant="warning">ERROR / REVIEW</Badge>;
      case "WARNING":
        return <Badge variant="neutral">WARNING</Badge>;
      default:
        return <Badge variant="outline">INFO</Badge>;
    }
  };

  const filteredIssues = (validation?.issues || []).filter((issue) => {
    if (filterSeverity === "ALL") return true;
    return issue.severity === filterSeverity;
  });

  // Group checks by category
  const checksByCategory = (validation?.checks || []).reduce<Record<string, ValidationCheckDTO[]>>((acc, c) => {
    acc[c.category] = acc[c.category] || [];
    acc[c.category].push(c);
    return acc;
  }, {});

  return (
    <Card className="border border-slate-200 shadow-xs">
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-indigo-600" />
              <CardTitle className="text-base font-bold text-slate-900">
                Stage 11: Report Validation &amp; Quality Engine
              </CardTitle>
            </div>
            <CardDescription className="text-xs text-slate-500 mt-1">
              Automated multi-layer quality gate evaluating Template Schema, Report Plan, Content Grounding, Evidence, DOCX, PDF, and Security.
            </CardDescription>
          </div>

          <div className="flex items-center space-x-2">
            {validation && getStatusBadge(validation.status)}
            <Button
              onClick={handleRunValidation}
              disabled={validating || loading}
              variant="outline"
              size="sm"
              className="text-xs font-semibold"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validating ? "animate-spin" : ""}`} />
              {validating ? "Validating Report..." : validation ? "Re-Run Validation" : "Run Quality Engine"}
            </Button>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-3 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {validation?.is_stale && (
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>
              <strong>Validation is Stale:</strong> The underlying report content, DOCX, PDF, or template has been modified since the last audit. Please re-run validation.
            </span>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {!validation && !loading && (
          <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <Layers className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700">No Quality Engine Validation Run Yet</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-md mx-auto">
              Execute the automated quality gate to audit template compliance, factual grounding, numerical consistency, and artifact integrity.
            </p>
            <Button
              onClick={handleRunValidation}
              disabled={validating}
              size="sm"
              variant="primary"
              className="mt-4 text-xs font-bold"
            >
              <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
              {validating ? "Running Multi-Layer Checks..." : "Run Quality Engine Validation"}
            </Button>
          </div>
        )}

        {validation && (
          <>
            {/* Metric Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
                <span className="text-[10px] uppercase font-bold text-slate-400">Total Checks</span>
                <span className="text-lg font-black text-slate-800 block mt-0.5">
                  {validation.summary.total_checks}
                </span>
              </div>
              <div className="bg-emerald-50/50 p-3 rounded-lg border border-emerald-200 text-center">
                <span className="text-[10px] uppercase font-bold text-emerald-600">Passed Checks</span>
                <span className="text-lg font-black text-emerald-700 block mt-0.5">
                  {validation.summary.passed_checks}
                </span>
              </div>
              <div className="bg-rose-50/50 p-3 rounded-lg border border-rose-200 text-center">
                <span className="text-[10px] uppercase font-bold text-rose-600">Blocking Issues</span>
                <span className="text-lg font-black text-rose-700 block mt-0.5">
                  {validation.summary.blocking_count}
                </span>
              </div>
              <div className="bg-orange-50/50 p-3 rounded-lg border border-orange-200 text-center">
                <span className="text-[10px] uppercase font-bold text-orange-600">Review Required</span>
                <span className="text-lg font-black text-orange-700 block mt-0.5">
                  {validation.summary.errors_count}
                </span>
              </div>
              <div className="bg-amber-50/50 p-3 rounded-lg border border-amber-200 text-center col-span-2 sm:col-span-1">
                <span className="text-[10px] uppercase font-bold text-amber-600">Warnings</span>
                <span className="text-lg font-black text-amber-700 block mt-0.5">
                  {validation.summary.warnings_count}
                </span>
              </div>
            </div>

            {/* Layer Check Progress List */}
            <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
              <div className="bg-slate-50 px-4 py-2 text-xs font-bold text-slate-700 flex items-center justify-between">
                <span>12-Layer Automated Quality Checks</span>
                <span className="text-[10px] text-slate-400 font-normal">Deterministic rules</span>
              </div>

              {Object.entries(checksByCategory).map(([cat, catChecks]) => {
                const isExpanded = expandedCategory === cat;
                const hasFail = catChecks.some((c) => c.status === "FAIL");
                const hasWarn = catChecks.some((c) => c.status === "WARNING");
                const statusColor = hasFail
                  ? "text-rose-600"
                  : hasWarn
                  ? "text-amber-600"
                  : "text-emerald-600";

                return (
                  <div key={cat} className="text-xs">
                    <button
                      onClick={() => setExpandedCategory(isExpanded ? null : cat)}
                      className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-slate-50/70 transition"
                    >
                      <div className="flex items-center space-x-2">
                        {hasFail ? (
                          <AlertCircle className="w-4 h-4 text-rose-600" />
                        ) : hasWarn ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        )}
                        <span className="font-semibold text-slate-800 capitalize">
                          {cat.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`text-[11px] font-bold ${statusColor}`}>
                          {catChecks.filter((c) => c.status === "PASS").length}/{catChecks.length} Passed
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-3 pt-1 space-y-1.5 bg-slate-50/50 border-t border-slate-100">
                        {catChecks.map((c) => (
                          <div
                            key={c.check_id}
                            className="flex items-start justify-between p-2 rounded bg-white border border-slate-100"
                          >
                            <div className="flex items-start space-x-2">
                              {c.status === "PASS" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5" />}
                              {c.status === "WARNING" && <AlertTriangle className="w-3.5 h-3.5 text-amber-600 mt-0.5" />}
                              {c.status === "FAIL" && <AlertCircle className="w-3.5 h-3.5 text-rose-600 mt-0.5" />}
                              {c.status === "NOT_TESTED" && <Clock className="w-3.5 h-3.5 text-slate-400 mt-0.5" />}
                              <div>
                                <p className="text-[11px] text-slate-700 font-medium">{c.message}</p>
                                {c.source && (
                                  <span className="text-[9px] text-slate-400 block mt-0.5">Source: {c.source}</span>
                                )}
                              </div>
                            </div>
                            <span className="text-[10px] font-bold uppercase text-slate-500 ml-2">{c.status}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Surfaced Issues & Recommendations */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <h4 className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-slate-600" />
                  <span>Surfaced Issues &amp; Remediations ({validation.issues.length})</span>
                </h4>

                {/* Filter buttons */}
                <div className="flex items-center space-x-1">
                  {["ALL", "BLOCKING", "ERROR", "WARNING"].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setFilterSeverity(sev)}
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
                        filterSeverity === sev
                          ? "bg-slate-800 text-white"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              {filteredIssues.length === 0 ? (
                <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>No {filterSeverity !== "ALL" ? filterSeverity.toLowerCase() : ""} issues identified in this report.</span>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredIssues.map((issue) => (
                    <div
                      key={issue.issue_id}
                      className="p-3 bg-white rounded-lg border border-slate-200 space-y-1.5 shadow-2xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          {getSeverityBadge(issue.severity)}
                          <span className="text-xs font-bold text-slate-800">
                            {issue.section_title || issue.section_id || "General Report Check"}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 capitalize">
                          {issue.category.replace(/_/g, " ")}
                        </span>
                      </div>

                      <p className="text-xs text-slate-700">{issue.message}</p>

                      {issue.affected_claim && (
                        <div className="p-2 bg-slate-50 border border-slate-100 rounded text-[11px] text-slate-600 italic">
                          Claim: &ldquo;{issue.affected_claim}&rdquo;
                        </div>
                      )}

                      {issue.suggested_action && (
                        <div className="flex items-start space-x-1.5 text-[11px] text-indigo-700 bg-indigo-50/60 p-2 rounded border border-indigo-100">
                          <Info className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0 mt-0.5" />
                          <span>
                            <strong>Suggested Remediation:</strong> {issue.suggested_action}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
