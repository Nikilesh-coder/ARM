"use client";

import React, { useState, useRef } from "react";
import { apiClient, TemplateDTO } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  FileCode2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Building,
  GraduationCap,
  Sparkles,
  ShieldCheck,
  Lock,
  ArrowRight,
  Sliders,
  Type,
  Image as ImageIcon,
  Check,
  RefreshCw,
  Eye,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CustomCollegeTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTemplateSaved: (template: TemplateDTO) => void;
}

export const REPORT_TYPES = [
  { value: "Seminar", label: "Seminar Survey & Research Report" },
  { value: "Major Project", label: "Major / Capstone Project Report" },
  { value: "Mini Project", label: "Mini Project Report" },
  { value: "Internship", label: "Industrial Internship Report" },
  { value: "Thesis", label: "M.Tech / MS Academic Thesis" },
  { value: "Research", label: "Research Paper & Survey" },
  { value: "Weekly Report", label: "Weekly Laboratory Project Report" },
  { value: "Other", label: "Other College Report" },
];

export const CANONICAL_ARM_FIELDS = [
  { key: "project_title", label: "Project Title" },
  { key: "student_name", label: "Student Name" },
  { key: "roll_number", label: "Roll Number / Reg No" },
  { key: "guide_name", label: "Guide / Supervisor Name" },
  { key: "department", label: "Department" },
  { key: "institution", label: "College / University Name" },
  { key: "academic_year", label: "Academic Year" },
  { key: "introduction", label: "Introduction (Chapter 1)" },
  { key: "objectives", label: "Objectives" },
  { key: "problem_statement", label: "Problem Statement" },
  { key: "methodology", label: "Methodology (Chapter 2)" },
  { key: "technologies", label: "Technologies / Tools" },
  { key: "implementation", label: "Implementation (Chapter 3)" },
  { key: "results", label: "Results & Discussion" },
  { key: "advantages", label: "Advantages" },
  { key: "limitations", label: "Limitations" },
  { key: "future_scope", label: "Future Scope" },
  { key: "conclusion", label: "Conclusion" },
  { key: "references", label: "References" },
];

