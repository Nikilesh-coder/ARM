"use client";

import React, { useState } from "react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CalendarDays,
  Plus,
  ArrowRight,
  CheckCircle2,
  Clock,
  Menu,
} from "lucide-react";

interface WeeklyReportItem {
  id: string;
  weekNumber: number;
  project: string;
  milestoneTitle: string;
  hoursSpent: number;
  status: "approved" | "submitted" | "draft";
  createdDate: string;
  docxAvailable: boolean;
}

export default function WeeklyReportsPage() {
  const [weeklyReports, setWeeklyReports] = useState<WeeklyReportItem[]>([]);
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
              Weekly Reports & Diary
            </h1>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={() => (window.location.href = "/app")}
            className="text-xs font-semibold"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            Create Weekly Report
          </Button>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full">
          {/* Continuity Explanation Header */}
          <div className="p-4 rounded-xl border border-zinc-850 bg-zinc-950/60 mb-6 text-xs text-zinc-400 flex items-center justify-between">
            <p>
              Weekly diaries maintain uninterrupted academic continuity across the semester. Previous week milestones automatically feed into subsequent work-package reports.
            </p>
            <span className="text-[11px] font-mono text-zinc-500 shrink-0 ml-4 hidden sm:inline">
              16 Weeks Progression
            </span>
          </div>

          {weeklyReports.length === 0 ? (
            /* Strict Section 19 Empty State */
            <div className="py-16">
              <EmptyState
                icon={CalendarDays}
                title="No weekly reports yet"
                description="Start logging your weekly project milestones, hours spent, and supervisor remarks to maintain an unbroken semester diary."
                actionLabel="Create Weekly Report"
                onAction={() => (window.location.href = "/app")}
              />
            </div>
          ) : (
            <div className="space-y-3">
              {weeklyReports.map((item) => (
                <Card
                  key={item.id}
                  className="border-zinc-800 bg-zinc-950/70 p-4 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono font-bold text-white bg-zinc-900 border border-zinc-850 px-2.5 py-1 rounded-lg">
                        W{item.weekNumber}
                      </span>
                      <div>
                        <h4 className="text-sm font-semibold text-white">
                          {item.milestoneTitle}
                        </h4>
                        <p className="text-[11px] text-zinc-500 font-mono">
                          {item.project} • {item.hoursSpent} Hours Tracked
                        </p>
                      </div>
                    </div>
                    <Badge variant="success" className="text-[10px]">
                      {item.status}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
