"use client";

import React from "react";
import { useTheme, ThemePreference } from "@/lib/theme";
import { Moon, Sun, Laptop, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  const themes: {
    id: ThemePreference;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    {
      id: "dark",
      label: "Dark",
      description: "Pure black visual identity designed for deep focus",
      icon: Moon,
    },
    {
      id: "light",
      label: "Light",
      description: "High-clarity paper aesthetic for daytime authoring",
      icon: Sun,
    },
    {
      id: "system",
      label: "System",
      description: "Automatically synchronizes with your device settings",
      icon: Laptop,
    },
  ];

  const handleSelectTheme = (newTheme: ThemePreference) => {
    setTheme(newTheme);
  };

  return (
    <section
      id="theme-selection"
      className="py-20 px-6 max-w-5xl mx-auto w-full border-t border-zinc-200 dark:border-zinc-900 transition-colors duration-300"
    >
      <div className="text-center max-w-2xl mx-auto mb-14">
        <span className="text-xs uppercase tracking-[0.25em] text-blue-600 dark:text-blue-400 font-mono font-medium">
          Personalize Your Workspace
        </span>
        <h2 className="text-2xl sm:text-4xl font-light text-zinc-900 dark:text-white tracking-tight mt-3 mb-3">
          How would you like ARM to look?
        </h2>
        <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400">
          Choose a visual theme below. Notice how ARM instantly transforms its background and atmosphere.
        </p>
      </div>

      {/* 3 Visual Theme Preview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {themes.map((item) => {
          const isSelected = theme === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleSelectTheme(item.id)}
              className={cn(
                "group relative flex flex-col rounded-2xl p-4 sm:p-5 text-left transition-all duration-300 border cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40",
                isSelected
                  ? "border-blue-600 dark:border-white bg-blue-50/50 dark:bg-zinc-900/90 shadow-xl scale-[1.02]"
                  : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/70 hover:border-zinc-400 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-900/40"
              )}
              aria-pressed={isSelected}
            >
              {/* Selected Badge */}
              <div className="absolute top-4 right-4 z-10">
                <div
                  className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center transition-all",
                    isSelected
                      ? "bg-blue-600 dark:bg-white text-white dark:text-black shadow-sm"
                      : "bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-transparent"
                  )}
                >
                  <Check className="w-3 h-3 stroke-[3]" />
                </div>
              </div>

              {/* Visual Preview Graphic */}
              <div className="w-full h-36 rounded-xl overflow-hidden mb-5 border border-zinc-200 dark:border-zinc-800 relative shadow-inner">
                {item.id === "dark" && (
                  /* Dark Mode Miniature Preview */
                  <div className="w-full h-full bg-[#050505] p-3 flex flex-col justify-between">
                    <div className="flex items-center gap-2 pb-2 border-b border-zinc-900">
                      <div className="w-4 h-4 rounded bg-zinc-800 text-white font-mono text-[8px] flex items-center justify-center font-bold">
                        A
                      </div>
                      <div className="h-2 w-16 bg-zinc-800 rounded" />
                    </div>
                    <div className="space-y-1.5 py-1">
                      <div className="h-2 w-3/4 bg-zinc-850 rounded" />
                      <div className="h-2 w-1/2 bg-zinc-900 rounded" />
                    </div>
                    {/* Miniature Composer */}
                    <div className="h-6 rounded-lg bg-zinc-900 border border-zinc-800 px-2 flex items-center justify-between">
                      <div className="h-1.5 w-20 bg-zinc-750 rounded" />
                      <div className="w-3 h-3 rounded-full bg-white" />
                    </div>
                  </div>
                )}

                {item.id === "light" && (
                  /* Light Mode Miniature Preview */
                  <div className="w-full h-full bg-slate-50 p-3 flex flex-col justify-between">
                    <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
                      <div className="w-4 h-4 rounded bg-slate-900 text-white font-mono text-[8px] flex items-center justify-center font-bold">
                        A
                      </div>
                      <div className="h-2 w-16 bg-slate-300 rounded" />
                    </div>
                    <div className="space-y-1.5 py-1">
                      <div className="h-2 w-3/4 bg-slate-300 rounded" />
                      <div className="h-2 w-1/2 bg-slate-200 rounded" />
                    </div>
                    {/* Miniature Composer */}
                    <div className="h-6 rounded-lg bg-white border border-slate-300 px-2 flex items-center justify-between shadow-xs">
                      <div className="h-1.5 w-20 bg-slate-300 rounded" />
                      <div className="w-3 h-3 rounded-full bg-slate-900" />
                    </div>
                  </div>
                )}

                {item.id === "system" && (
                  /* System Split Miniature Preview */
                  <div className="w-full h-full flex">
                    {/* Left half: Dark */}
                    <div className="w-1/2 h-full bg-[#050505] p-3 flex flex-col justify-between border-r border-zinc-700">
                      <div className="flex items-center gap-1.5">
                        <div className="w-3.5 h-3.5 rounded bg-zinc-800 text-white font-mono text-[7px] flex items-center justify-center">
                          A
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-zinc-800 rounded" />
                      <div className="h-5 rounded bg-zinc-900 border border-zinc-800" />
                    </div>
                    {/* Right half: Light */}
                    <div className="w-1/2 h-full bg-slate-50 p-3 flex flex-col justify-between">
                      <div className="flex items-center justify-end">
                        <Sun className="w-3 h-3 text-amber-500" />
                      </div>
                      <div className="h-1.5 w-full bg-slate-300 rounded" />
                      <div className="h-5 rounded bg-white border border-slate-300" />
                    </div>
                  </div>
                )}
              </div>

              {/* Card Label and Meta */}
              <div className="flex items-center gap-2 mb-1.5">
                <Icon
                  className={cn(
                    "w-4 h-4",
                    isSelected
                      ? "text-blue-600 dark:text-white"
                      : "text-zinc-600 dark:text-zinc-400"
                  )}
                />
                <h3 className="text-base font-semibold text-zinc-900 dark:text-white tracking-tight">
                  {item.label}
                </h3>
              </div>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                {item.description}
              </p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
