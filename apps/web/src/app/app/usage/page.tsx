"use client";

import React, { useState } from "react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Zap, Info, Cpu, FileText, HardDrive, BookOpen, Menu } from "lucide-react";

export default function UsagePage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Per Section 20: Display only real backend usage information.
  // If usage tracking is not implemented yet, show:
  // "Usage tracking is not available yet."
  // Do not invent numbers.
  const isUsageTrackingEnabled = false;

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
              Usage & Quota Limits
            </h1>
          </div>
          <Badge variant="outline" className="text-[10px]">
            Preview Tier
          </Badge>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6">
          {/* Strict Section 20 Banner */}
          {!isUsageTrackingEnabled && (
            <div className="p-6 rounded-2xl border border-zinc-800 bg-zinc-950/70 text-center space-y-3">
              <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-zinc-400 mx-auto">
                <Info className="w-5 h-5" />
              </div>
              <h2 className="text-base font-semibold text-white">
                Usage tracking is not available yet.
              </h2>
              <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
                Backend quota telemetry is scheduled for activation in Stage 4. During this technical preview, document synthesis and template analysis limits are unrestricted.
              </p>
            </div>
          )}

          {/* Prepared Metric Slots for Real Backend Telemetry */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-widest text-zinc-500">
              Telemetry Allocation Targets
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card className="border-zinc-850 bg-zinc-950/40">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-300 flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-blue-400" />
                      AI Generations
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">Unmetered Preview</span>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-[11px] text-zinc-500">
                    Tracks LLM context windows and section synthesis requests.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-zinc-850 bg-zinc-950/40">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-300 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-emerald-400" />
                      Reports Generated
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">Unmetered Preview</span>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-[11px] text-zinc-500">
                    Tracks completed OpenXML document assembly jobs.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-zinc-850 bg-zinc-950/40">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-300 flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-purple-400" />
                      Storage Allocation
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">Unmetered Preview</span>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-[11px] text-zinc-500">
                    Tracks uploaded template assets, evidence files, and report binaries.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-zinc-850 bg-zinc-950/40">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-300 flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-amber-400" />
                      Research & Citation Usage
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">Unmetered Preview</span>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-[11px] text-zinc-500">
                    Tracks automated citation indexing and reference literature lookups.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
