"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Plus,
  Download,
  Calendar,
  Eye,
  CheckCircle2,
  Menu,
} from "lucide-react";
import { AiReportAgentPanel } from "@/components/arm/ai-report-agent-panel";

interface ReportItem {
  id: string;
  name: string;
  project: string;
  type: string;
  status: "ready" | "compiling" | "draft";
  createdDate: string;
  lastUpdated: string;
  docxAvailable: boolean;
  pdfAvailable: boolean;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
            <h1 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">
              Generated Reports
            </h1>
          </div>

          <Link href="/app">
            <Button variant="primary" size="sm" className="text-xs font-semibold">
              <Plus className="w-3.5 h-3.5 mr-1" />
              Create Report
            </Button>
          </Link>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-8">
          {/* ARM AI Report Agent Panel */}
          <AiReportAgentPanel />

          <div className="pt-2 space-y-4">
            <h2 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-white">
              Compiled Document Artifacts
            </h2>
            {reports.length === 0 ? (
              /* Strict Section 18 Empty State */
              <div className="py-8">
                <EmptyState
                  icon={FileText}
                  title="No compiled document artifacts yet"
                  description="Use the AI Report Agent above or the AI Workspace to assemble your first academic report from your uploaded college template and project evidence."
                  actionLabel="Go to Workspace"
                  onAction={() => (window.location.href = "/app")}
                />
              </div>
            ) : (
            <div className="space-y-4">
              {reports.map((report) => (
                <Card
                  key={report.id}
                  className="border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 transition-colors"
                >
                  <CardHeader>
                    <div className="flex justify-between items-start mb-2">
                      <Badge variant="success" className="text-[10px]">
                        <CheckCircle2 className="w-2.5 h-2.5 mr-1" />
                        {report.status}
                      </Badge>
                      <span className="text-[10px] font-mono text-zinc-500">
                        Updated {new Date(report.lastUpdated).toLocaleDateString()}
                      </span>
                    </div>
                    <CardTitle className="text-base">{report.name}</CardTitle>
                    <CardDescription>
                      {report.project} • {report.type}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="pt-3 border-t border-zinc-900 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {report.docxAvailable && (
                          <Badge variant="outline" className="text-[10px] text-zinc-300">
                            DOCX Ready
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="text-xs">
                          <Eye className="w-3.5 h-3.5 mr-1" /> Preview
                        </Button>
                        <Button variant="primary" size="sm" className="text-xs">
                          <Download className="w-3.5 h-3.5 mr-1" /> Download
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          </div>
        </main>
      </div>
    </div>
  );
}
