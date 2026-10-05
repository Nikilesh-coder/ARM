"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Plus,
  Sparkles,
  FileCode2,
  FolderGit2,
  User,
  Settings,
  X,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ArmSidebarProps {
  onNewChat?: () => void;
  onStartWizard?: () => void;
  userEmail?: string;
  userName?: string;
  isMobileOpen?: boolean;
  onToggleMobile?: () => void;
}

export function ArmSidebar({
  onNewChat,
  onStartWizard,
  userEmail: propEmail,
  userName: propName,
  isMobileOpen = false,
  onToggleMobile,
}: ArmSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [userName, setUserName] = useState(propName || "Engineering Scholar");
  const [userEmail, setUserEmail] = useState(propEmail || "scholar@university.edu");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedName = localStorage.getItem("arm_user_name");
      const storedEmail = localStorage.getItem("arm_user_email");
      if (storedName && storedName.trim()) {
        setUserName(storedName.trim());
      } else if (propName) {
        setUserName(propName);
      }
      if (storedEmail && storedEmail.trim()) {
        setUserEmail(storedEmail.trim());
      } else if (propEmail) {
        setUserEmail(propEmail);
      }
    }
  }, [propName, propEmail]);

  // Strict 4 secondary navigation items + 1 primary action (New Chat) as mandated in Section 7
  const navItems = [
    { label: "Templates", href: "/app/templates", icon: FileCode2 },
    { label: "My Projects", href: "/app/projects", icon: FolderGit2 },
    { label: "Profile", href: "/app/settings", icon: User },
    { label: "Settings", href: "/app/settings", icon: Settings },
  ];

  const handleNewChatClick = () => {
    if (onNewChat) {
      onNewChat();
    }
    if (pathname !== "/app") {
      router.push("/app");
    }
    if (onToggleMobile) {
      onToggleMobile();
    }
  };

  const content = (
    <div className="flex flex-col h-full bg-zinc-50 dark:bg-black border-r border-zinc-200 dark:border-zinc-850 select-none transition-colors duration-300">
      {/* Brand Header */}
      <div className="p-4 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900">
        <Link href="/app" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-xs tracking-wider shadow-xs">
            ARM
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-white">ARM</span>
            <span className="text-[10px] text-zinc-500 font-mono tracking-wider uppercase">
              Academic Assistant
            </span>
          </div>
        </Link>

        {onToggleMobile && (
          <button
            onClick={onToggleMobile}
            className="md:hidden p-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-900"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Item 1: Prominent Primary Action — New Chat */}
      <div className="p-3">
        <button
          type="button"
          onClick={handleNewChatClick}
          className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-zinc-900 text-white hover:bg-black dark:bg-white dark:text-black dark:hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all duration-150 active:scale-[0.98] cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Plus className="w-4 h-4 stroke-[2.5]" />
            New Chat
          </span>
          <span className="text-[10px] font-mono bg-zinc-800 text-zinc-300 dark:bg-zinc-100 dark:text-zinc-600 px-1.5 py-0.5 rounded">
            ⌘N
          </span>
        </button>

        {onStartWizard && (
          <button
            type="button"
            onClick={() => {
              onStartWizard();
              if (onToggleMobile) onToggleMobile();
            }}
            className="w-full mt-2 flex items-center justify-between px-3 py-2 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 border border-blue-200 dark:border-blue-900/60 text-xs font-semibold shadow-xs transition-all duration-150 cursor-pointer"
          >
            <span className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              Guided Report
            </span>
            <span className="text-[9px] font-mono uppercase bg-blue-200/60 dark:bg-blue-900/80 px-1 py-0.5 rounded">
              8 Steps
            </span>
          </button>
        )}
      </div>

      {/* Items 2, 3, 4, 5: Minimal Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={onToggleMobile}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors",
                isActive
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white font-semibold border border-zinc-200 dark:border-zinc-800 shadow-xs"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-950"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0", isActive ? "text-blue-600 dark:text-blue-400" : "text-zinc-500")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Minimal Footer: Profile Information & Logout */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-900 bg-zinc-100/50 dark:bg-zinc-950/70">
        <div className="flex items-center justify-between p-2 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/40 shadow-xs">
          <Link
            href="/app/settings"
            onClick={onToggleMobile}
            className="flex items-center gap-2.5 min-w-0 flex-1 hover:opacity-90"
          >
            <div className="w-7 h-7 rounded-full bg-zinc-200 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-750 flex items-center justify-center text-zinc-700 dark:text-zinc-300 shrink-0 text-xs font-medium">
              {userName.charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-zinc-900 dark:text-white truncate">{userName}</p>
              <p className="text-[10px] text-zinc-500 font-mono truncate">{userEmail}</p>
            </div>
          </Link>
          <Link
            href="/login"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors shrink-0 ml-1"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Minimal Sidebar */}
      <aside className="hidden md:flex w-60 h-screen flex-col shrink-0 sticky top-0">
        {content}
      </aside>

      {/* Mobile Drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm"
            onClick={onToggleMobile}
          />
          <div className="relative w-64 h-full z-10">
            {content}
          </div>
        </div>
      )}
    </>
  );
}
