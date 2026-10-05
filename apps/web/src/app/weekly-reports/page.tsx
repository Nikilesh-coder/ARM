"use client";

import React, { useState } from "react";
import {
  CalendarDays,
  Plus,
  CheckCircle2,
  Clock,
  Printer,
  X,
  FileCheck
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { INITIAL_MOCK_WEEKLY_REPORTS, WeeklyReportItem } from "@/lib/mock-data";

export default function WeeklyReportsPage() {
  const [weeklyReports, setWeeklyReports] = useState<WeeklyReportItem[]>(INITIAL_MOCK_WEEKLY_REPORTS);
  const [modalOpen, setModalOpen] = useState(false);

  // New report form state
  const [planned, setPlanned] = useState("");
  const [completed, setCompleted] = useState("");
  const [blockers, setBlockers] = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!completed.trim()) return;

    const newReport: WeeklyReportItem = {
      id: `wk-${Date.now()}`,
      weekNumber: weeklyReports.length + 1,
      dateRange: "Current Academic Week",
      plannedTasks: planned || "Continue system development.",
      completedTasks: completed,
      blockers: blockers || "None",
      status: "submitted",
    };

    setWeeklyReports([newReport, ...weeklyReports]);
    setModalOpen(false);
    setPlanned("");
    setCompleted("");
    setBlockers("");
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Weekly Lab &amp; Project Diary</h1>
              <p className="text-xs text-slate-500 mt-1">
                Maintain continuous milestone tracking for faculty guide review and attendance logging.
              </p>
            </div>
            <Button onClick={() => setModalOpen(true)} variant="primary" size="sm">
              <Plus className="w-4 h-4 mr-1.5" />
              Add Week Entry
            </Button>
          </div>

          {/* Weekly Entries Feed */}
          <div className="space-y-6">
            {weeklyReports.map((entry) => (
              <Card key={entry.id}>
                <CardHeader className="flex flex-row items-center justify-between pb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-xs">
                      W{entry.weekNumber}
                    </div>
                    <div>
                      <CardTitle className="text-base">Week {entry.weekNumber} Progress Report</CardTitle>
                      <CardDescription>{entry.dateRange}</CardDescription>
                    </div>
                  </div>
                  <Badge variant={entry.status === "approved" ? "success" : "academic"}>
                    {entry.status === "approved" ? "Guide Approved" : "Submitted for Review"}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs sm:text-sm">
                  <div>
                    <span className="font-bold text-slate-700 block text-xs uppercase tracking-wider mb-1">
                      Tasks Planned
                    </span>
                    <p className="text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                      {entry.plannedTasks}
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 block text-xs uppercase tracking-wider mb-1">
                      Completed Work &amp; Achievements
                    </span>
                    <p className="text-slate-700 leading-relaxed bg-blue-50/50 p-3 rounded-lg border border-blue-100/80">
                      {entry.completedTasks}
                    </p>
                  </div>

                  {entry.blockers && entry.blockers !== "None" && (
                    <div>
                      <span className="font-bold text-slate-700 block text-xs uppercase tracking-wider mb-1">
                        Challenges &amp; Technical Roadblocks
                      </span>
                      <p className="text-slate-600 leading-relaxed bg-amber-50/50 p-3 rounded-lg border border-amber-100/80">
                        {entry.blockers}
                      </p>
                    </div>
                  )}

                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                    <span>Guide Sign-off: Dr. Sarah Jenkins</span>
                    <button
                      onClick={() => window.print()}
                      className="inline-flex items-center text-slate-600 hover:text-slate-900 font-semibold"
                    >
                      <Printer className="w-3.5 h-3.5 mr-1" />
                      Print Guide Slip
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Modal */}
          {modalOpen && (
            <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
                  <h3 className="text-lg font-bold text-slate-900">Record Week Entry</h3>
                  <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form onSubmit={handleCreate} className="space-y-4 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Planned Tasks for this Week
                    </label>
                    <textarea
                      rows={2}
                      value={planned}
                      onChange={(e) => setPlanned(e.target.value)}
                      placeholder="What deliverables were scheduled on the project timeline?"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Completed Work &amp; Modules
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={completed}
                      onChange={(e) => setCompleted(e.target.value)}
                      placeholder="Detail experimental results, code modules completed, or benchmark tests run..."
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Blockers / Dependencies (Optional)
                    </label>
                    <input
                      type="text"
                      value={blockers}
                      onChange={(e) => setBlockers(e.target.value)}
                      placeholder="e.g. Awaiting GPU cluster quota approval"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>

                  <div className="flex items-center justify-end space-x-2 pt-4 border-t border-slate-100">
                    <Button type="button" variant="outline" size="sm" onClick={() => setModalOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary" size="sm">
                      Submit for Guide Review
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
