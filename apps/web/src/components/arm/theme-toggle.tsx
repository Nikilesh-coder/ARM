"use client";

import React from "react";
import { useTheme } from "@/lib/theme";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  className?: string;
  variant?: "segmented" | "button";
}

export function ThemeToggle({ className, variant = "segmented" }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();

  if (variant === "button") {
    const isDark = theme === "dark";
    return (
      <button
        type="button"
        onClick={() => setTheme(isDark ? "light" : "dark")}
        className={cn(
          "p-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-100/80 dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-white transition-all cursor-pointer shadow-xs flex items-center gap-1.5",
          className
        )}
        title={isDark ? "Switch to Light theme" : "Switch to Dark theme"}
        aria-label="Toggle theme"
      >
        {isDark ? (
          <>
            <Sun className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-medium hidden sm:inline">Light</span>
          </>
        ) : (
          <>
            <Moon className="w-4 h-4 text-zinc-700" />
            <span className="text-xs font-medium hidden sm:inline">Dark</span>
          </>
        )}
      </button>
    );
  }

  // Segmented Pill Variant (Recommended for top right header)
  return (
    <div
      className={cn(
        "flex items-center p-0.5 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs",
        className
      )}
      role="group"
      aria-label="Theme selector"
    >
      <button
        type="button"
        onClick={() => setTheme("light")}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all cursor-pointer",
          theme === "light"
            ? "bg-white text-zinc-900 shadow-xs font-semibold border border-zinc-200/60"
            : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white font-medium"
        )}
        title="Switch to Light Theme"
      >
        <Sun className={cn("w-3.5 h-3.5", theme === "light" ? "text-amber-500" : "text-zinc-400")} />
        <span className="hidden sm:inline">Light</span>
      </button>

      <button
        type="button"
        onClick={() => setTheme("dark")}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all cursor-pointer",
          theme === "dark"
            ? "bg-zinc-800 text-white shadow-xs font-semibold border border-zinc-700"
            : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white font-medium"
        )}
        title="Switch to Dark Theme"
      >
        <Moon className={cn("w-3.5 h-3.5", theme === "dark" ? "text-blue-400" : "text-zinc-400")} />
        <span className="hidden sm:inline">Dark</span>
      </button>
    </div>
  );
}
