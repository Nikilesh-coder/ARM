"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FolderKanban,
  FileCode,
  Database,
  FileText,
  CalendarDays,
  Plus,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Clock,
  Download,
  AlertCircle
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { WorkflowStepper } from "@/components/workflow/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { INITIAL_MOCK_PROJECTS, INITIAL_MOCK_TEMPLATES } from "@/lib/mock-data";

export default function DashboardPage() {
  const activeProject = INITIAL_MOCK_PROJECTS[0];
  const activeTemplate = INITIAL_MOCK_TEMPLATES[0];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {/* Welcome Banner */}
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Academic Dashboard</h1>
              <p className="text-xs text-slate-500 mt-1">
                Active Term: 2026-2027 &middot; Computer Science Department
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Link href="/projects">
                <Button variant="outline" size="sm">
                  All Projects
                </Button>
              </Link>
              <Link href="/templates">
                <Button variant="primary" size="sm">
                  <FileCode className="w-3.5 h-3.5 mr-1.5" />
                  Upload Template
                </Button>
              </Link>
            </div>
          </div>

          {/* Primary Visual Workflow Stepper */}
          <WorkflowStepper currentStep={2} />

          {/* Active Project Highlight */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-start justify-between pb-4">
                <div>
                  <div className="flex items-center space-x-2 mb-1.5">
                    <Badge variant="academic">Capstone Final</Badge>
                    <Badge variant="success">In Progress</Badge>
                  </div>
                  <CardTitle>{activeProject.title}</CardTitle>
                  <CardDescription>{activeProject.guideName}</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed mb-6">
                  {activeProject.abstractSummary}
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="text-[11px] text-slate-400 font-medium">Assigned Template</div>
                    <div className="text-xs font-bold text-blue-700 truncate mt-0.5">
                      {activeProject.templateName}
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="text-[11px] text-slate-400 font-medium">Evidence Files</div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {activeProject.evidenceCount} Files Deposited
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="text-[11px] text-slate-400 font-medium">Report Version</div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">v1.2-draft</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="text-[11px] text-slate-400 font-medium">Academic Year</div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {activeProject.academicYear}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100">
                  <div className="flex items-center space-x-2 text-xs text-slate-500">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>Last updated {activeProject.updatedAt}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Link href="/evidence">
                      <Button variant="outline" size="sm">Add Evidence</Button>
                    </Link>
                    <Link href="/reports">
                      <Button variant="primary" size="sm">Generate Report Plan</Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Template Intelligence Status Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Template Status</CardTitle>
                  <Badge variant="success">Verified</Badge>
                </div>
                <CardDescription>Deterministic OpenXML profile</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-100 text-xs">
                  <div className="font-bold text-blue-900 truncate">{activeTemplate.name}</div>
                  <div className="text-blue-700 text-[11px] mt-0.5">{activeTemplate.institution}</div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Page Geometry</span>
                    <span className="font-semibold text-slate-800">{activeTemplate.pageSize}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Binding Gutter</span>
                    <span className="font-semibold text-slate-800">31.75 mm (1.25 in)</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Typography</span>
                    <span className="font-semibold text-slate-800">Times New Roman 12pt</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Roman Page Numbering</span>
                    <span className="font-semibold text-emerald-600">Front Matter (ii..v)</span>
                  </div>
                </div>

                <Link href="/templates" className="block pt-2">
                  <Button variant="outline" size="sm" className="w-full">
                    View Template Intelligence Details
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link
              href="/projects"
              className="p-5 bg-white border border-slate-200/90 rounded-2xl hover:border-blue-400 hover:shadow-xs transition group"
            >
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:scale-105 transition">
                <FolderKanban className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">Projects Hub</h4>
              <p className="text-xs text-slate-500">Manage capstone, thesis, and seminar project files.</p>
            </Link>

            <Link
              href="/templates"
              className="p-5 bg-white border border-slate-200/90 rounded-2xl hover:border-indigo-400 hover:shadow-xs transition group"
            >
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 group-hover:scale-105 transition">
                <FileCode className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">Template Studio</h4>
              <p className="text-xs text-slate-500">Upload and inspect institutional Word layouts.</p>
            </Link>

            <Link
              href="/evidence"
              className="p-5 bg-white border border-slate-200/90 rounded-2xl hover:border-emerald-400 hover:shadow-xs transition group"
            >
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3 group-hover:scale-105 transition">
                <Database className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">Evidence Vault</h4>
              <p className="text-xs text-slate-500">Deposit diagrams, benchmarks, and code snippets.</p>
            </Link>

            <Link
              href="/weekly-reports"
              className="p-5 bg-white border border-slate-200/90 rounded-2xl hover:border-purple-400 hover:shadow-xs transition group"
            >
              <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-3 group-hover:scale-105 transition">
                <CalendarDays className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">Weekly Lab Diary</h4>
              <p className="text-xs text-slate-500">Record weekly progress for faculty guide signatures.</p>
            </Link>
          </div>
        </main>
      </div>
    </div>
  );
}
