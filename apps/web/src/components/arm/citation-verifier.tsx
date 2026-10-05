"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  FileCheck,
  XCircle,
  HelpCircle,
  BookmarkCheck,
  RefreshCw,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
  Search,
} from "lucide-react";
import {
  apiClient,
  ReportVerificationReportDTO,
  ClaimVerificationRecordDTO,
  ClaimVerificationStatus,
} from "@/lib/api-client";

interface CitationVerifierProps {
  projectId: string;
  versionNumber?: number;
  onVerificationComplete?: (report: ReportVerificationReportDTO) => void;
}

export function CitationVerifier({
  projectId,
  versionNumber,
  onVerificationComplete,
}: CitationVerifierProps) {
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verification, setVerification] = useState<ReportVerificationReportDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selectedSection, setSelectedSection] = useState<string>("ALL");

  const loadLatestVerification = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (versionNumber) {
        const res = await apiClient.getVersionProjectVerification(projectId, versionNumber);
        setVerification(res);
      } else {
        const res = await apiClient.getLatestProjectVerification(projectId);
        setVerification(res);
      }
    } catch {
      // No existing verification yet
      setVerification(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, versionNumber]);

  useEffect(() => {
    loadLatestVerification();
  }, [loadLatestVerification]);


  async function handleRunVerification() {
    setVerifying(true);
    setError(null);
    try {
      const res = await apiClient.verifyProjectReport(projectId, versionNumber);
      setVerification(res);
      if (onVerificationComplete) {
        onVerificationComplete(res);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to complete citation and evidence verification.");
    } finally {
      setVerifying(false);
    }
  }

  function getStatusBadge(status: ClaimVerificationStatus) {
    switch (status) {
      case "supported":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Verified & Supported
          </span>
        );
      case "partially_supported":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Partially Supported
          </span>
        );
      case "unsupported":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3.5 h-3.5" />
            Unsupported
          </span>
        );
      case "citation_invalid":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 border border-rose-300">
            <XCircle className="w-3.5 h-3.5" />
            Fabricated / Invalid Citation
          </span>
        );
      case "citation_required":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <BookmarkCheck className="w-3.5 h-3.5" />
            Citation Required
          </span>
        );
      case "requires_review":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-3.5 h-3.5" />
            Needs Student Review
          </span>
        );
    }
  }

  const allClaims = verification?.claims || [];
  const uniqueSections = Array.from(new Set(allClaims.map((c) => c.section_id)));

  const filteredClaims = allClaims.filter((c) => {
    if (selectedSection !== "ALL" && c.section_id !== selectedSection) return false;
    if (selectedFilter === "ALL") return true;
    if (selectedFilter === "BLOCKING") {
      return c.status === "citation_invalid" || (c.status === "unsupported" && (c.claim_type === "project_result" || c.claim_type === "metric"));
    }
    return c.status === selectedFilter;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & Trigger */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
            <h2 className="text-xl font-bold text-slate-900">Citation & Evidence Verification</h2>
            <span className="text-xs font-semibold px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-150">
              Stage 8 Engine v1.0
            </span>
          </div>
          <p className="text-sm text-slate-600 max-w-2xl">
            Verifies generated academic text against project facts and evidence files. Detects ungrounded metrics, protects against fabricated citations, and maps verified provenance.
          </p>
        </div>

        <button
          onClick={handleRunVerification}
          disabled={verifying}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          <RefreshCw className={`w-4 h-4 ${verifying ? "animate-spin" : ""}`} />
          {verifying ? "Verifying Claims..." : verification ? "Re-Verify Draft" : "Run Verification"}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700 flex items-start gap-2">
          <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Verification Alert</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {loading && !verification && (
        <div className="p-12 text-center text-slate-500 bg-white border border-slate-200 rounded-xl">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-500" />
          <p className="font-medium">Loading verification status...</p>
        </div>
      )}

      {!loading && !verification && (
        <div className="p-12 text-center bg-slate-50 border border-dashed border-slate-300 rounded-xl">
          <FileCheck className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800 mb-1">No Verification Run Yet</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
            Run the Stage 8 Citation & Evidence Verification engine to audit all assertions, numbers, and references before document generation.
          </p>
          <button
            onClick={handleRunVerification}
            disabled={verifying}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm"
          >
            <ShieldCheck className="w-4 h-4" />
            Verify Report Draft
          </button>
        </div>
      )}

      {verification && (
        <>
          {/* Summary Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-slate-500">Total Claims</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">{verification.summary.total_claims}</p>
            </div>
            <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-emerald-700">Supported</span>
              <p className="text-2xl font-bold text-emerald-800 mt-1">{verification.summary.supported}</p>
            </div>
            <div className="p-4 bg-amber-50/50 border border-amber-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-amber-700">Partial</span>
              <p className="text-2xl font-bold text-amber-800 mt-1">{verification.summary.partially_supported}</p>
            </div>
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-slate-600">Needs Review</span>
              <p className="text-2xl font-bold text-slate-800 mt-1">{verification.summary.requires_review}</p>
            </div>
            <div className="p-4 bg-rose-50/50 border border-rose-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-rose-700">Unsupported</span>
              <p className="text-2xl font-bold text-rose-800 mt-1">{verification.summary.unsupported}</p>
            </div>
            <div className="p-4 bg-indigo-50/50 border border-indigo-200 rounded-lg shadow-sm">
              <span className="text-xs font-medium text-indigo-700">Grounding Rate</span>
              <p className="text-2xl font-bold text-indigo-800 mt-1">{verification.summary.grounding_rate_percent}%</p>
            </div>
          </div>

          {/* Quality Gate Status Banner */}
          <div
            className={`p-4 rounded-xl border flex items-start gap-3 ${
              verification.quality_gates.can_proceed_to_document_generation
                ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                : "bg-rose-50 border-rose-200 text-rose-900"
            }`}
          >
            {verification.quality_gates.can_proceed_to_document_generation ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className="font-semibold text-sm">
                {verification.quality_gates.can_proceed_to_document_generation
                  ? "Quality Gate Passed: Ready for Document Generation"
                  : "Quality Gate Blocked: Document Generation Paused"}
              </h4>
              <p className="text-xs mt-0.5 opacity-90">
                {verification.quality_gates.can_proceed_to_document_generation
                  ? "All project assertions and citations are grounded. No fabricated citations or unsupported core results were detected."
                  : "Critical verification issues detected. Fabricated citations or unsupported numerical claims must be resolved before document compilation."}
              </p>

              {verification.quality_gates.blocking_issues.length > 0 && (
                <div className="mt-2.5 space-y-1">
                  {verification.quality_gates.blocking_issues.map((b, idx) => (
                    <div key={idx} className="text-xs font-medium text-rose-800 flex items-center gap-1.5">
                      <XCircle className="w-3.5 h-3.5" />
                      {b}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Filters & Section Switcher */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Filter:</span>
              <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
                {["ALL", "BLOCKING", "supported", "partially_supported", "unsupported", "citation_required", "citation_invalid"].map((f) => (
                  <button
                    key={f}
                    onClick={() => setSelectedFilter(f)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                      selectedFilter === f
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {f.replace("_", " ").toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {uniqueSections.length > 1 && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Section:</span>
                <select
                  value={selectedSection}
                  onChange={(e) => setSelectedSection(e.target.value)}
                  className="text-xs font-medium bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="ALL">All Sections</option>
                  {uniqueSections.map((sec) => (
                    <option key={sec} value={sec}>
                      {sec}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Claims List Table/Cards */}
          <div className="space-y-3">
            {filteredClaims.length === 0 ? (
              <div className="p-8 text-center bg-white border border-slate-200 rounded-xl text-slate-500 text-sm">
                No claims match the selected filter.
              </div>
            ) : (
              filteredClaims.map((claim) => (
                <div
                  key={claim.claim_id}
                  className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-slate-300 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(claim.status)}
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                        {claim.claim_type.replace("_", " ")}
                      </span>
                      <span className="text-xs text-slate-400">Section: {claim.section_id}</span>
                    </div>

                    <span className="text-[11px] text-slate-400 font-mono">
                      ID: {claim.claim_id.slice(0, 14)}
                    </span>
                  </div>

                  {/* Claim Text */}
                  <p className="text-sm font-medium text-slate-900 mb-2">
                    &ldquo;{claim.text}&rdquo;
                  </p>

                  {/* Verification Rationale */}
                  {claim.reason && (
                    <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-150 text-xs text-slate-600 mb-2">
                      <span className="font-semibold text-slate-700">Verification Finding: </span>
                      {claim.reason}
                    </div>
                  )}

                  {/* Provenance & Evidence Trace */}
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1 border-t border-slate-100">
                    {claim.evidence_ids.length > 0 && (
                      <span className="inline-flex items-center gap-1 text-slate-700">
                        <FileCheck className="w-3.5 h-3.5 text-indigo-500" />
                        Evidence Files: <code className="bg-slate-100 px-1 rounded">{claim.evidence_ids.join(", ")}</code>
                      </span>
                    )}

                    {claim.source_ids.length > 0 && (
                      <span className="inline-flex items-center gap-1 text-slate-700">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                        Project Sources: <code className="bg-slate-100 px-1 rounded">{claim.source_ids.join(", ")}</code>
                      </span>
                    )}

                    {claim.provenance?.excerpt && (
                      <span className="text-slate-500 truncate max-w-md">
                        Excerpt: &ldquo;{claim.provenance.excerpt}&rdquo;
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
