"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
  ShieldCheck,
  Lock,
  Layers,
  Sparkles,
  AlertCircle,
  Clock,
  ExternalLink,
  FileType
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface DocumentCompilerProps {
  projectId: string;
}

export function DocumentCompiler({ projectId }: DocumentCompilerProps) {
  // Stage 9 DOCX states
  const [compilingDocx, setCompilingDocx] = useState<boolean>(false);
  const [downloadingDocx, setDownloadingDocx] = useState<boolean>(false);
  const [compiledDocxResult, setCompiledDocxResult] = useState<any | null>(null);
  const [docxErrorMsg, setDocxErrorMsg] = useState<string | null>(null);
  const [blockingIssues, setBlockingIssues] = useState<string[]>([]);
  const [docxStep, setDocxStep] = useState<string>("");
  const [docxProgress, setDocxProgress] = useState<number>(0);

  // Prerequisites
  const [hasReportDraft, setHasReportDraft] = useState<boolean>(false);
  const [hasPlanApproved, setHasPlanApproved] = useState<boolean>(false);
  const [verificationPassed, setVerificationPassed] = useState<boolean | null>(null);

  const checkPrerequisites = useCallback(async () => {
    if (!projectId) return;
    try {
      // 1. Check Report Plan
      try {
        const plan = await apiClient.getProjectReportPlan(projectId);
        setHasPlanApproved(Boolean(plan && plan.is_approved));
      } catch {
        setHasPlanApproved(false);
      }

      // 2. Check Report Draft
      try {
        const report = await apiClient.getLatestProjectReport(projectId);
        setHasReportDraft(Boolean(report && report.sections && report.sections.length > 0));
      } catch {
        setHasReportDraft(false);
      }

      // 3. Check Stage 8 Verification
      try {
        const v = await apiClient.getLatestProjectVerification(projectId);
        if (v && v.quality_gates) {
          setVerificationPassed(v.quality_gates.can_proceed_to_document_generation);
        } else {
          setVerificationPassed(null);
        }
      } catch {
        setVerificationPassed(null);
      }
    } catch (e) {
      console.warn("Error checking document generation prerequisites:", e);
    }
  }, [projectId]);

  useEffect(() => {
    checkPrerequisites();
  }, [checkPrerequisites]);

  // Handle Stage 9 DOCX Compilation
  const handleCompileDocx = async (force: boolean = false) => {
    if (!projectId) return;
    setCompilingDocx(true);
    setDocxErrorMsg(null);
    setBlockingIssues([]);
    setDocxStep("Loading locked template & validating inputs...");
    setDocxProgress(20);

    try {
      const timer1 = setTimeout(() => {
        setDocxStep("Applying college formatting & assembling sections...");
        setDocxProgress(50);
      }, 700);

      const timer2 = setTimeout(() => {
        setDocxStep("Validating OpenXML structure & running reopen test...");
        setDocxProgress(80);
      }, 1400);

      const res = await apiClient.compileProjectDocx(projectId, { force });
      clearTimeout(timer1);
      clearTimeout(timer2);

      setCompiledDocxResult(res);
      setDocxProgress(100);
      setDocxStep("Completed & validated!");
    } catch (err: any) {
      let msg = err.message || "Failed to compile document.";
      if (err.status === 422 || msg.includes("Quality Gate")) {
        setBlockingIssues([
          "Stage 8 verification detected ungrounded claims or missing citations.",
          "You can force compilation in REVIEW_REQUIRED mode or resolve the claims."
        ]);
      }
      setDocxErrorMsg(msg);
      setDocxStep("Compilation failed");
    } finally {
      setCompilingDocx(false);
    }
  };

  // Handle Stage 9 DOCX Download
  const handleDownloadDocx = async () => {
    if (!projectId) return;
    setDownloadingDocx(true);
    try {
      const { blob, filename } = await apiClient.downloadProjectDocxBlob(projectId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "Report.docx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloadingDocx(false);
    }
  };

  const isDocxReady = Boolean(compiledDocxResult);

  return (
    <Card className="border border-slate-200 shadow-sm bg-white overflow-hidden">
      <CardHeader className="bg-slate-50/60 border-b border-slate-100 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-md bg-blue-100 text-blue-700">
                <FileCheck2 className="w-4 h-4" />
              </span>
              <CardTitle className="text-base font-semibold text-slate-900">
                Deterministic Document &amp; PDF Engine
              </CardTitle>
            </div>
            <CardDescription className="text-xs text-slate-500 mt-1">
              Stages 9 &amp; 10: Compiles institutional DOCX and server-side PDF grounded in locked template rules.
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Badge
              variant="outline"
              className={
                hasPlanApproved && hasReportDraft
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 text-[11px]"
                  : "bg-amber-50 text-amber-700 border-amber-200 text-[11px]"
              }
            >
              {hasPlanApproved && hasReportDraft ? "Prerequisites Met" : "Prerequisites Incomplete"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-6">
        {/* Prerequisites Checklist */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50/50 text-xs">
          <div className="flex items-center space-x-2">
            {hasPlanApproved ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
            )}
            <span className={hasPlanApproved ? "text-slate-800 font-medium" : "text-slate-500"}>
              Report Plan Approved
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {hasReportDraft ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
            )}
            <span className={hasReportDraft ? "text-slate-800 font-medium" : "text-slate-500"}>
              Generated Report Draft
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {verificationPassed === true ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : verificationPassed === false ? (
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
            ) : (
              <Clock className="w-4 h-4 text-slate-400 shrink-0" />
            )}
            <span
              className={
                verificationPassed === true
                  ? "text-slate-800 font-medium"
                  : verificationPassed === false
                  ? "text-rose-600 font-medium"
                  : "text-slate-500"
              }
            >
              {verificationPassed === true
                ? "Quality Gate Cleared"
                : verificationPassed === false
                ? "Review Required"
                : "Verification Pending"}
            </span>
          </div>
        </div>

        {/* SECTION 1: STAGE 9 DETERMINISTIC DOCX COMPILATION */}
        <div className="p-4 rounded-lg border border-slate-200 bg-white space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="p-1 rounded bg-blue-50 text-blue-600">
                <FileText className="w-4 h-4" />
              </span>
              <span className="text-sm font-semibold text-slate-900">Stage 9: OpenXML DOCX Compilation</span>
            </div>
            {compiledDocxResult && (
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                DOCX Validated
              </Badge>
            )}
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-500">
              Deterministic assembly enforcing margins, typography, tables, and headers/footers.
            </span>
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => handleCompileDocx(false)}
                disabled={compilingDocx || !hasReportDraft}
                size="sm"
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-3"
              >
                {compilingDocx ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Compiling DOCX...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                    Compile DOCX
                  </>
                )}
              </Button>
              {compiledDocxResult && (
                <Button
                  onClick={handleDownloadDocx}
                  disabled={downloadingDocx}
                  variant="outline"
                  size="sm"
                  className="border-blue-200 text-blue-700 hover:bg-blue-50 text-xs h-8 px-3"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5" />
                  Download DOCX
                </Button>
              )}
            </div>
          </div>

          {/* Compilation Progress Bar */}
          {compilingDocx && (
            <div className="p-3 rounded-lg border border-blue-100 bg-blue-50/60 space-y-2">
              <div className="flex justify-between text-xs text-blue-900 font-medium">
                <span>{docxStep}</span>
                <span>{docxProgress}%</span>
              </div>
              <div className="w-full bg-blue-100 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${docxProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* DOCX Error / Blocking Issues */}
          {blockingIssues.length > 0 && (
            <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/80 space-y-2 text-xs">
              <div className="flex items-center space-x-1.5 text-amber-900 font-semibold">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Stage 8 Quality Gate Blocked Final Compilation</span>
              </div>
              <ul className="list-disc list-inside text-amber-800 space-y-0.5 pl-1">
                {blockingIssues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
              <div className="pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleCompileDocx(true)}
                  className="border-amber-300 text-amber-900 hover:bg-amber-100 text-xs font-semibold h-7"
                >
                  Force Compile as REVIEW_REQUIRED Draft
                </Button>
              </div>
            </div>
          )}
          {docxErrorMsg && blockingIssues.length === 0 && (
            <div className="p-3 rounded-lg border border-rose-200 bg-rose-50 flex items-start space-x-2 text-xs text-rose-800">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{docxErrorMsg}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
