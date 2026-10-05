"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  FileCode,
  Database,
  FileText,
  CalendarDays,
  BarChart3,
  Settings,
  Sparkles,
  ChevronRight,
  LogOut,
  GraduationCap
} from "lucide-react";
import { cn } from "@/lib/utils";

const SIDEBAR_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/templates", label: "Templates", icon: FileCode },
  { href: "/evidence", label: "Evidence", icon: Database },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/weekly-reports", label: "Weekly Reports", icon: CalendarDays },
  { href: "/usage", label: "Usage & Limits", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-200/80 bg-white flex flex-col justify-between h-[calc(100vh-4rem)] sticky top-16 hidden md:flex">
      {/* Navigation Links */}
      <div className="p-4 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Academic Workspace
          </div>
          <nav className="space-y-1">
            {SIDEBAR_ITEMS.map((item) => {
              const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-colors",
                    active
                      ? "bg-blue-50 text-blue-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  )}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={cn("w-4 h-4", active ? "text-blue-600" : "text-slate-400")} />
                    <span>{item.label}</span>
                  </div>
                  {active && <ChevronRight className="w-3.5 h-3.5 text-blue-500" />}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Workflow Prompt Card */}
        <div className="p-3.5 bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-xl shadow-xs">
          <div className="flex items-center space-x-1.5 text-blue-300 text-xs font-bold mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Deterministic Engine</span>
          </div>
          <p className="text-[11px] text-blue-100/90 leading-relaxed mb-3">
            Ensure your master college .docx is uploaded to lock page geometry and roman numbering.
          </p>
          <Link
            href="/templates"
            className="block text-center text-xs font-semibold py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
          >
            Inspect Template
          </Link>
        </div>
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
            <GraduationCap className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-slate-800 truncate">Alex Student</div>
            <div className="text-[10px] text-slate-400 truncate">B.Tech CS &middot; 2026</div>
          </div>
        </div>
        <Link href="/login" title="Logout" className="text-slate-400 hover:text-slate-700 p-1 rounded-md">
          <LogOut className="w-4 h-4" />
        </Link>
      </div>
    </aside>
  );
}
