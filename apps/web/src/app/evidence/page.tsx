"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FolderArchive,
  ArrowRight,
  ShieldCheck,
  FolderKanban,
  Clock,
  Plus
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { WorkflowStepper } from "@/components/workflow/workflow-stepper";
import { Button } from "@/components/ui/button";
import { EvidenceLocker } from "@/components/arm/evidence-locker";
import { apiClient, ProjectDTO } from "@/lib/api-client";

export default function EvidencePage() {
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [loadingProjects, setLoadingProjects] = useState(true);

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

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Project Evidence Repository</h1>
              <p className="text-xs text-slate-500 mt-1">
                Stage 5: Secure Evidence Locker with SHA-256 tamper-proof provenance. Grounding for all academic citations.
              </p>
            </div>
            <Link href="/reports">
              <Button variant="primary" size="sm">
                Next: Plan Report <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </Link>
          </div>

          <WorkflowStepper currentStep={3} />

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

          {/* Live Evidence Locker Component */}
          {selectedProjectId ? (
            <EvidenceLocker projectId={selectedProjectId} />
          ) : (
            <div className="p-12 text-center text-slate-500 text-sm bg-white rounded-xl border border-slate-200">
              Please select or create a project to deposit and manage supporting evidence.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
