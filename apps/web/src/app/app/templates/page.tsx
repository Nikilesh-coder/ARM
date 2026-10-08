"use client";

import React, { useState, useEffect } from "react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/arm/theme-toggle";
import { CollegeTemplateUpload, TemplateData } from "@/components/arm/college-template-upload";
import { MasterTemplateCard } from "@/components/arm/master-template-card";
import { CustomCollegeTemplateModal } from "@/components/arm/custom-college-template-modal";
import { apiClient, ProjectDTO, TemplateDTO } from "@/lib/api-client";
import {
  FileCode2,
  FolderGit2,
  Menu,
  ChevronDown,
  Layers,
  Plus,
  Trash2,
  Lock,
  Building,
  CheckCircle2,
  FileCheck,
  ShieldCheck,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export default function TemplatesPage() {
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [activeTemplate, setActiveTemplate] = useState<TemplateData | null>(null);
  const [customTemplates, setCustomTemplates] = useState<TemplateDTO[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isCustomUploadOpen, setIsCustomUploadOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
    fetchTemplates();
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("arm_selected_template_id");
      if (stored) {
        setSelectedTemplateId(stored);
      } else {
        const actProjStr = localStorage.getItem("arm_active_project");
        if (actProjStr) {
          try {
            const act = JSON.parse(actProjStr);
            if (act.template_id) {
              setSelectedTemplateId(act.template_id);
              localStorage.setItem("arm_selected_template_id", act.template_id);
            }
          } catch {}
        }
      }
    }
  }, []);

  const fetchProjects = async () => {
    setIsLoadingProjects(true);
    try {
      const data = await apiClient.getProjects();
      setProjects(data || []);
      if (data && data.length > 0 && data[0].id) {
        setSelectedProjectId(data[0].id);
      }
    } catch {
      setProjects([]);
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const list = await apiClient.getTemplates();
      // Filter custom uploaded templates
      const customs = (list || []).filter(
        (t) => !t.is_master && !t.is_institution_preset && t.id !== "00000000-0000-0000-0000-000000000001"
      );
      setCustomTemplates(customs);
    } catch {
      setCustomTemplates([]);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    try {
      await apiClient.deleteCustomTemplate(templateId);
      setCustomTemplates((prev) => prev.filter((t) => t.id !== templateId));
    } catch (err) {
      console.error("Failed to delete custom template:", err);
    } finally {
      setDeleteId(null);
    }
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <div className="flex h-screen w-full bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 overflow-hidden transition-colors duration-300">
      <ArmSidebar
        isMobileOpen={mobileMenuOpen}
        onToggleMobile={() => setMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-black transition-colors duration-300">
        {/* Top Bar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 px-6 flex items-center justify-between shrink-0 bg-white/80 dark:bg-black/80 backdrop-blur-md transition-colors duration-300">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight flex items-center gap-2">
              <FileCode2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Templates & Guidelines
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Primary Action: + Upload College Template */}
            <Button
              onClick={() => setIsCustomUploadOpen(true)}
              className="h-8 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Upload College Template</span>
            </Button>

            {/* Project Selector */}
            {projects.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500 hidden sm:inline">Active Project:</span>
                <div className="relative">
                  <select
                    value={selectedProjectId}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    className="appearance-none pl-3 pr-8 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-900 dark:text-zinc-100 font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    aria-label="Select Project for Template"
                  >
                    {projects.map((proj) => (
                      <option key={proj.id} value={proj.id}>
                        {proj.title}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-3.5 h-3.5 text-zinc-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>
            )}
            <ThemeToggle />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-6">
          {/* Master College Template (Configured Once • Automatically Reused) */}
          <MasterTemplateCard />

          {/* User-Uploaded Custom College Templates Section */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
                  <span>My Uploaded College Templates</span>
                  <Badge variant="outline" className="text-[10px] font-normal border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                    {customTemplates.length} Custom
                  </Badge>
                </h3>
                <p className="text-[11px] text-zinc-500">
                  Your uploaded college templates are used as the exact source of truth during report generation.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsCustomUploadOpen(true)}
                className="h-7 text-xs flex items-center gap-1.5 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>+ Upload College Template</span>
              </Button>
            </div>

            {isLoadingTemplates ? (
              <div className="py-6 text-center text-xs text-zinc-500">
                Loading uploaded templates...
              </div>
            ) : customTemplates.length === 0 ? (
              <div className="p-6 rounded-2xl border border-dashed border-zinc-200 dark:border-zinc-800 text-center bg-zinc-50/50 dark:bg-zinc-900/20 space-y-2">
                <FileCode2 className="w-8 h-8 text-zinc-400 mx-auto" />
                <h4 className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  No custom college templates uploaded yet
                </h4>
                <p className="text-[11px] text-zinc-500 max-w-sm mx-auto">
                  Upload your department or university report template (.docx). ARM will preserve logos, borders, headers, and page sizes without redesigning.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsCustomUploadOpen(true)}
                  className="mt-2 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Upload College Template
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {customTemplates.map((tpl) => (
                  <div
                    key={tpl.id}
                    className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-sm space-y-3 relative group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                          <FileCheck className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-zinc-900 dark:text-white line-clamp-1">
                            {tpl.name}
                          </h4>
                          <p className="text-[10px] text-zinc-500 flex items-center gap-1.5 mt-0.5">
                            <Building className="w-3 h-3 text-zinc-400" />
                            <span>{tpl.institution || "College / Institution"}</span>
                            {tpl.department && <span>• {tpl.department}</span>}
                          </p>
                        </div>
                      </div>

                      <Badge className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                        Ready
                      </Badge>
                    </div>

                    {/* Geometry & Preservation pill */}
                    <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono bg-zinc-50 dark:bg-zinc-850 p-2 rounded-lg border border-zinc-100 dark:border-zinc-800">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                      <span className="line-clamp-1">
                        {tpl.page_settings
                          ? `${tpl.page_settings.width_in}"x${tpl.page_settings.height_in}" (${tpl.page_settings.orientation}) • Logos Preserved`
                          : "Original Geometry & Logos Preserved"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] pt-1 border-t border-zinc-100 dark:border-zinc-850">
                      <span className="text-[10px] text-zinc-400">
                        Type: {tpl.report_type || "Seminar"} • .docx
                      </span>
                      <div className="flex items-center gap-2">
                        {/* SELECT / USE TEMPLATE BUTTON */}
                        <button
                          onClick={async () => {
                            setSelectedTemplateId(tpl.id);
                            if (typeof window !== "undefined") {
                              localStorage.setItem("arm_selected_template_id", tpl.id);
                              const actProjStr = localStorage.getItem("arm_active_project");
                              if (actProjStr) {
                                try {
                                  const act = JSON.parse(actProjStr);
                                  act.template_id = tpl.id;
                                  localStorage.setItem("arm_active_project", JSON.stringify(act));
                                } catch {}
                              }
                            }
                            if (selectedProjectId) {
                              try {
                                await apiClient.updateProject(selectedProjectId, { template_id: tpl.id });
                              } catch (e) {
                                console.warn("Failed to update project template:", e);
                              }
                            }
                          }}
                          className={cn(
                            "inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded-md transition shadow-xs cursor-pointer",
                            selectedTemplateId === tpl.id
                              ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                              : "bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200"
                          )}
                          title="Select this template for report generation"
                        >
                          {selectedTemplateId === tpl.id ? (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                              <span>Active Template</span>
                            </>
                          ) : (
                            <span>Use This Template</span>
                          )}
                        </button>

                        {/* DIAGNOSTIC BUTTON: DOWNLOAD ORIGINAL TEMPLATE */}
                        <a
                          href={`${API_BASE_URL}/api/v1/templates/${tpl.id}/raw-download`}
                          target="_blank"
                          rel="noopener noreferrer"
                          download
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white transition shadow-xs cursor-pointer"
                          title="Download the exact raw uploaded template file"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download Original Template</span>
                        </a>
                        <button
                          onClick={() => handleDeleteTemplate(tpl.id)}
                          className="text-zinc-400 hover:text-red-500 p-1 rounded transition"
                          title="Delete template"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {isLoadingProjects ? (
            <div className="py-10 text-center text-xs text-zinc-500">
              Loading projects and template status...
            </div>
          ) : projects.length === 0 ? (
            <div className="py-6">
              <EmptyState
                icon={FolderGit2}
                title="Create a project to bind this template"
                description="Your college master template is locked and ready. Create a project to automatically generate reports with these 20 fields."
                actionLabel="Go to Projects"
                onAction={() => (window.location.href = "/app/projects")}
              />
            </div>
          ) : (
            <div className="space-y-6 pt-2">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-white">
                    Project-Specific College Uploads & Overrides
                  </h3>
                  <p className="text-[11px] text-zinc-500">
                    If your department requires a specialized syllabus variant, upload it here.
                  </p>
                </div>
              </div>

              {/* Active Project Banner */}
              {selectedProject && (
                <div className="flex items-center justify-between p-4 rounded-xl border border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/70 dark:bg-zinc-900/40">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-mono text-xs font-bold">
                      ARM
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                        {selectedProject.title}
                      </h2>
                      <p className="text-[11px] text-zinc-500 capitalize">
                        Type: {selectedProject.project_type} • Guide: {selectedProject.guide_name || "Unassigned"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-850 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-800">
                    ID: {selectedProject.id?.substring(0, 8)}...
                  </span>
                </div>
              )}

              {/* Stage 2 College Template Upload Interface */}
              <CollegeTemplateUpload
                key={selectedProjectId}
                projectId={selectedProjectId}
                initialTemplate={activeTemplate}
                onTemplateUpdated={(t) => setActiveTemplate(t)}
              />
            </div>
          )}
        </main>
      </div>

      {/* Modal for Custom College Template Upload & Mapping */}
      <CustomCollegeTemplateModal
        isOpen={isCustomUploadOpen}
        onClose={() => setIsCustomUploadOpen(false)}
        onTemplateSaved={async (tpl) => {
          setSelectedTemplateId(tpl.id);
          if (typeof window !== "undefined") {
            localStorage.setItem("arm_selected_template_id", tpl.id);
            const actProjStr = localStorage.getItem("arm_active_project");
            if (actProjStr) {
              try {
                const act = JSON.parse(actProjStr);
                act.template_id = tpl.id;
                localStorage.setItem("arm_active_project", JSON.stringify(act));
              } catch {}
            }
          }
          if (selectedProjectId) {
            try {
              await apiClient.updateProject(selectedProjectId, { template_id: tpl.id });
            } catch (e) {
              console.warn("Failed to update project template:", e);
            }
          }
          fetchTemplates();
        }}
      />
    </div>
  );
}
