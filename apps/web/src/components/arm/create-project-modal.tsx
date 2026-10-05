"use client";

import React, { useState, useEffect } from "react";
import { apiClient, ProjectDTO, TemplateDTO } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FolderGit2,
  FileCode2,
  Building,
  GraduationCap,
  Sparkles,
  X,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: ProjectDTO) => void;
  initialTopic?: string;
}

export const REPORT_TYPES = [
  { value: "capstone", label: "Capstone / Major Project Report" },
  { value: "community_service", label: "Community Service Project (CSP)" },
  { value: "seminar", label: "Seminar Survey & Research Report" },
  { value: "internship", label: "Industrial Internship Report" },
  { value: "thesis", label: "M.Tech / MS Academic Thesis" },
  { value: "weekly_lab", label: "Weekly Laboratory Project Report" },
];

export function CreateProjectModal({
  isOpen,
  onClose,
  onProjectCreated,
  initialTopic = "",
}: CreateProjectModalProps) {
  // Form fields
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState(initialTopic);
  const [instructions, setInstructions] = useState("");
  const [institution, setInstitution] = useState("");
  const [department, setDepartment] = useState("");
  const [reportType, setReportType] = useState("capstone");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [guideName, setGuideName] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");

  // State management
  const [templates, setTemplates] = useState<TemplateDTO[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showCollegeDetails, setShowCollegeDetails] = useState(false);

  // Pre-fill user profile and fetch available templates
  useEffect(() => {
    if (!isOpen) return;

    if (typeof window !== "undefined") {
      const storedInst = localStorage.getItem("arm_user_institution");
      const storedDept = localStorage.getItem("arm_user_department");
      if (storedInst) setInstitution(storedInst);
      if (storedDept) setDepartment(storedDept);
    }

    if (initialTopic && !description) {
      setDescription(initialTopic);
    }

    loadTemplates();
  }, [isOpen, initialTopic]);

  const loadTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const list = await apiClient.getTemplates();
      if (list && list.length > 0) {
        setTemplates(list);
        if (!selectedTemplateId) {
          const storedTid = typeof window !== "undefined" ? localStorage.getItem("arm_selected_template_id") : null;
          if (storedTid && list.some((t) => t.id === storedTid)) {
            setSelectedTemplateId(storedTid);
          } else {
            const master = list.find((t) => t.is_master || t.id === "00000000-0000-0000-0000-000000000001");
            setSelectedTemplateId(master ? master.id : list[0].id);
          }
        }
      } else {
        // Fallback standard presets
        const defaultPresets: TemplateDTO[] = [
          {
            id: "00000000-0000-0000-0000-000000000001",
            name: "Standard College Academic Report Master Template (.docx)",
            file_type: "docx",
            is_institution_preset: true,
            is_master: true,
          },
          {
            id: "tpl_preset_capstone",
            name: "Standard University Capstone Report Template (.docx)",
            file_type: "docx",
            is_institution_preset: true,
          },
          {
            id: "tpl_preset_community_service",
            name: "Community Service Project Presentation & Report (.pdf/.docx)",
            file_type: "docx",
            is_institution_preset: true,
          },
          {
            id: "tpl_preset_ieee_seminar",
            name: "IEEE Double-Column Seminar & Survey Specification (.docx)",
            file_type: "docx",
            is_institution_preset: true,
          },
        ];
        setTemplates(defaultPresets);
        setSelectedTemplateId(defaultPresets[0].id);
      }
    } catch {
      // Graceful fallback for offline mode
      const defaultPresets: TemplateDTO[] = [
        {
          id: "tpl_preset_capstone",
          name: "Standard University Capstone Report Template (.docx)",
          file_type: "docx",
          is_institution_preset: true,
        },
      ];
      setTemplates(defaultPresets);
      setSelectedTemplateId(defaultPresets[0].id);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    // Validation
    const cleanTitle = title.trim();
    const cleanDesc = description.trim();

    if (!cleanTitle) {
      setErrorMsg("Please enter a project or report title.");
      return;
    }
    if (cleanTitle.length < 4) {
      setErrorMsg("Project title must contain at least 4 characters.");
      return;
    }
    if (!cleanDesc) {
      setErrorMsg("Please describe your project topic or problem statement.");
      return;
    }
    if (cleanDesc.length < 10) {
      setErrorMsg("Project description should be at least 10 characters.");
      return;
    }

    setIsSubmitting(true);

    let authUserId: string | undefined = undefined;
    if (typeof window !== "undefined") {
      const storedId = localStorage.getItem("arm_user_id");
      if (storedId) authUserId = storedId;
    }

    try {
      const newProject = await apiClient.createProject({
        title: cleanTitle,
        project_name: cleanTitle,
        report_title: cleanTitle,
        description: cleanDesc,
        abstract_summary: cleanDesc,
        problem_statement: cleanDesc,
        instructions: instructions.trim() || undefined,
        additional_notes: instructions.trim() || undefined,
        institution: institution.trim() || undefined,
        department: department.trim() || undefined,
        project_type: reportType,
        report_type: reportType,
        template_id: selectedTemplateId || undefined,
        guide_name: guideName.trim() || undefined,
        academic_year: academicYear.trim() || "2026-2027",
        user_id: authUserId,
      });

      if (typeof window !== "undefined" && selectedTemplateId) {
        localStorage.setItem("arm_selected_template_id", selectedTemplateId);
      }

      setSuccessMsg(`Project "${cleanTitle}" initialized successfully!`);

      setTimeout(() => {
        onProjectCreated(newProject);
        onClose();
        // Reset state
        setTitle("");
        setDescription("");
        setInstructions("");
        setErrorMsg(null);
        setSuccessMsg(null);
      }, 700);
    } catch (err: any) {
      // Local fallback if backend network error in demo
      const fallbackProject: ProjectDTO = {
        id: "proj_" + Math.random().toString(36).substring(2, 8),
        title: cleanTitle,
        project_name: cleanTitle,
        description: cleanDesc,
        instructions: instructions.trim(),
        institution: institution.trim(),
        department: department.trim(),
        project_type: reportType,
        report_type: reportType,
        template_id: selectedTemplateId,
        guide_name: guideName.trim(),
        academic_year: academicYear.trim(),
        status: "draft",
        created_at: new Date().toISOString(),
      };
      setSuccessMsg(`Project "${cleanTitle}" initialized.`);
      setTimeout(() => {
        onProjectCreated(fallbackProject);
        onClose();
      }, 600);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl my-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 sm:p-7 shadow-2xl text-zinc-900 dark:text-zinc-100 transition-colors duration-300">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-zinc-200 dark:border-zinc-850">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-sm shadow-xs">
              ARM
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-semibold tracking-tight text-zinc-900 dark:text-white flex items-center gap-2">
                Create Academic Project
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                Define your project scope, institution formatting, and report template
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Validation Error Banner */}
        {errorMsg && (
          <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Success Banner */}
        {successMsg && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Project Creation Form */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* 1. Project Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
              <span>Project / Report Title</span>
              <span className="text-red-500 text-[11px]">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Automated IoT Drip Irrigation System with Soil Nutrient Analytics"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/90 text-xs sm:text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>

          {/* 2. Project Description / Topic */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
              <span>Project Description & Topic</span>
              <span className="text-red-500 text-[11px]">*</span>
            </label>
            <textarea
              rows={3}
              required
              placeholder="Detail the technical problem, objective, methodology, and domain scope..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/90 text-xs sm:text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-none"
            />
          </div>

          {/* 3. Report Type & 6. Template Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                Report Type
              </label>
              <div className="relative">
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  disabled={isSubmitting}
                  className="w-full appearance-none pl-3 pr-8 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                >
                  {REPORT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-zinc-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>College Template</span>
                </label>
                {isLoadingTemplates && (
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                    <Loader2 className="w-2.5 h-2.5 animate-spin" /> Loading
                  </span>
                )}
              </div>
              <div className="relative">
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  disabled={isSubmitting || isLoadingTemplates}
                  className="w-full appearance-none pl-3 pr-8 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                >
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.name} {tpl.is_master ? "(Master)" : tpl.is_institution_preset ? "(Preset)" : "(Custom)"}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-zinc-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* 3. Optional Additional Instructions */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center justify-between">
              <span>Optional Additional Instructions</span>
              <span className="text-[10px] text-zinc-500 font-mono">Optional</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Emphasize energy efficiency equations and IEEE citation numbering format"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/90 text-xs text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>

          {/* 4. College / Department Collapsible Section */}
          <div className="pt-2 border-t border-zinc-200 dark:border-zinc-850">
            <button
              type="button"
              onClick={() => setShowCollegeDetails(!showCollegeDetails)}
              className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1.5 cursor-pointer py-1"
            >
              <Building className="w-3.5 h-3.5" />
              <span>
                {showCollegeDetails
                  ? "Hide College & Supervisor Details"
                  : "+ Add College / Department / Supervisor Information"}
              </span>
            </button>

            {showCollegeDetails && (
              <div className="mt-3 p-3.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-900/50 space-y-3 animate-in fade-in duration-200">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">
                      College / University Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. National Institute of Technology"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                      disabled={isSubmitting}
                      className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">
                      Department
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Electrical & Electronics Engineering"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      disabled={isSubmitting}
                      className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">
                      Faculty Guide / Supervisor
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Dr. R. Sireesha, Ph.D"
                      value={guideName}
                      onChange={(e) => setGuideName(e.target.value)}
                      disabled={isSubmitting}
                      className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">
                      Academic Year
                    </label>
                    <input
                      type="text"
                      placeholder="2026-2027"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                      disabled={isSubmitting}
                      className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-zinc-200 dark:border-zinc-850 flex items-center justify-end gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                  Creating Project...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                  Create Project & Report
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
