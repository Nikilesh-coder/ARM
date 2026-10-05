"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  CheckCircle2,
  AlertCircle,
  FileCheck2,
  Clock,
  Sparkles,
  ChevronRight,
  ExternalLink,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  FolderKanban,
  Plus
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { WorkflowStepper } from "@/components/workflow/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { StatusBanner } from "@/components/ui/status-banner";
import { INITIAL_MOCK_REPORTS, ReportItem } from "@/lib/mock-data";
import { apiClient, ProjectDTO } from "@/lib/api-client";
import { ReportPlanner } from "@/components/arm/report-planner";
import { ReportGenerator } from "@/components/arm/report-generator";
import { CitationVerifier } from "@/components/arm/citation-verifier";
import { DocumentCompiler } from "@/components/arm/document-compiler";
import { ReportQualityView } from "@/components/arm/report-quality-view";

export default function ReportsPage() {
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [reports] = useState<ReportItem[]>(INITIAL_MOCK_REPORTS);
  const [selectedReport] = useState<ReportItem>(INITIAL_MOCK_REPORTS[0]);
  const [downloadMsg, setDownloadMsg] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const loadProjects = React.useCallback(async () => {
    try {
      setLoadingProjects(true);
      const list = await apiClient.getProjects();
      setProjects(list);
      if (list.length > 0 && !selectedProjectId) {
        setSelectedProjectId(list[0].id || "");
      }
    } catch {
      // Fallback
    } finally {
      setLoadingProjects(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const sections = [
    { key: "sec-01", title: "Chapter 1: Introduction & Problem Definition", words: 850, status: "Validated", figures: 0, sources: 3 },
    { key: "sec-02", title: "Chapter 2: Literature Survey & Related Work", words: 1420, status: "Validated", figures: 0, sources: 12 },
    { key: "sec-03", title: "Chapter 3: System Architecture & Methodology", words: 1950, status: "Validated", figures: 3, sources: 4 },
    { key: "sec-04", title: "Chapter 4: Implementation Details & Algorithm", words: 2400, status: "Validated", figures: 2, sources: 2 },
    { key: "sec-05", title: "Chapter 5: Experimental Results & Comparative Study", words: 1250, status: "Validated", figures: 2, sources: 1 },
    { key: "sec-06", title: "Chapter 6: Conclusion & Future Scope", words: 580, status: "Draft Planned", figures: 0, sources: 2 },
    { key: "sec-07", title: "References & Bibliography (IEEE Numeric)", words: 420, status: "Verified 24/24", figures: 0, sources: 24 },
  ];

  const handleDownload = async (format: "DOCX" | "PDF") => {
    if (!selectedProjectId) {
      setDownloadError("Please select a project before downloading.");
      return;
    }
    setIsDownloading(true);
    setDownloadMsg(null);
    setDownloadError(null);

    try {
      // Step 1: Compile the document
      setDownloadMsg(`⚙️ Compiling ${format} using deterministic Document Engine...`);
      if (format === "DOCX") {
        await apiClient.compileProjectDocx(selectedProjectId);
      } else {
        // Ensure DOCX exists first, then compile PDF
        try { await apiClient.compileProjectDocx(selectedProjectId); } catch { /* may already exist */ }
        await apiClient.compileProjectPdf(selectedProjectId);
      }

      // Step 2: Download the blob
      setDownloadMsg(`📥 Preparing ${format} for download...`);
      let blob: Blob;
      let filename: string;

      if (format === "DOCX") {
        const result = await apiClient.downloadProjectDocxBlob(selectedProjectId);
        blob = result.blob;
        filename = result.filename;
      } else {
        const result = await apiClient.downloadProjectPdfBlob(selectedProjectId);
        blob = result.blob;
        filename = result.filename;
      }

      // Step 3: Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setDownloadMsg(`✅ ${format} downloaded successfully as "${filename}".`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to download ${format}`;
      setDownloadError(`❌ ${msg}`);
      setDownloadMsg(null);
    } finally {
      setIsDownloading(false);
    }
  };


  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Report Plan &amp; Export Hub</h1>
              <p className="text-xs text-slate-500 mt-1">
                Stage 6: AI-Assisted Report Planner. Synthesizes locked templates, project ground truth, and verified evidence.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => handleDownload("DOCX")}
                variant="primary"
                size="sm"
                disabled={isDownloading}
              >
                <Download className={`w-3.5 h-3.5 mr-1 ${isDownloading ? "animate-bounce" : ""}`} />
                {isDownloading ? "Compiling..." : "Compile DOCX"}
              </Button>
            </div>
          </div>

          {/* Download status banners */}
          {downloadMsg && (
            <div className="flex items-center gap-2 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
              <Clock className="w-4 h-4 shrink-0" />
              {downloadMsg}
            </div>
          )}
          {downloadError && (
            <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {downloadError}
            </div>
          )}


          <WorkflowStepper currentStep={4} />

          {/* Project Selector Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="flex items-center gap-2">
              <FolderKanban className="w-5 h-5 text-indigo-600" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Active Project:
              </span>
              {loadingProjects ? (
                <span className="text-xs text-slate-400 flex items-center">
                  <Clock className="w-3.5 h-3.5 mr-1 animate-spin" /> Loading...
                </span>
              ) : projects.length > 0 ? (
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="px-2.5 py-1 text-sm border rounded-md border-slate-300 bg-white font-medium text-slate-800 focus:outline-none"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title || p.project_name || "Untitled Project"}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-xs text-slate-500 italic">No projects found. Please create a project first.</span>
              )}
            </div>

            <Link href="/projects">
              <Button variant="outline" size="sm">
                <Plus className="w-3.5 h-3.5 mr-1" /> New Project
              </Button>
            </Link>
          </div>

          {/* Live Stage 6 Report Planner, Stage 7 Report Generator, Stage 8 Citation Verifier, Stage 9/10 Document Compiler, Stage 11 Quality Engine */}
          {selectedProjectId ? (
            <>
              <ReportPlanner projectId={selectedProjectId} />
              <ReportGenerator projectId={selectedProjectId} />
              <CitationVerifier projectId={selectedProjectId} />
              <DocumentCompiler projectId={selectedProjectId} />
              <ReportQualityView projectId={selectedProjectId} />
            </>
          ) : (
            <div className="p-12 text-center text-slate-500 text-sm bg-white rounded-xl border border-slate-200">
              Please select or create a project to generate and review the AI report plan.
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs">
              <span className="text-[11px] text-slate-400 font-medium block">Report Scope</span>
              <span className="text-sm font-bold text-slate-900 block mt-0.5">{selectedReport.reportType}</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs">
              <span className="text-[11px] text-slate-400 font-medium block">Total Word Count</span>
              <span className="text-sm font-bold text-blue-700 block mt-0.5">{selectedReport.wordCount.toLocaleString()} words</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs">
              <span className="text-[11px] text-slate-400 font-medium block">Verified Citations</span>
              <span className="text-sm font-bold text-emerald-700 block mt-0.5">{selectedReport.citationCount} Sources (0 Hallucinations)</span>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs">
              <span className="text-[11px] text-slate-400 font-medium block">Validation Status</span>
              <span className="text-sm font-bold text-slate-900 block mt-0.5 flex items-center">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 mr-1" />
                92% Rubric Score
              </span>
            </div>
          </div>

          {/* Section Breakdown List */}
          <Card className="mb-8">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Structured Chapter Outlines</CardTitle>
                <CardDescription>Generated section-by-section according to institutional guidelines</CardDescription>
              </div>
              <Badge variant="academic">7 Sections Active</Badge>
            </CardHeader>
            <CardContent className="divide-y divide-slate-100 p-0">
              {sections.map((sec, idx) => (
                <div
                  key={sec.key}
                  className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60 transition"
                >
                  <div className="flex items-start sm:items-center space-x-3.5">
                    <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center flex-shrink-0">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="text-xs sm:text-sm font-bold text-slate-900">{sec.title}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5 flex flex-wrap gap-3">
                        <span>{sec.words} words</span>
                        {sec.figures > 0 && <span>&middot; {sec.figures} Figures/Tables</span>}
                        {sec.sources > 0 && <span>&middot; {sec.sources} Mapped Sources</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 self-end sm:self-center">
                    <Badge variant={sec.status.includes("Verified") || sec.status === "Validated" ? "success" : "neutral"}>
                      {sec.status}
                    </Badge>
                    <button className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center">
                      Inspect Content <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                    </button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Version History Table */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Version History &amp; Compilations</CardTitle>
              <CardDescription>Every generated draft is tracked deterministically</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-y border-slate-100 text-slate-500 uppercase font-semibold text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Version</th>
                      <th className="py-3 px-4">Generated Time</th>
                      <th className="py-3 px-4">Word Count</th>
                      <th className="py-3 px-4">Compliance Status</th>
                      <th className="py-3 px-4 text-right">Download Formats</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50/50">
                      <td className="py-3.5 px-4 font-bold text-slate-800">v1.2-draft (Latest)</td>
                      <td className="py-3.5 px-4 text-slate-500">Today, 11:45 AM</td>
                      <td className="py-3.5 px-4 font-mono text-slate-700">8,450 words</td>
                      <td className="py-3.5 px-4">
                        <Badge variant="success">Validated 92%</Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <button onClick={() => handleDownload("DOCX")} className="text-blue-600 font-bold hover:underline">DOCX</button>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/50 text-slate-500">
                      <td className="py-3.5 px-4 font-medium">v1.1-initial</td>
                      <td className="py-3.5 px-4">Sep 24, 2026</td>
                      <td className="py-3.5 px-4 font-mono">5,200 words</td>
                      <td className="py-3.5 px-4">
                        <Badge variant="neutral">Draft</Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <button onClick={() => handleDownload("DOCX")} className="text-slate-600 hover:underline">DOCX</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
