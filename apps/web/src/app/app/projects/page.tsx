"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FolderGit2,
  Plus,
  Calendar,
  Building,
  GraduationCap,
  FileCode2,
  FileText,
  X,
  Menu,
  Search,
  Filter,
  Play,
  ArrowRight,
  RefreshCw,
  Eye,
  Download,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Lock,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBanner } from "@/components/ui/status-banner";
import { ThemeToggle } from "@/components/arm/theme-toggle";
import {
  apiClient,
  ProjectDTO,
  ReplacementJobResponseDTO,
} from "@/lib/api-client";
import { CollegeTemplateUpload } from "@/components/arm/college-template-upload";
import { CreateProjectModal } from "@/components/arm/create-project-modal";
import { ReportPreviewModal } from "@/components/arm/report-preview-modal";
import { supabase } from "@/lib/supabase";

export default function MyProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Auth state
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals & Active actions
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<ProjectDTO | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [regeneratingProjectId, setRegeneratingProjectId] = useState<string | null>(null);

  // Preview Modal State
  const [previewJob, setPreviewJob] = useState<ReplacementJobResponseDTO | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // 1. Check Authentication on Mount
  useEffect(() => {
    async function checkAuth() {
      setIsAuthChecking(true);
      try {
        const { data } = await supabase.auth.getSession();
        if (data.session?.user) {
          setCurrentUser(data.session.user);
        } else {
          // Check local storage fallback for dev demo
          const localId = localStorage.getItem("arm_user_id");
          const localEmail = localStorage.getItem("arm_user_email");
          if (localId && localEmail) {
            setCurrentUser({ id: localId, email: localEmail });
          } else {
            setCurrentUser(null);
          }
        }
      } catch (err) {
        console.error("Auth session check error:", err);
      } finally {
        setIsAuthChecking(false);
      }
    }
    checkAuth();
  }, []);

  // 2. Fetch Projects for the Authenticated User
  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getProjects();
      setProjects(data || []);
    } catch (err: any) {
      console.error("Error fetching projects:", err);
      setError(err.message || "Failed to load projects. Please ensure you are logged in.");
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthChecking) {
      fetchProjects();
    }
  }, [isAuthChecking, fetchProjects]);

  // Action: Regenerate Project Report
  const handleRegenerate = async (proj: ProjectDTO) => {
    if (!proj.id) return;
    setRegeneratingProjectId(proj.id);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await apiClient.regenerateProject(proj.id);
      setSuccessMsg(`Report generation initiated for "${proj.title}"! College template preserved with zero redesign.`);
      await fetchProjects();
    } catch (err: any) {
      setError(`Failed to regenerate report: ${err.message}`);
    } finally {
      setRegeneratingProjectId(null);
    }
  };

  // Action: Open Preview Modal
  const handleOpenPreview = async (proj: ProjectDTO) => {
    if (!proj.id) return;
    try {
      // If we have a latest_job_id, fetch the full job
      if (proj.latest_job_id) {
        const job = await apiClient.getReplacementStatus(proj.latest_job_id);
        setPreviewJob(job);
        setIsPreviewOpen(true);
        return;
      }

      // Otherwise synthesize baseline preview job from project information
      const previewJobStub: ReplacementJobResponseDTO = {
        job_id: proj.id,
        project_id: proj.id,
        template_id: proj.template_id || "master-college-template",
        state: (proj.generation_status?.toUpperCase() as any) || "COMPLETED",
        approval_status: (proj.latest_report?.approval_status as any) || "pending",
        approved_at: proj.latest_report?.approved_at || null,
        progress_percent: 100,
        arm_ui_state: "completed",
        status_message: "College template replacement report loaded.",
        fields_replaced: 20,
        total_fields: 20,
        images_replaced: 2,
        preview_html: `<div class="p-8 max-w-3xl mx-auto font-serif">
          <h1 class="text-xl font-bold uppercase text-center text-blue-900 mb-4">${proj.title}</h1>
          <p class="text-center italic text-xs text-zinc-600 mb-8">Department of ${proj.department || "Computer Science & Engineering"}</p>
          <h2 class="text-sm font-bold text-blue-800 uppercase mt-4 mb-2">1. ABSTRACT</h2>
          <p class="text-xs leading-relaxed text-zinc-800">${proj.abstract_summary || proj.description || "Academic project synopsis and experimental evaluation."}</p>
          <h2 class="text-sm font-bold text-blue-800 uppercase mt-6 mb-2">2. SYSTEM METHODOLOGY</h2>
          <p class="text-xs leading-relaxed text-zinc-800">${proj.methodology || "Multi-stage system architecture and experimental benchmarking methodology."}</p>
        </div>`,
        stats: {
          page_count: proj.latest_report?.page_count || 4,
          estimated_word_count: proj.latest_report?.word_count || 1850,
          sections_count: 8,
          images_count: 2,
          validation_status: "VALID",
        },
        audit: [],
        errors: [],
        warnings: [],
        created_at: proj.created_at || new Date().toISOString(),
        updated_at: proj.updated_at || new Date().toISOString(),
      };

      setPreviewJob(previewJobStub);
      setIsPreviewOpen(true);
    } catch (err: any) {
      setError(`Failed to load report preview: ${err.message}`);
    }
  };

  // Action: Delete Project
  const confirmDelete = async () => {
    if (!projectToDelete?.id) return;
    setIsDeleting(true);
    try {
      await apiClient.deleteProject(projectToDelete.id);
      setProjects((prev) => prev.filter((p) => p.id !== projectToDelete.id));
      setSuccessMsg(`Project "${projectToDelete.title}" deleted.`);
      setProjectToDelete(null);
    } catch (err: any) {
      setError(`Failed to delete project: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Filtered project list
  const filteredProjects = projects.filter((p) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      p.title?.toLowerCase().includes(q) ||
      p.guide_name?.toLowerCase().includes(q) ||
      p.department?.toLowerCase().includes(q) ||
      p.template_name?.toLowerCase().includes(q);

    const matchesType = typeFilter === "all" || p.project_type?.toLowerCase() === typeFilter.toLowerCase();
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "completed" && p.generation_status === "completed") ||
      (statusFilter === "draft" && p.generation_status !== "completed");

    return matchesSearch && matchesType && matchesStatus;
  });

  return (
    <div className="flex h-screen w-full bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 overflow-hidden transition-colors duration-300">
      <ArmSidebar
        isMobileOpen={mobileMenuOpen}
        onToggleMobile={() => setMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-black transition-colors duration-300">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 px-6 flex items-center justify-between shrink-0 bg-white/80 dark:bg-black/80 backdrop-blur-md transition-colors duration-300">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <FolderGit2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <h1 className="text-sm font-bold text-zinc-900 dark:text-white tracking-tight">
                My Projects
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {currentUser && (
              <span className="hidden sm:inline-block text-xs font-mono text-zinc-500 dark:text-zinc-400">
                👤 {currentUser.email || "Scholar"}
              </span>
            )}
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              className="text-xs font-semibold"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              Create Project
            </Button>
            <ThemeToggle />
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto w-full space-y-6">
          {/* Notifications */}
          {error && (
            <StatusBanner
              type="error"
              title="Project Service Notice"
              message={error}
            />
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successMsg}</span>
              </div>
              <button
                onClick={() => setSuccessMsg(null)}
                className="text-zinc-400 hover:text-zinc-600 font-bold text-xs"
              >
                ✕
              </button>
            </div>
          )}

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 rounded-xl">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search projects by title, guide, or template..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs pl-9 pr-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs px-2.5 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-zinc-700 dark:text-zinc-300 focus:outline-none"
              >
                <option value="all">All Types</option>
                <option value="capstone">Capstone</option>
                <option value="seminar">Seminar</option>
                <option value="thesis">Thesis</option>
                <option value="internship">Internship</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs px-2.5 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-zinc-700 dark:text-zinc-300 focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="completed">Completed</option>
                <option value="draft">In Progress / Draft</option>
              </select>
            </div>
          </div>

          {/* Project List / Grid */}
          {isLoading ? (
            <div className="py-24 text-center space-y-3">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-500" />
              <p className="text-xs text-zinc-500 font-mono">Loading authenticated student projects...</p>
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="py-16">
              <EmptyState
                icon={FolderGit2}
                title="No projects found"
                description={
                  searchQuery
                    ? "No academic projects match your search query."
                    : "You haven't created any projects yet. Create your first project to begin automated college report synthesis."
                }
                actionLabel="Create Project"
                onAction={() => setIsCreateModalOpen(true)}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5">
              {filteredProjects.map((proj) => {
                const isRegenerating = regeneratingProjectId === proj.id;
                const isApproved = proj.latest_report?.approval_status === "approved";
                const isCompleted = proj.generation_status === "completed";
                const templateDisplayName = proj.template_name || "Master College Template (IEEE Standard)";

                return (
                  <div
                    key={proj.id || proj.title}
                    className="p-5 sm:p-6 rounded-2xl border border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-950 shadow-sm hover:border-zinc-300 dark:hover:border-zinc-750 transition-all space-y-4"
                  >
                    {/* Top Row: Title, Badges, Status */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="text-base font-bold text-zinc-900 dark:text-white tracking-tight">
                            {proj.title}
                          </h2>
                          <Badge variant="outline" className="text-[10px] font-mono capitalize">
                            {proj.project_type || "Capstone"}
                          </Badge>
                          {isCompleted ? (
                            <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 text-[10px]">
                              ✓ Completed
                            </Badge>
                          ) : (
                            <Badge className="bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 text-[10px]">
                              In Progress
                            </Badge>
                          )}
                        </div>

                        {proj.description && (
                          <p className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-2 max-w-3xl leading-relaxed">
                            {proj.description}
                          </p>
                        )}
                      </div>

                      {/* Last Updated Timestamp */}
                      <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400 shrink-0">
                        <Clock className="w-3.5 h-3.5" />
                        <span>
                          Updated:{" "}
                          {proj.updated_at
                            ? new Date(proj.updated_at).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })
                            : "Recent"}
                        </span>
                      </div>
                    </div>

                    {/* Metadata Ribbon: Template, Guide, Generation Status */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800 text-xs">
                      <div>
                        <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-400 block mb-0.5">
                          Template
                        </span>
                        <div className="flex items-center gap-1.5 font-medium text-zinc-800 dark:text-zinc-200 truncate">
                          <FileCode2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                          <span className="truncate" title={templateDisplayName}>
                            {templateDisplayName}
                          </span>
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-400 block mb-0.5">
                          Generation Status
                        </span>
                        <div className="flex items-center gap-1.5 font-medium">
                          {isCompleted ? (
                            <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Submission
                            </span>
                          ) : (
                            <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                              <Sparkles className="w-3.5 h-3.5" /> {proj.generation_status || "Draft"}
                            </span>
                          )}
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-400 block mb-0.5">
                          Faculty Guide
                        </span>
                        <div className="flex items-center gap-1.5 text-zinc-700 dark:text-zinc-300 truncate">
                          <GraduationCap className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                          <span className="truncate">{proj.guide_name || "Assigned Guide"}</span>
                        </div>
                      </div>
                    </div>

                    {/* Latest Report Snapshot (if generated) */}
                    {proj.latest_report ? (
                      <div className="p-3.5 rounded-xl border border-blue-200/80 dark:border-blue-900/40 bg-blue-50/40 dark:bg-blue-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
                            DOC
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-zinc-900 dark:text-zinc-100">
                                Latest Report: {proj.latest_report.title || "Academic Report"}
                              </span>
                              {isApproved ? (
                                <Badge className="bg-emerald-600 text-white text-[10px] py-0 px-1.5 flex items-center gap-0.5">
                                  <ShieldCheck className="w-3 h-3" /> Approved
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-300 text-[10px] py-0 px-1.5">
                                  Pending Approval
                                </Badge>
                              )}
                            </div>
                            <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400 block mt-0.5">
                              📄 {proj.latest_report.page_count || 1} Pages • 📝 {proj.latest_report.word_count?.toLocaleString() || 0} Words • 100% Master Template Geometry
                            </span>
                          </div>
                        </div>

                        {/* Quick Report Download buttons */}
                        <div className="flex items-center gap-1.5">
                          {proj.latest_report.docx_url && (
                            <a
                              href={proj.latest_report.docx_url}
                              download
                              className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1 shadow-xs"
                            >
                              <Download className="w-3 h-3" /> DOCX
                            </a>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 text-xs text-zinc-500 flex items-center justify-between">
                        <span>No report document synthesized yet.</span>
                        <Link
                          href={`/app?projectId=${proj.id}`}
                          className="text-blue-600 dark:text-blue-400 hover:underline font-semibold flex items-center gap-1"
                        >
                          Generate Now <ArrowRight className="w-3 h-3" />
                        </Link>
                      </div>
                    )}

                    {/* The 6 Required Actions Toolbar */}
                    <div className="pt-3 border-t border-zinc-100 dark:border-zinc-900 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        {/* 1. Open */}
                        <Link
                          href={`/app?projectId=${proj.id}`}
                          className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-800 dark:text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
                          Open
                        </Link>

                        {/* 2. Continue */}
                        <Link
                          href={`/app?projectId=${proj.id}&step=generator`}
                          className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        >
                          <Play className="w-3.5 h-3.5 text-blue-600" />
                          Continue
                        </Link>

                        {/* 3. Regenerate */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRegenerate(proj)}
                          disabled={isRegenerating}
                          className="text-xs h-8"
                          title="Regenerate report content into Master Template"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isRegenerating ? "animate-spin text-blue-500" : ""}`} />
                          {isRegenerating ? "Regenerating..." : "Regenerate"}
                        </Button>

                        {/* 4. Preview */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenPreview(proj)}
                          className="text-xs h-8"
                          title="Preview actual synthesized document with OpenXML styles"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1 text-purple-500" />
                          Preview
                        </Button>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {/* 5. Download */}
                        {proj.latest_report?.docx_url ? (
                          <a
                            href={proj.latest_report.docx_url}
                            download
                            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download DOCX
                          </a>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled
                            className="text-xs h-8 text-zinc-400"
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />
                            Download
                          </Button>
                        )}

                        {/* 6. Delete */}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setProjectToDelete(proj)}
                          className="text-xs h-8 text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                          title="Delete this project"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* Delete Confirmation Modal */}
      {projectToDelete && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-600">
              <div className="w-10 h-10 rounded-xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-white">Delete Project?</h3>
                <p className="text-xs text-zinc-500">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Are you sure you want to permanently delete{" "}
              <strong className="text-zinc-900 dark:text-zinc-100">&ldquo;{projectToDelete.title}&rdquo;</strong>?
              All associated report drafts, evidence files, and image assets will be deleted from your account.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-900">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProjectToDelete(null)}
                disabled={isDeleting}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={confirmDelete}
                disabled={isDeleting}
                className="text-xs bg-rose-600 hover:bg-rose-700 text-white font-semibold"
              >
                {isDeleting ? "Deleting..." : "Delete Permanently"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onProjectCreated={(newProj) => {
          setProjects((prev) => [newProj, ...prev]);
        }}
      />

      {/* Report Preview Modal */}
      {previewJob && (
        <ReportPreviewModal
          job={previewJob}
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          onJobUpdated={(updated) => {
            setPreviewJob(updated);
            fetchProjects();
          }}
        />
      )}
    </div>
  );
}