export function CustomCollegeTemplateModal({
  isOpen,
  onClose,
  onTemplateSaved,
}: CustomCollegeTemplateModalProps) {
  // Step state: 1: upload -> 2: info -> 3: analyzing -> 4: mapping -> 5: done
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Template Info
  const [templateName, setTemplateName] = useState("");
  const [institution, setInstitution] = useState("");
  const [department, setDepartment] = useState("");
  const [reportType, setReportType] = useState("Seminar");

  // Analysis result
  const [analyzedTemplate, setAnalyzedTemplate] = useState<any>(null);
  const [fieldMappings, setFieldMappings] = useState<any[]>([]);
  const [imageMappings, setImageMappings] = useState<any[]>([]);

  // Status
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [analysisStepText, setAnalysisStepText] = useState<string>("Uploading template...");

  if (!isOpen) return null;

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    const isDocx = file.name.toLowerCase().endsWith(".docx");
    if (!isDocx) {
      setErrorMessage("Unsupported file format. Only DOCX college templates (.docx) are currently supported.");
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage("File is too large. Maximum supported template size is 25MB.");
      return;
    }
    setSelectedFile(file);
    if (!templateName) {
      const clean = file.name.replace(/\.docx$/i, "").replace(/[_-]/g, " ");
      setTemplateName(clean);
    }
    setStep(2);
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a valid .docx college template file.");
      return;
    }
    if (!templateName.trim()) {
      setErrorMessage("Please provide a name for this college template.");
      return;
    }

    setErrorMessage(null);
    setIsUploading(true);
    setAnalysisStepText("Uploading template...");
    setStep(3); // Analyzing screen

    const t1 = setTimeout(() => {
      setAnalysisStepText("Analyzing template...");
    }, 500);

    try {
      const res = await apiClient.uploadCustomCollegeTemplate(selectedFile, {
        name: templateName.trim(),
        institution: institution.trim() || undefined,
        department: department.trim() || undefined,
        report_type: reportType,
      });

      if (t1) clearTimeout(t1);

      if (res && res.template) {
        setAnalysisStepText("Template ready");
        setAnalyzedTemplate(res.template);
        setFieldMappings(res.template.field_mapping || []);
        setImageMappings(res.template.image_mapping || []);
        setTimeout(() => {
          setStep(4); // Mapping screen
        }, 400);
      } else {
        throw new Error("Invalid response from server.");
      }
    } catch (err: any) {
      if (t1) clearTimeout(t1);
      setErrorMessage(
        err.message ||
          "Failed to analyze college template. Please ensure the DOCX file is valid and uncorrupted."
      );
      setStep(2);
    } finally {
      setIsUploading(false);
    }
  };

  const handleFieldMappingChange = (index: number, key: string, value: any) => {
    setFieldMappings((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [key]: value };
      return copy;
    });
  };

  const handleImageMappingChange = (index: number, key: string, value: any) => {
    setImageMappings((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [key]: value };
      return copy;
    });
  };

  const handleSaveTemplate = async () => {
    if (!analyzedTemplate?.id) return;
    setIsSaving(true);
    setErrorMessage(null);

    try {
      const updated = await apiClient.updateCustomTemplateMapping(analyzedTemplate.id, {
        field_mapping: fieldMappings,
        image_mapping: imageMappings,
      });

      setSuccessMessage(`College template "${templateName}" saved and ready for report generation!`);
      if (typeof window !== "undefined") {
        localStorage.setItem("arm_selected_template_id", analyzedTemplate.id);
      }
      setTimeout(() => {
        onTemplateSaved(updated.template || analyzedTemplate);
        onClose();
      }, 900);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to save template mappings.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-900/50 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <FileCode2 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
                Upload College Template
                <Badge variant="outline" className="text-[10px] font-normal border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                  DOCX Source of Truth
                </Badge>
              </h2>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                ARM preserves logos, borders, headers, and page size without redesigning
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Stepper progress */}
        <div className="px-6 py-2.5 border-b border-zinc-100 dark:border-zinc-900 bg-zinc-50/30 dark:bg-zinc-900/20 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                step >= 1 ? "bg-emerald-500 text-white" : "bg-zinc-200 dark:bg-zinc-800 text-zinc-500"
              )}
            >
              1
            </span>
            <span className={step >= 1 ? "font-medium text-zinc-900 dark:text-white" : "text-zinc-400"}>
              Upload File
            </span>
          </div>
          <div className="w-8 h-[1px] bg-zinc-200 dark:bg-zinc-800" />
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                step >= 2 ? "bg-emerald-500 text-white" : "bg-zinc-200 dark:bg-zinc-800 text-zinc-500"
              )}
            >
              2
            </span>
            <span className={step >= 2 ? "font-medium text-zinc-900 dark:text-white" : "text-zinc-400"}>
              Template Info
            </span>
          </div>
          <div className="w-8 h-[1px] bg-zinc-200 dark:bg-zinc-800" />
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                step >= 4 ? "bg-emerald-500 text-white" : "bg-zinc-200 dark:bg-zinc-800 text-zinc-500"
              )}
            >
              3
            </span>
            <span className={step >= 4 ? "font-medium text-zinc-900 dark:text-white" : "text-zinc-400"}>
              Map Fields & Protect Fixed
            </span>
          </div>
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* STEP 1: UPLOAD FILE */}
          {step === 1 && (
            <div className="space-y-4 py-2">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileSelect(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3",
                  isDragging
                    ? "border-emerald-500 bg-emerald-500/5 dark:bg-emerald-500/10"
                    : "border-zinc-200 dark:border-zinc-800 hover:border-emerald-500/60 hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileSelect(e.target.files[0]);
                    }
                  }}
                />
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                  <Upload className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-white">
                    Upload College Template (.docx)
                  </h3>
                  <p className="text-xs text-zinc-500 mt-1">
                    or click to choose file from your device (Max 25MB)
                  </p>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="text-[10px] text-zinc-500 border-zinc-200 dark:border-zinc-800">
                    Supported format: .docx
                  </Badge>
                  <Badge variant="outline" className="text-[10px] text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                    Preserves original layout & logos
                  </Badge>
                </div>
              </div>

              {/* Preservation reassurance card */}
              <div className="p-3.5 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-zinc-50/70 dark:bg-zinc-900/40 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-200">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span>ARM Absolute Template Preservation Guarantee</span>
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  ARM does NOT convert your document into plain text or redesign it from scratch. Your uploaded
                  template (.docx) will serve as the exact master layout source, preserving college logos, page borders, headers,
                  footers, and page sizes.
                </p>
              </div>
            </div>
          )}

          {/* STEP 2: TEMPLATE INFORMATION */}
          {step === 2 && (
            <div className="space-y-4 py-1">
              {/* Selected File badge */}
              {selectedFile && (
                <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <FileCode2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <div>
                      <p className="text-xs font-medium text-zinc-900 dark:text-white">{selectedFile.name}</p>
                      <p className="text-[10px] text-zinc-500">
                        {(selectedFile.size / 1024).toFixed(1)} KB • DOCX format
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
                    onClick={() => {
                      setSelectedFile(null);
                      setStep(1);
                    }}
                  >
                    Change File
                  </Button>
                </div>
              )}

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1">
                    <span>Template Name</span>
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ABC College Capstone Report Template"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      College / Institution
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Sri Venkateswara College of Engineering"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      Department (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Electrical & Electronics Engineering"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    Report Type
                  </label>
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                  >
                    {REPORT_TYPES.map((rt) => (
                      <option key={rt.value} value={rt.value}>
                        {rt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: ANALYZING STATE */}
          {step === 3 && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-500 animate-pulse">
                  <Sparkles className="w-8 h-8 animate-spin" style={{ animationDuration: "3s" }} />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white">
                  {analysisStepText}
                </h3>
                <p className="text-xs text-zinc-500 mt-1 max-w-sm">
                  Extracting document geometry, isolating fixed logos and borders, and discovering candidate text and image fields.
                </p>
              </div>
              <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-600 dark:text-emerald-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{analysisStepText}</span>
              </div>
            </div>
          )}

          {/* STEP 4: MAPPING & FIXED PROTECTION UI */}
          {step === 4 && analyzedTemplate && (
            <div className="space-y-5">
              {/* Geometry & Fixed Elements Banner */}
              <div className="p-3.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-900/40 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-semibold text-zinc-900 dark:text-white">
                      Fixed Elements (Immutable by Default)
                    </span>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                    Protected
                  </Badge>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-zinc-500 pt-1">
                  <div className="p-2 rounded bg-white dark:bg-zinc-850 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-400 block text-[9px] uppercase font-mono">Page Size</span>
                    <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                      {analyzedTemplate.page_settings?.width_in}&quot; x {analyzedTemplate.page_settings?.height_in}&quot;
                    </span>
                  </div>
                  <div className="p-2 rounded bg-white dark:bg-zinc-850 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-400 block text-[9px] uppercase font-mono">Margins</span>
                    <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                      L: {analyzedTemplate.page_settings?.left_margin_in}&quot;, R: {analyzedTemplate.page_settings?.right_margin_in}&quot;
                    </span>
                  </div>
                  <div className="p-2 rounded bg-white dark:bg-zinc-850 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-400 block text-[9px] uppercase font-mono">College Logo</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">Preserved</span>
                  </div>
                  <div className="p-2 rounded bg-white dark:bg-zinc-850 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-400 block text-[9px] uppercase font-mono">Page Borders</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">Preserved</span>
                  </div>
                </div>
              </div>

              {/* Text Fields Mapping Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-zinc-900 dark:text-white flex items-center gap-1.5">
                    <Type className="w-3.5 h-3.5 text-blue-500" />
                    <span>Candidate Text Fields</span>
                  </h4>
                  <span className="text-[10px] text-zinc-500 font-mono">
                    {fieldMappings.filter((f) => f.action === "replace").length} of {fieldMappings.length} marked Replace
                  </span>
                </div>

                <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-50 dark:bg-zinc-900/80 border-b border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500 font-medium">
                      <tr>
                        <th className="py-2 px-3">Template Element</th>
                        <th className="py-2 px-3">ARM Field</th>
                        <th className="py-2 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 dark:divide-zinc-850">
                      {fieldMappings.map((fm, idx) => (
                        <tr key={fm.id || idx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30">
                          <td className="py-2.5 px-3">
                            <span className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                              {fm.template_element}
                            </span>
                            {fm.location && (
                              <span className="block text-[10px] text-zinc-400">{fm.location}</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <select
                              value={fm.arm_field}
                              onChange={(e) => handleFieldMappingChange(idx, "arm_field", e.target.value)}
                              className="px-2 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white font-medium focus:ring-1 focus:ring-emerald-500"
                            >
                              {CANONICAL_ARM_FIELDS.map((af) => (
                                <option key={af.key} value={af.key}>
                                  {af.label}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <select
                              value={fm.action}
                              onChange={(e) => handleFieldMappingChange(idx, "action", e.target.value)}
                              className={cn(
                                "px-2.5 py-1 rounded-lg border text-xs font-semibold focus:outline-none",
                                fm.action === "replace"
                                  ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800"
                                  : fm.action === "fixed"
                                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700"
                                  : "bg-zinc-50 dark:bg-zinc-900 text-zinc-400 border-zinc-200 dark:border-zinc-800"
                              )}
                            >
                              <option value="replace">Replace</option>
                              <option value="fixed">Fixed</option>
                              <option value="ignore">Ignore</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Images Mapping Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-zinc-900 dark:text-white flex items-center gap-1.5">
                    <ImageIcon className="w-3.5 h-3.5 text-purple-500" />
                    <span>Candidate Images & Logos</span>
                  </h4>
                  <span className="text-[10px] text-zinc-500 font-mono">
                    {imageMappings.filter((im) => im.action === "replace").length} marked Replace
                  </span>
                </div>

                <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-50 dark:bg-zinc-900/80 border-b border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500 font-medium">
                      <tr>
                        <th className="py-2 px-3">Template Image</th>
                        <th className="py-2 px-3">ARM Image Field</th>
                        <th className="py-2 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 dark:divide-zinc-850">
                      {imageMappings.map((im, idx) => (
                        <tr key={im.id || idx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30">
                          <td className="py-2.5 px-3">
                            <span className="font-medium text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                              {im.label}
                              {im.is_logo && (
                                <Badge variant="outline" className="text-[9px] border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                                  Logo (Fixed)
                                </Badge>
                              )}
                            </span>
                            {im.description && (
                              <span className="block text-[10px] text-zinc-400">{im.description}</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <select
                              value={im.arm_image_field}
                              onChange={(e) => handleImageMappingChange(idx, "arm_image_field", e.target.value)}
                              className="px-2 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white font-medium focus:ring-1 focus:ring-emerald-500"
                            >
                              <option value="image_1">image_1 (Primary Diagram)</option>
                              <option value="image_2">image_2 (Secondary Diagram)</option>
                              <option value="image_3">image_3 (Tertiary Diagram)</option>
                            </select>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <select
                              value={im.action}
                              onChange={(e) => handleImageMappingChange(idx, "action", e.target.value)}
                              className={cn(
                                "px-2.5 py-1 rounded-lg border text-xs font-semibold focus:outline-none",
                                im.action === "replace"
                                  ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800"
                                  : im.action === "fixed"
                                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700"
                                  : "bg-zinc-50 dark:bg-zinc-900 text-zinc-400 border-zinc-200 dark:border-zinc-800"
                              )}
                            >
                              <option value="fixed">Fixed</option>
                              <option value="replace">Replace</option>
                              <option value="ignore">Ignore</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-3.5 border-t border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/50 flex items-center justify-between shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={isUploading || isSaving}
            className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
          >
            Cancel
          </Button>

          <div className="flex items-center gap-2">
            {step === 2 && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleUploadAndAnalyze}
                disabled={isUploading || !templateName.trim()}
                className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                Analyze Template <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            )}

            {step === 4 && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setStep(2)}
                  disabled={isSaving}
                  className="text-xs"
                >
                  Edit Details
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSaveTemplate}
                  disabled={isSaving}
                  className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Saving Template...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Save Template
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
