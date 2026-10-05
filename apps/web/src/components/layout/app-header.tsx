"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { FileText, Plus, Menu, X, Activity, HardDrive, Cpu, Database } from "lucide-react";
import { apiClient, DetailedHealthResponse } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState<"connecting" | "healthy" | "offline">("connecting");
  const [diag, setDiag] = useState<DetailedHealthResponse | null>(null);

  useEffect(() => {
    apiClient
      .checkHealth()
      .then((res) => {
        if (res.status === "healthy") {
          setHealthStatus("healthy");
          return apiClient.getDetailedHealth();
        }
        setHealthStatus("offline");
        return null;
      })
      .then((d) => {
        if (d) setDiag(d);
      })
      .catch(() => setHealthStatus("offline"));
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md h-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
        {/* Left side: Brand + Mobile Trigger */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link href="/dashboard" className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-700 flex items-center justify-center text-white shadow-xs">
              <FileText className="w-5 h-5" />
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900 tracking-tight text-base sm:text-lg">ReportForge AI</span>
              <span className="hidden sm:inline-block text-[10px] font-bold px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                Workspace
              </span>
            </div>
          </Link>
        </div>

        {/* Right side: Health indicator + New Project */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          <div className="hidden sm:flex items-center space-x-2 text-xs font-medium">
            <span className="text-slate-400">Engine:</span>
            {healthStatus === "healthy" ? (
              <span className="inline-flex items-center text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
                Active
              </span>
            ) : healthStatus === "connecting" ? (
              <span className="text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                Checking...
              </span>
            ) : (
              <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                Standby
              </span>
            )}
          </div>

          <Link href="/projects">
            <Button variant="primary" size="sm">
              <Plus className="w-3.5 h-3.5 mr-1" />
              New Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Mobile Nav Links Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-b border-slate-200 bg-white px-4 py-3 space-y-1 shadow-lg">
          {[
            { href: "/dashboard", label: "Dashboard" },
            { href: "/projects", label: "Projects" },
            { href: "/templates", label: "Templates" },
            { href: "/evidence", label: "Evidence" },
            { href: "/reports", label: "Reports" },
            { href: "/weekly-reports", label: "Weekly Reports" },
            { href: "/usage", label: "Usage & Limits" },
            { href: "/settings", label: "Settings" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className="block px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
