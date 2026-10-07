"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Play,
  FileCode2,
  Layers,
  Type,
  Table as TableIcon,
  Image as ImageIcon,
  Info,
  Lock,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { TemplateReviewModal } from "./template-review-modal";

export interface TemplateData {
  id: string;
  name: string;
  file_type: string;
  file_size?: number;
  status: string;
  analysis_status?: string;
  original_file_path?: string;
  is_locked?: boolean;
  locked_at?: string;
  locked_by?: string;
  locked_schema_version?: string;
  created_at?: string;
}

export interface TemplateAnalysisData {
  template_id: string;
  status: string;
  schema_version?: string;
  parser_version?: string;
  schema_data?: any;
  warnings?: string[];
}

interface CollegeTemplateUploadProps {
  projectId: string;
  initialTemplate?: TemplateData | null;
  onTemplateUpdated?: (template: TemplateData | null) => void;
}

export function CollegeTemplateUpload({
  projectId,
  initialTemplate = null,
  onTemplateUpdated,
}: CollegeTemplateUploadProps) {
  const [template, setTemplate] = useState<TemplateData | null>(initialTemplate);
  const [uploadState, setUploadState] = useState<
    "idle" | "uploading" | "success" | "ready" | "analyzing" | "analyzed" | "error"
  >(initialTemplate?.status === "analyzed" ? "analyzed" : initialTemplate ? "ready" : "idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<string>("");
  const [analysisData, setAnalysisData] = useState<TemplateAnalysisData | null>(null);
  const [isReviewOpen, setIsReviewOpen] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadAnalysis = useCallback(async (templateId: string) => {
    try {
      const res = await apiClient.getProjectTemplateAnalysis(projectId, templateId);
      if (res && res.status === "completed" && res.schema_data) {
        setAnalysisData(res);
        setUploadState("analyzed");
        setStatusMessage("Template analyzed successfully. Document structure and typography extracted.");
      }
    } catch {
      // Analysis not ready yet
    }
  }, [projectId]);

  const loadTemplate = useCallback(async () => {
    try {
      const data = await apiClient.getProjectTemplate(projectId);
      if (data && data.id) {
        setTemplate(data);
        if (data.is_locked || data.status === "locked") {
          setUploadState("analyzed");
          loadAnalysis(data.id);
        } else if (data.status === "analyzed") {
          setUploadState("analyzed");
          loadAnalysis(data.id);
        } else if (data.status === "analyzing") {
          setUploadState("analyzing");
        } else {
          setUploadState("ready");
        }
        onTemplateUpdated?.(data);
      } else {
        setTemplate(null);
        setUploadState("idle");
      }
    } catch {
      setTemplate(null);
      setUploadState("idle");
    }
  }, [projectId, onTemplateUpdated, loadAnalysis]);

  useEffect(() => {
    if (initialTemplate) {
      setTemplate(initialTemplate);
      if (initialTemplate.status === "analyzed") {
        setUploadState("analyzed");
        loadAnalysis(initialTemplate.id);
      } else if (initialTemplate.status === "analyzing") {
        setUploadState("analyzing");
      } else {
        setUploadState("ready");
      }
    } else if (projectId) {
      loadTemplate();
    }
  }, [projectId, initialTemplate, loadTemplate, loadAnalysis]);

  // Clean up polling interval
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleTriggerPicker = () => {
    setErrorMessage(null);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (fileInputRef.current) fileInputRef.current.value = "";

    const nameLower = file.name.toLowerCase();
    if (!nameLower.endsWith(".docx")) {
      setUploadState("error");
      setErrorMessage("Unsupported file type. Only DOCX college templates (.docx) are currently supported.");
      return;
    }

    if (file.size === 0) {
      setUploadState("error");
      setErrorMessage("Uploaded file is empty. Please upload a valid document.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setUploadState("error");
      setErrorMessage("File is too large (exceeds 25MB limit). Please upload a smaller template.");
      return;
    }

    setUploadState("uploading");
    setErrorMessage(null);
    setStatusMessage("Uploading template...");
    setAnalysisData(null);

    try {
      const res = await apiClient.uploadProjectTemplate(projectId, file);

      const newTemplate: TemplateData = {
        id: res.template_id,
        name: res.name,
        file_type: res.file_type || "docx",
        file_size: res.file_size_bytes,
        status: res.status,
        analysis_status: res.analysis_status,
        original_file_path: res.original_file_path,
        created_at: new Date().toISOString(),
      };

      setTemplate(newTemplate);
      setUploadState("ready");
      setStatusMessage("Template ready");
      onTemplateUpdated?.(newTemplate);
    } catch (err: any) {
      setUploadState("error");
      setErrorMessage(
        err.message || "Template upload failed. Please try again with a valid DOCX document."
      );
    }
  };

  const pollJobStatus = (jobId: string, templateId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const job = await apiClient.getProjectTemplateJob(projectId, templateId, jobId);
        if (job) {
          setAnalysisProgress(job.progress || 0);
          setCurrentStep(job.current_step ? job.current_step.replace(/_/g, " ") : "");

          if (job.status === "completed") {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setIsAnalyzing(false);
            setUploadState("analyzed");
            setStatusMessage("Template ready");
            await loadAnalysis(templateId);
            setTemplate((prev) => prev ? { ...prev, status: "analyzed", analysis_status: "completed" } : null);
          } else if (job.status === "failed") {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setIsAnalyzing(false);
            setUploadState("error");
            setErrorMessage(job.error_message || "Template analysis encountered an issue.");
          }
        }
      } catch {
        // Continue polling until timeout or success
      }
    }, 1500);
  };

  const handleAnalyzeTemplate = async () => {
    if (!template || !projectId) return;

    setIsAnalyzing(true);
    setUploadState("analyzing");
    setErrorMessage(null);
    setStatusMessage("Analyzing template...");
    setAnalysisProgress(10);
    setCurrentStep("Analyzing template structure...");

    try {
      const res = await apiClient.analyzeProjectTemplate(projectId, template.id);
      setStatusMessage(res.message || "Template analysis queued. Ready for processing.");
      const updatedTemplate: TemplateData = {
        ...template,
        status: "analyzing",
        analysis_status: "pending",
      };
      setTemplate(updatedTemplate);
      onTemplateUpdated?.(updatedTemplate);

      if (res.job_id) {
        pollJobStatus(res.job_id, template.id);
      }
    } catch (err: any) {
      setIsAnalyzing(false);
      setUploadState("ready");
      setErrorMessage(err.message || "Failed to start template analysis. Please try again.");
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return "Unknown size";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const schema = analysisData?.schema_data;
  const sections = schema?.sections || [];
  const typography = schema?.typography || {};
  const geometry = schema?.geometry || {};
  const headings = schema?.heading_rules || typography?.headings || {};

  return (
    <div
      className="w-full rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 shadow-sm transition-all duration-200"
      aria-labelledby="template-section-title"
    >
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".docx"
        className="sr-only"
        id={`template-upload-input-${projectId}`}
        onChange={handleFileChange}
        tabIndex={-1}
        aria-hidden="true"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-100 dark:border-zinc-900">
        <div>
          <h3
            id="template-section-title"
            className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2"
          >
            <FileCode2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            Upload College Template (.docx)
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-xl">
            Upload the report format provided by your college (.docx). ARM parses its layout, typography,
            and structure to guarantee 100% compliant report generation.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-mono text-zinc-500 bg-zinc-100 dark:bg-zinc-900 px-2 py-1 rounded">
            Supported format: .docx
          </span>
        </div>
      </div>

      {/* Screen Reader Live Status */}
      <div className="sr-only" role="status" aria-live="polite">
        {statusMessage || errorMessage || (template ? "Template ready" : "No template uploaded")}
      </div>

      {/* Main Content Area */}
      <div className="mt-5 space-y-4">
        {/* Error Alert Banner */}
        {errorMessage && (
          <div
            role="alert"
            className="rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 p-4 flex items-start gap-3 transition-all"
          >
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-xs font-semibold text-red-900 dark:text-red-300">
                Upload or Analysis Error
              </h4>
              <p className="text-xs text-red-700 dark:text-red-400 mt-0.5">{errorMessage}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleTriggerPicker}
              className="text-xs shrink-0 border-red-200 hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900/50"
            >
              Try Again
            </Button>
          </div>
        )}

        {/* Uploading Progress State */}
        {uploadState === "uploading" && (
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20 p-6 text-center">
            <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mx-auto mb-2" />
            <p className="text-xs font-medium text-emerald-800 dark:text-emerald-300">{statusMessage}</p>
            <p className="text-[11px] text-zinc-500 mt-1">
              Verifying file signatures and transferring to private storage...
            </p>
          </div>
        )}

        {/* Empty Dropzone State */}
        {!template && uploadState !== "uploading" && (
          <div
            onClick={handleTriggerPicker}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleTriggerPicker();
              }
            }}
            tabIndex={0}
            role="button"
            aria-label="Upload College Template (.docx)"
            className="rounded-xl border-2 border-dashed border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 dark:hover:border-emerald-500 bg-zinc-50/50 dark:bg-zinc-900/50 hover:bg-emerald-50/20 dark:hover:bg-emerald-950/10 p-8 text-center cursor-pointer transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          >
            <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center mx-auto mb-3">
              <Upload className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
              Select or Drop College Template Document (.docx)
            </h4>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto mt-1 mb-4">
              Upload your department report guideline document (.docx) to lock layout styles.
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleTriggerPicker();
              }}
              className="text-xs font-medium focus-visible:ring-2 focus-visible:ring-emerald-500"
              aria-label="Upload College Template (.docx)"
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" />
              Upload College Template (.docx)
            </Button>
          </div>
        )}

        {/* Template Card */}
        {template && uploadState !== "uploading" && (
          <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 p-5 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                      College Template
                    </span>
                    {template.is_locked || template.status === "locked" ? (
                      <Badge
                        variant="outline"
                        className="text-[10px] uppercase font-mono px-1.5 py-0 border-emerald-500 text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/60 flex items-center gap-1 font-bold"
                      >
                        <Lock className="w-2.5 h-2.5" />
                        LOCKED
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-[10px] uppercase font-mono px-1.5 py-0 border-emerald-500/30 text-emerald-700 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/30"
                      >
                        {template.file_type || "DOCX"}
                      </Badge>
                    )}
                  </div>
                  <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mt-0.5 break-all">
                    {template.name}
                  </h4>
                  <div className="flex items-center gap-3 text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                    <span>Size: {formatFileSize(template.file_size)}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1 font-medium">
                      {template.is_locked || template.status === "locked" ? (
                        <span className="text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          Locked & Authoritative
                        </span>
                      ) : uploadState === "analyzed" ? (
                        <span className="text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          Template Understood
                        </span>
                      ) : isAnalyzing || template.status === "analyzing" ? (
                        <span className="text-blue-600 dark:text-blue-400 flex items-center gap-1">
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                          Analyzing ({analysisProgress}%)
                        </span>
                      ) : (
                        <span className="text-zinc-600 dark:text-zinc-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-zinc-400" />
                          Ready for analysis
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleTriggerPicker}
                  className="text-xs font-medium border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  aria-label="Replace College Template"
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                  Replace Template
                </Button>

                {(uploadState === "analyzed" || template.status === "analyzed" || template.is_locked || template.status === "locked") && (
                  <Button
                    size="sm"
                    onClick={() => setIsReviewOpen(true)}
                    className={`text-xs font-medium text-white flex items-center gap-1.5 ${
                      template.is_locked || template.status === "locked"
                        ? "bg-emerald-600 hover:bg-emerald-700"
                        : "bg-blue-600 hover:bg-blue-700"
                    }`}
                    aria-label={template.is_locked || template.status === "locked" ? "View Locked Template Structure" : "Review & Lock Template"}
                  >
                    {template.is_locked || template.status === "locked" ? (
                      <>
                        <ShieldCheck className="w-3.5 h-3.5" />
                        View Locked Structure
                      </>
                    ) : (
                      <>
                        <Sliders className="w-3.5 h-3.5" />
                        Review & Lock
                      </>
                    )}
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="primary"
                  onClick={handleAnalyzeTemplate}
                  isLoading={isAnalyzing || template.status === "analyzing"}
                  disabled={isAnalyzing || template.status === "analyzing"}
                  className="text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white"
                  aria-label="Analyze College Template"
                >
                  <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                  {uploadState === "analyzed" ? "Re-analyze" : isAnalyzing ? "Analyzing..." : "Analyze Template"}
                </Button>
              </div>
            </div>

            {/* Analysis Progress Bar */}
            {(isAnalyzing || template.status === "analyzing") && uploadState !== "analyzed" && (
              <div className="mt-4 pt-4 border-t border-zinc-200/60 dark:border-zinc-800/60">
                <div className="flex justify-between items-center text-xs mb-1.5 font-medium">
                  <span className="text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                    <Loader2 className="w-3 h-3 animate-spin text-emerald-600" />
                    {currentStep || "Extracting template intelligence..."}
                  </span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                    {analysisProgress}%
                  </span>
                </div>
                <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-600 h-full transition-all duration-300 ease-out"
                    style={{ width: `${analysisProgress}%` }}
                    role="progressbar"
                    aria-valuenow={analysisProgress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              </div>
            )}

            {/* Stage 3: Structured Template Intelligence Summary Card */}
            {uploadState === "analyzed" && schema && (
              <div className="mt-5 pt-4 border-t border-zinc-200/80 dark:border-zinc-800/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Template Analysis Summary
                  </h5>
                  <span className="text-[11px] text-zinc-500 font-mono">
                    Schema v{schema.schema_version || "1.0.0"} • Parser v{schema.parser_version || "1.0.0"}
                  </span>
                </div>

                {/* Grid: Document Dimensions & Geometry */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white dark:bg-zinc-950 p-3 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 text-xs">
                  <div>
                    <span className="text-zinc-400 text-[10px] uppercase font-mono block">Format</span>
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {schema.document?.file_type?.toUpperCase() || template.file_type.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[10px] uppercase font-mono block">Page Count</span>
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {schema.document?.page_count || 1} pages
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[10px] uppercase font-mono block">Page Size</span>
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {geometry.page_size || "A4"} ({geometry.orientation || "portrait"})
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[10px] uppercase font-mono block">Margins (T/B/L/R)</span>
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {geometry.margins ? `${geometry.margins.top_mm}/${geometry.margins.bottom_mm}/${geometry.margins.left_mm}/${geometry.margins.right_mm}mm` : "Standard"}
                    </span>
                  </div>
                </div>

                {/* Typography & Spacing Rules */}
                <div className="bg-white dark:bg-zinc-950 p-3 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 text-xs space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold text-zinc-800 dark:text-zinc-200 text-xs">
                    <Type className="w-3.5 h-3.5 text-zinc-500" />
                    Typography & Spacing Rules
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
                    <div>
                      <span className="text-zinc-400 block text-[10px]">Body Typography:</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {typography.default_font || "Times New Roman"}, {typography.default_size_pt || 12} pt
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 block text-[10px]">Line & Paragraph Spacing:</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {typography.line_spacing || 1.5}x • After: {typography.paragraph_after_pt || 6} pt
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 block text-[10px]">Heading 1 Style:</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {headings.level_1 ? `${headings.level_1.font_name}, ${headings.level_1.size_pt} pt (${headings.level_1.alignment})` : "14 pt Bold"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Detected Academic Sections */}
                {sections.length > 0 && (
                  <div className="bg-white dark:bg-zinc-950 p-3 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-semibold text-zinc-800 dark:text-zinc-200 text-xs">
                        <Layers className="w-3.5 h-3.5 text-zinc-500" />
                        Detected Institutional Sections ({sections.length})
                      </div>
                      <span className="text-[10px] text-zinc-400">Hierarchical Order</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {sections.map((sec: any, idx: number) => (
                        <Badge
                          key={sec.id || idx}
                          variant="secondary"
                          className="text-[11px] py-0.5 px-2 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center gap-1"
                        >
                          <span className="font-mono text-zinc-400 text-[10px]">{idx + 1}.</span>
                          <span className="font-medium text-zinc-800 dark:text-zinc-200">{sec.detected_title}</span>
                          <span className="text-[9px] uppercase font-mono text-emerald-700 dark:text-emerald-400 ml-1">
                            [{sec.semantic_role || "SECTION"}]
                          </span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Structural Elements (Tables, Images, Numbering) */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div className="bg-white dark:bg-zinc-950 p-2.5 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 flex items-center gap-2">
                    <TableIcon className="w-4 h-4 text-zinc-500 shrink-0" />
                    <div>
                      <span className="text-zinc-400 text-[10px] block">Tables</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {schema.tables?.detected_count || 0} detected
                      </span>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-zinc-950 p-2.5 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 flex items-center gap-2">
                    <ImageIcon className="w-4 h-4 text-zinc-500 shrink-0" />
                    <div>
                      <span className="text-zinc-400 text-[10px] block">Images & Figures</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {schema.images?.detected_count || 0} detected
                      </span>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-zinc-950 p-2.5 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80 flex items-center gap-2">
                    <Info className="w-4 h-4 text-zinc-500 shrink-0" />
                    <div>
                      <span className="text-zinc-400 text-[10px] block">Numbering Pattern</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">
                        {schema.numbering?.detected_patterns?.length ? schema.numbering.detected_patterns.join(", ") : "Standard Multi-level"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Warnings / Fallbacks */}
                {schema.warnings && schema.warnings.length > 0 && (
                  <div className="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/60 rounded-lg p-3 text-xs text-amber-800 dark:text-amber-300">
                    <span className="font-semibold block mb-1">Analyzer Notices:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                      {schema.warnings.map((w: string, i: number) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Stage 4: Template Review & Lock Modal */}
        {template && (
          <TemplateReviewModal
            isOpen={isReviewOpen}
            onClose={() => setIsReviewOpen(false)}
            projectId={projectId}
            templateId={template.id}
            templateName={template.name}
            isInitiallyLocked={Boolean(template.is_locked || template.status === "locked")}
            onLockSuccess={() => {
              setTemplate((prev) => (prev ? { ...prev, status: "locked", is_locked: true } : null));
              setUploadState("analyzed");
              loadTemplate();
            }}
          />
        )}
      </div>
    </div>
  );
}
